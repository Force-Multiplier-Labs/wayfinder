"""
Tests for the Action framework: ActionResult, ActionRegistry, and Action base class.

Covers:
- ActionStatus enum
- ActionResult dataclass and to_dict serialization
- ActionRegistry: register (decorator + direct), get, list_actions, execute
- Validation gating (validate returning an error prevents execute)
- Exception handling in execute (graceful failure)
- Lazy instantiation of action instances
"""

import pytest

from contextcore_rabbit.action import (
    Action,
    ActionRegistry,
    ActionResult,
    ActionStatus,
    action_registry,
)


# ---------------------------------------------------------------------------
# ActionStatus enum
# ---------------------------------------------------------------------------

class TestActionStatus:
    def test_values(self):
        assert ActionStatus.SUCCESS.value == "success"
        assert ActionStatus.FAILED.value == "failed"
        assert ActionStatus.SKIPPED.value == "skipped"

    def test_member_count(self):
        assert len(ActionStatus) == 3


# ---------------------------------------------------------------------------
# ActionResult
# ---------------------------------------------------------------------------

class TestActionResult:
    def test_minimal_construction(self):
        result = ActionResult(
            status=ActionStatus.SUCCESS,
            action_name="test",
        )
        assert result.status == ActionStatus.SUCCESS
        assert result.action_name == "test"
        assert result.message == ""
        assert result.data == {}
        assert result.duration_ms == 0.0
        assert result.timestamp  # auto-generated

    def test_to_dict_serialization(self):
        result = ActionResult(
            status=ActionStatus.FAILED,
            action_name="my_action",
            message="something broke",
            data={"detail": "info"},
            duration_ms=42.5,
        )
        d = result.to_dict()
        assert d["status"] == "failed"
        assert d["action_name"] == "my_action"
        assert d["message"] == "something broke"
        assert d["data"]["detail"] == "info"
        assert d["duration_ms"] == 42.5
        assert "timestamp" in d

    def test_to_dict_keys(self):
        result = ActionResult(status=ActionStatus.SUCCESS, action_name="t")
        d = result.to_dict()
        expected_keys = {
            "status", "action_name", "message",
            "data", "duration_ms", "timestamp",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# ActionRegistry: registration
# ---------------------------------------------------------------------------

class TestActionRegistryRegistration:
    def test_register_class_direct(self, fresh_registry):
        from conftest import SuccessAction
        fresh_registry.register_class("s", SuccessAction)
        assert fresh_registry.get("s") is not None

    def test_register_via_decorator(self, fresh_registry):
        @fresh_registry.register("decorated")
        class DecoratedAction(Action):
            name = "decorated"
            description = "via decorator"

            def execute(self, payload, context):
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action_name=self.name,
                )

        action = fresh_registry.get("decorated")
        assert action is not None
        assert action.name == "decorated"

    def test_decorator_sets_name_on_class(self, fresh_registry):
        @fresh_registry.register("custom_name")
        class MyAction(Action):
            description = "test"

            def execute(self, payload, context):
                return ActionResult(status=ActionStatus.SUCCESS, action_name=self.name)

        assert MyAction.name == "custom_name"

    def test_list_actions_returns_metadata(self, populated_registry):
        actions = populated_registry.list_actions()
        names = {a["name"] for a in actions}
        assert "success" in names
        assert "failing" in names
        assert "validating" in names
        for a in actions:
            assert "name" in a
            assert "description" in a


# ---------------------------------------------------------------------------
# ActionRegistry: get / lazy instantiation
# ---------------------------------------------------------------------------

class TestActionRegistryGet:
    def test_get_returns_none_for_unknown(self, fresh_registry):
        assert fresh_registry.get("nonexistent") is None

    def test_get_returns_instance(self, populated_registry):
        action = populated_registry.get("success")
        assert isinstance(action, Action)

    def test_get_returns_same_instance_on_repeated_calls(self, populated_registry):
        a1 = populated_registry.get("success")
        a2 = populated_registry.get("success")
        assert a1 is a2

    def test_different_names_return_different_instances(self, populated_registry):
        a = populated_registry.get("success")
        b = populated_registry.get("failing")
        assert a is not b


# ---------------------------------------------------------------------------
# ActionRegistry: execute
# ---------------------------------------------------------------------------

class TestActionRegistryExecute:
    def test_successful_execution(self, populated_registry):
        result = populated_registry.execute(
            "success", {"key": "value"}, {"ctx": True}
        )
        assert result.status == ActionStatus.SUCCESS
        assert result.action_name == "success"
        assert "key" in result.data["received_keys"]
        assert result.duration_ms > 0

    def test_execute_unknown_action_returns_failed(self, populated_registry):
        result = populated_registry.execute("no_such_action", {})
        assert result.status == ActionStatus.FAILED
        assert "not found" in result.message.lower()
        assert result.action_name == "no_such_action"

    def test_execute_with_exception_returns_failed(self, populated_registry):
        result = populated_registry.execute("failing", {})
        assert result.status == ActionStatus.FAILED
        assert "intentional failure" in result.message
        assert result.duration_ms > 0

    def test_execute_with_validation_failure(self, populated_registry):
        result = populated_registry.execute("validating", {"no_field": True})
        assert result.status == ActionStatus.FAILED
        assert "validation failed" in result.message.lower()

    def test_execute_with_validation_success(self, populated_registry):
        result = populated_registry.execute(
            "validating", {"required_field": "present"}
        )
        assert result.status == ActionStatus.SUCCESS

    def test_execute_passes_none_context_as_empty_dict(self, populated_registry):
        """When context=None (default), the action should receive {}."""
        result = populated_registry.execute("success", {"x": 1})
        assert result.status == ActionStatus.SUCCESS

    def test_execute_records_duration(self, populated_registry):
        result = populated_registry.execute("success", {})
        assert isinstance(result.duration_ms, float)
        assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

class TestGlobalRegistry:
    def test_global_registry_is_an_instance(self):
        assert isinstance(action_registry, ActionRegistry)

    def test_global_registry_has_log_action_after_import(self):
        """Importing the actions subpackage registers built-in actions."""
        import contextcore_rabbit.actions  # noqa: F401

        action = action_registry.get("log")
        assert action is not None
        assert action.name == "log"
