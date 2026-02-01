"""
Lead Contractor Workflow Scripts for ContextCore Phase 3.

This package provides modular scripts for running the startd8 SDK's
Lead Contractor workflow to implement Phase 3 features.

Usage:
    # Run all features
    python3 -m scripts.lead_contractor.run_all

    # Run specific feature groups
    python3 -m scripts.lead_contractor.run_graph
    python3 -m scripts.lead_contractor.run_learning
    python3 -m scripts.lead_contractor.run_vscode

    # Or use the CLI
    python3 scripts/lead_contractor/cli.py graph
    python3 scripts/lead_contractor/cli.py learning
    python3 scripts/lead_contractor/cli.py vscode
    python3 scripts/lead_contractor/cli.py all

    # Beaver workflow: Integrate backlog and complete full cycle
    python3 scripts/lead_contractor/run_integrate_backlog_workflow.py
    python3 scripts/lead_contractor/run_integrate_backlog_workflow.py --feature graph_schema
    python3 scripts/lead_contractor/run_integrate_backlog_workflow.py --dry-run
"""
