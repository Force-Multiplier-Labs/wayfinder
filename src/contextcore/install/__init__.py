"""
ContextCore Installation Verification.

Provides self-verification capabilities to check installation completeness
and emit telemetry about the installation state.
"""

from contextcore.install.requirements import (
    InstallationRequirement,
    RequirementCategory,
    RequirementStatus,
    INSTALLATION_REQUIREMENTS,
)
from contextcore.install.verifier import (
    InstallationVerifier,
    VerificationResult,
    verify_installation,
)

__all__ = [
    "InstallationRequirement",
    "RequirementCategory",
    "RequirementStatus",
    "INSTALLATION_REQUIREMENTS",
    "InstallationVerifier",
    "VerificationResult",
    "verify_installation",
]
