"""
Dashboard provisioning and discovery module for Wayfinder.

Provides Grafana dashboard provisioning and auto-discovery for all
Wayfinder extension packs (core, squirrel, rabbit, beaver, fox, coyote, owl).

Example usage:
    from contextcore.dashboards import DashboardProvisioner, discover_all_dashboards

    # Discover all dashboards
    dashboards = discover_all_dashboards()
    print(f"Found {len(dashboards)} dashboards")

    # Provision to Grafana
    provisioner = DashboardProvisioner(grafana_url="http://localhost:3000")
    provisioner.provision_all()
"""

from contextcore.dashboards.provisioner import (
    DashboardProvisioner,
    DashboardConfig,
)
from contextcore.dashboards.discovery import (
    EXTENSION_REGISTRY,
    DashboardConfig as DiscoveryDashboardConfig,
    discover_from_filesystem,
    discover_from_entry_points,
    discover_all_dashboards,
    list_extensions,
    get_dashboard_root,
)

__all__ = [
    # Provisioner
    "DashboardProvisioner",
    "DashboardConfig",
    # Discovery
    "EXTENSION_REGISTRY",
    "DiscoveryDashboardConfig",
    "discover_from_filesystem",
    "discover_from_entry_points",
    "discover_all_dashboards",
    "list_extensions",
    "get_dashboard_root",
]
