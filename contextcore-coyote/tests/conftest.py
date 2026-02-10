"""Shared fixtures for contextcore-coyote tests."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from contextcore_coyote.models import (
    Incident,
    IncidentSeverity,
    Lesson,
    StageResult,
    StageStatus,
)
from contextcore_coyote.config import CoyoteConfig
import contextcore_coyote.config as config_module


@pytest.fixture(autouse=True)
def reset_global_config():
    """Reset global config and tracer provider between tests."""
    config_module._config = None
    config_module._tracer_provider = None
    yield
    # Shut down any tracer provider created during the test
    if config_module._tracer_provider is not None:
        try:
            config_module._tracer_provider.shutdown()
        except Exception:
            pass
    config_module._config = None
    config_module._tracer_provider = None


@pytest.fixture
def sample_incident():
    """Pre-built Incident for reuse."""
    return Incident(
        id="INC-20260209120000",
        title="NullPointerException in UserService.getProfile",
        description="NullPointerException when accessing user profile for deleted accounts",
        error_message="NullPointerException: Cannot invoke method on null reference\n  at UserService.getProfile(UserService.java:42)",
        stack_trace=(
            "java.lang.NullPointerException\n"
            "  at com.example.UserService.getProfile(UserService.java:42)\n"
            "  at com.example.ProfileController.show(ProfileController.java:18)\n"
            "  at org.springframework.web.servlet.FrameworkServlet.service(FrameworkServlet.java:97)"
        ),
        severity=IncidentSeverity.HIGH,
        source="log",
        created_at=datetime(2026, 2, 9, 12, 0, 0),
        detected_at=datetime(2026, 2, 9, 12, 0, 5),
        labels={"service": "user-service", "env": "production"},
        affected_files=["src/main/java/com/example/UserService.java"],
    )


@pytest.fixture
def completed_stage_result():
    """Pre-built completed StageResult."""
    started = datetime(2026, 2, 9, 12, 0, 0)
    return StageResult(
        stage_name="investigate",
        status=StageStatus.COMPLETED,
        started_at=started,
        completed_at=started + timedelta(seconds=15),
        summary="Investigation complete: NullPointerException due to missing null check",
        details="Root cause identified in UserService.getProfile",
        root_cause="Missing null check for deleted user accounts",
        affected_code=["src/main/java/com/example/UserService.java"],
        originating_pr="#42",
    )


@pytest.fixture
def incomplete_stage_result():
    """Pre-built in-progress StageResult (no completed_at)."""
    return StageResult(
        stage_name="investigate",
        status=StageStatus.RUNNING,
        started_at=datetime(2026, 2, 9, 12, 0, 0),
        summary="Investigation in progress",
    )


@pytest.fixture
def failed_stage_result():
    """Pre-built failed StageResult."""
    started = datetime(2026, 2, 9, 12, 0, 0)
    return StageResult(
        stage_name="investigate",
        status=StageStatus.FAILED,
        started_at=started,
        completed_at=started + timedelta(seconds=5),
        summary="Stage investigate failed",
        error="LLM call timed out",
    )


@pytest.fixture
def coyote_config():
    """CoyoteConfig with test defaults (no real endpoints)."""
    return CoyoteConfig(
        llm_provider="anthropic",
        llm_model="test-model",
        anthropic_api_key="test-key",
        auto_proceed=True,
        contextcore_enabled=False,
    )


@pytest.fixture
def sample_lesson():
    """Pre-built Lesson for reuse."""
    return Lesson(
        id="INC-001-L1",
        incident_id="INC-001",
        category="null-reference",
        lesson="Always validate user objects before accessing properties",
        prevention="Add null check in getProfile() before accessing user fields",
        created_at=datetime(2026, 2, 9, 12, 0, 0),
        related_files=["UserService.java"],
        tags=["null-check", "validation", "user-service"],
        confidence=0.9,
    )


@pytest.fixture
def sample_llm_responses():
    """Dict of realistic LLM response strings per agent type."""
    return {
        "investigator": """### Root Cause
The NullPointerException occurs because UserService.getProfile() does not check
if the user account has been soft-deleted before accessing profile fields.

### Affected Code
- File: src/main/java/com/example/UserService.java
- Line(s): 42
- Function: getProfile

### Originating Change
- Commit: abc123
- PR: #42
- Author: dev@example.com
- Date: 2026-02-01

