"""
Operations module for ContextCore.

Provides operational commands for:
- Preflight checks (doctor)
- Health monitoring
- Smoke testing
- Backup and restore
- Storage management

Example usage:
    from contextcore.ops import (
        doctor,
        health_check,
        smoke_test,
        backup,
        restore,
    )

    # Run preflight checks
    issues = doctor()

    # Check component health
    status = health_check()

    # Full stack validation
    passed, total = smoke_test()

    # Backup state
    backup_path = backup()
"""

from contextcore.ops.doctor import doctor, DoctorResult
from contextcore.ops.health import health_check, HealthStatus, ComponentHealth
from contextcore.ops.smoke_test import smoke_test, SmokeTestResult
from contextcore.ops.backup import backup, restore, list_backups

__all__ = [
    # Doctor
    "doctor",
    "DoctorResult",
    # Health
    "health_check",
    "HealthStatus",
    "ComponentHealth",
    # Smoke Test
    "smoke_test",
    "SmokeTestResult",
    # Backup
    "backup",
    "restore",
    "list_backups",
]
