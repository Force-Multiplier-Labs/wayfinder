"""ContextCore CLI - RBAC management commands."""

from typing import Optional

import click


@click.group()
def rbac():
    """Manage RBAC roles and permissions for ContextCore Tour Guide."""
    pass


@rbac.command("list-roles")
def rbac_list_roles():
    """List all available roles."""
    from contextcore.rbac import get_rbac_store, BUILT_IN_ROLE_IDS

    store = get_rbac_store()
    roles = store.list_roles()

    if not roles:
        click.echo("No roles found.")
        return

    click.echo("Available Roles:")
    click.echo()
    click.echo(f"{'ID':<20} {'Name':<25} {'Built-in':<10} Permissions")
    click.echo("-" * 80)

    for role in sorted(roles, key=lambda r: (not r.built_in, r.id)):
        builtin = "Yes" if role.id in BUILT_IN_ROLE_IDS else "No"
        perm_count = len(role.permissions)
        inherits = f" (inherits: {', '.join(role.inherits_from)})" if role.inherits_from else ""
        click.echo(f"{role.id:<20} {role.name:<25} {builtin:<10} {perm_count}{inherits}")


@rbac.command("show-role")
@click.argument("role_id")
def rbac_show_role(role_id: str):
    """Show details of a specific role."""
    from contextcore.rbac import get_rbac_store

    store = get_rbac_store()
    role = store.get_role(role_id)

    if not role:
        raise click.ClickException(f"Role not found: {role_id}")

    click.echo(f"Role: {role.name} ({role.id})")
    click.echo(f"Description: {role.description}")
    click.echo(f"Built-in: {'Yes' if role.built_in else 'No'}")

    if role.inherits_from:
        click.echo(f"Inherits from: {', '.join(role.inherits_from)}")

    if role.assignable_to:
        click.echo(f"Assignable to: {', '.join(role.assignable_to)}")

    click.echo()
    click.echo("Permissions:")
    for perm in role.permissions:
        sensitive = " [SENSITIVE]" if perm.resource.sensitive else ""
        actions = ", ".join(perm.actions)
        click.echo(f"  - {perm.id}: {perm.resource.resource_type}/{perm.resource.resource_id}")
        click.echo(f"    Actions: {actions}{sensitive}")


@rbac.command("grant")
@click.option("--principal", "-p", required=True, help="Principal ID")
@click.option("--principal-type", "-t", type=click.Choice(["agent", "user", "team", "service_account"]), default="user")
@click.option("--role", "-r", required=True, help="Role ID to grant")
@click.option("--project-scope", help="Limit to specific project")
@click.option("--created-by", default="cli", help="Who is granting this role")
def rbac_grant(principal: str, principal_type: str, role: str, project_scope: Optional[str], created_by: str):
    """Grant a role to a principal."""
    from contextcore.rbac import get_rbac_store, RoleBinding, PrincipalType
    import uuid

    store = get_rbac_store()

    if not store.get_role(role):
        raise click.ClickException(f"Role not found: {role}")

    binding_id = f"{principal}-{role}-{uuid.uuid4().hex[:8]}"
    binding = RoleBinding(
        id=binding_id,
        principal_id=principal,
        principal_type=PrincipalType(principal_type),
        role_id=role,
        project_scope=project_scope,
        created_by=created_by,
    )

    store.save_binding(binding)
    click.echo(f"Granted role '{role}' to {principal_type} '{principal}'")
    if project_scope:
        click.echo(f"  Scoped to project: {project_scope}")


@rbac.command("revoke")
@click.option("--principal", "-p", required=True, help="Principal ID")
@click.option("--role", "-r", required=True, help="Role ID to revoke")
def rbac_revoke(principal: str, role: str):
    """Revoke a role from a principal."""
    from contextcore.rbac import get_rbac_store

    store = get_rbac_store()
    bindings = store.list_bindings(principal_id=principal, role_id=role)

    if not bindings:
        raise click.ClickException(f"No binding found for {principal} with role {role}")

    for binding in bindings:
        store.delete_binding(binding.id)
        click.echo(f"Revoked role '{role}' from '{principal}' (binding: {binding.id})")


@rbac.command("list-bindings")
@click.option("--principal", "-p", help="Filter by principal ID")
@click.option("--role", "-r", help="Filter by role ID")
def rbac_list_bindings(principal: Optional[str], role: Optional[str]):
    """List role bindings."""
    from contextcore.rbac import get_rbac_store

    store = get_rbac_store()
    bindings = store.list_bindings(principal_id=principal, role_id=role)

    if not bindings:
        click.echo("No bindings found.")
        return

    click.echo("Role Bindings:")
    click.echo()
    click.echo(f"{'Principal':<25} {'Type':<15} {'Role':<20} {'Scope':<15}")
    click.echo("-" * 80)

    for b in bindings:
        scope = b.project_scope or "(all)"
        click.echo(f"{b.principal_id:<25} {b.principal_type:<15} {b.role_id:<20} {scope:<15}")


@rbac.command("check")
@click.option("--principal", "-p", required=True, help="Principal ID")
@click.option("--principal-type", "-t", type=click.Choice(["agent", "user", "team", "service_account"]), default="user")
@click.option("--resource", "-r", required=True, help="Resource (type/id)")
@click.option("--action", "-a", required=True, help="Action (read, write, query, emit)")
@click.option("--project-scope", help="Project scope")
def rbac_check(principal: str, principal_type: str, resource: str, action: str, project_scope: Optional[str]):
    """Check if a principal has access to a resource."""
    from contextcore.rbac import get_enforcer, Resource, ResourceType, Action, PrincipalType, PolicyDecision

    if "/" not in resource:
        raise click.ClickException("Resource must be in format: type/id")

    res_type, res_id = resource.split("/", 1)
    sensitive = res_type == "knowledge_category" and res_id.lower() == "security"

    resource_obj = Resource(
        resource_type=ResourceType(res_type),
        resource_id=res_id,
        sensitive=sensitive,
        project_scope=project_scope,
    )

    enforcer = get_enforcer()
    decision = enforcer.check_access(
        principal_id=principal,
        principal_type=PrincipalType(principal_type),
        resource=resource_obj,
        action=Action(action),
        project_scope=project_scope,
    )

    if decision.decision == PolicyDecision.ALLOW:
        click.echo(click.style("ALLOWED", fg="green"))
        click.echo(f"  Matched role: {decision.matched_role}")
        click.echo(f"  Matched permission: {decision.matched_permission}")
    else:
        click.echo(click.style("DENIED", fg="red"))
        click.echo(f"  Reason: {decision.denial_reason}")


@rbac.command("whoami")
def rbac_whoami():
    """Show the current principal identity."""
    from contextcore.rbac import PrincipalResolver

    principal = PrincipalResolver.from_cli_context()

    click.echo(f"Principal ID: {principal.id}")
    click.echo(f"Type: {principal.principal_type}")
    click.echo(f"Display Name: {principal.display_name}")

    if principal.agent_id:
        click.echo(f"Agent ID: {principal.agent_id}")
    if principal.email:
        click.echo(f"Email: {principal.email}")