### Severity Assessment
High - affects all requests for deleted user profiles

### Recommended Next Steps
1. Add null check before accessing user fields
2. Add unit test for deleted user scenario
""",
        "designer": """### Fix Summary
Add null guard in UserService.getProfile() to return empty profile for deleted users.

### Root Cause (from investigation)
Missing null check when user is soft-deleted.

### Proposed Solution
Add an early return with an empty UserProfile when the user lookup returns null.

### Implementation Details
- Files to modify: UserService.java
- New code needed: no
- Tests to add: test_get_profile_deleted_user

### Tradeoffs
1. Returning empty profile vs throwing UserNotFoundException
2. Performance impact of additional null check is negligible

### Alternatives Considered
1. Throw UserNotFoundException - Why rejected: breaks existing API contract
2. Use Optional<User> return type - Why rejected: too many downstream changes

### Risk Assessment
- Risk Level: Low
- Rollback Strategy: Revert single commit
""",
        "implementer": """### Summary
Add null guard in UserService.getProfile()

#### src/main/java/com/example/UserService.java
```java
public UserProfile getProfile(String userId) {
    User user = userRepository.findById(userId);
    if (user == null || user.isDeleted()) {
        return UserProfile.empty();
    }
    return user.toProfile();
}
```

#### src/test/java/com/example/UserServiceTest.java
```java
@Test
public void testGetProfileDeletedUser() {
    when(userRepository.findById("deleted-user")).thenReturn(null);
    UserProfile profile = userService.getProfile("deleted-user");
    assertNotNull(profile);
    assertTrue(profile.isEmpty());
}
```

### Commit Message
```
fix: add null guard in UserService.getProfile

Handle soft-deleted user accounts by returning empty profile
instead of throwing NullPointerException.

Fixes: INC-20260209120000
```
""",
        "tester": """### Validation Summary
[Pass] - Fix correctly addresses the null pointer issue.

### Root Cause Verification
- Original Issue: NullPointerException on deleted user profiles
- Fix Addresses Issue: Yes, null guard prevents the exception
- Evidence: Added null check before field access

### Regression Analysis
- Affected Code Paths: getProfile(), ProfileController.show()
- Potential Side Effects: None identified
- Existing Tests: Pass

### Edge Cases Tested
1. Null user - Returns empty profile
2. Deleted user - Returns empty profile
3. Active user - Returns normal profile

### Code Quality
- Error Handling: Adequate
- Security: No issues
- Standards Compliance: Yes

### Recommendation
APPROVE

Reason: The fix is minimal, targeted, and includes appropriate test coverage.
""",
        "knowledge": """### Incident Summary
NullPointerException in UserService when accessing profiles of deleted users.

### Category
null-reference

### Lessons Learned

#### Lesson 1
**Lesson**: Always check for null/deleted state before accessing entity properties
**Prevention**: Add defensive null checks at service layer boundaries
**Related Files**: UserService.java, ProfileController.java
**Tags**: null-check, defensive-programming, service-layer

#### Lesson 2
**Lesson**: Soft-delete patterns require null guards at every access point
**Prevention**: Use repository-level filtering to exclude deleted records by default
**Related Files**: UserRepository.java
**Tags**: soft-delete, repository-pattern

### Prevention Checklist
- [ ] Add null checks at service boundaries
- [ ] Configure repository to filter deleted records

### Broader Recommendations
1. Adopt Optional return types for repository lookups
2. Add code review checklist item for null checks
""",
    }


@pytest.fixture
def tmp_knowledge_dir(tmp_path):
    """Temp directory with pre-populated lesson files."""
    lessons_file = tmp_path / "LESSONS_LEARNED.md"
    lessons_file.write_text(
        "# Lessons Learned\n\n"
        "## INC-001: NullPointer in UserService\n"
        "**Category**: null-reference\n"
        "**Lesson**: Always validate user objects before accessing properties\n"
        "**Prevention**: Add null check in getProfile()\n"
        "**Tags**: null-check, validation\n"
        "\n---\n\n"
        "## INC-002: Race condition in OrderProcessor\n"
        "**Category**: race-condition\n"
        "**Lesson**: Use pessimistic locking for concurrent order updates\n"
        "**Prevention**: Add SELECT FOR UPDATE in order processing\n"
        "**Tags**: concurrency, locking\n"
    )
    return tmp_path
