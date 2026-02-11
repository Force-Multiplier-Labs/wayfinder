"""Tests for contextcore_squirrel.knowledge_parser."""

from pathlib import Path

import pytest
import yaml

from contextcore_squirrel.knowledge_parser import (
    CapabilityItem,
    Endpoint,
    KnowledgeParser,
    Process,
    Project,
    Skill,
    SquirrelIndex,
    Tool,
    Workflow,
    _flatten_list_to_string,
    _get_tier_from_path,
    _parse_authentication,
    _safe_int_conversion,
    parse_capability_index,
    parse_endpoints_yaml,
    parse_processes_yaml,
    parse_projects_yaml,
    parse_skills_yaml,
    parse_tools_yaml,
    parse_workflows_yaml,
)


class TestUtilityFunctions:
    """Test utility helper functions."""

    def test_flatten_list_to_string_with_list(self):
        assert _flatten_list_to_string(["a", "b", "c"]) == "a,b,c"

    def test_flatten_list_to_string_with_string(self):
        assert _flatten_list_to_string("hello") == "hello"

    def test_flatten_list_to_string_with_none(self):
        assert _flatten_list_to_string(None) == ""

    def test_flatten_list_to_string_with_default(self):
        assert _flatten_list_to_string(None, "default") == "default"

    def test_flatten_list_to_string_with_int(self):
        assert _flatten_list_to_string(42) == "42"

    def test_flatten_list_to_string_filters_empty(self):
        assert _flatten_list_to_string(["a", "", "b"]) == "a,b"

    def test_parse_authentication_dict(self):
        assert _parse_authentication({"type": "bearer"}) == "bearer"

    def test_parse_authentication_string(self):
        assert _parse_authentication("basic") == "basic"

    def test_parse_authentication_none(self):
        assert _parse_authentication(None) == "none"

    def test_get_tier_from_path_public(self, tmp_path):
        p = tmp_path / "public" / "index"
        p.mkdir(parents=True)
        assert _get_tier_from_path(p) == "public"

    def test_get_tier_from_path_default(self, tmp_path):
        p = tmp_path / "random" / "index"
        p.mkdir(parents=True)
        assert _get_tier_from_path(p) == "personal"

    def test_safe_int_conversion_valid(self):
        assert _safe_int_conversion("42") == 42

    def test_safe_int_conversion_invalid(self):
        assert _safe_int_conversion("abc", 0) == 0

    def test_safe_int_conversion_none(self):
        assert _safe_int_conversion(None, 5) == 5


class TestPydanticModels:
    """Test Pydantic model creation and validation."""

    def test_capability_item(self):
        item = CapabilityItem(
            id="test", name="Test", category="skill", description="A test item"
        )
        assert item.id == "test"
        assert item.token_budget == 0

    def test_endpoint_model(self):
        ep = Endpoint(
            id="ep1",
            name="Grafana",
            category="endpoint",
            description="Dashboard",
            url="http://localhost:3000",
            port=3000,
        )
        assert ep.port == 3000
        assert ep.protocol == "http"

    def test_skill_model(self):
        skill = Skill(
            id="s1",
            name="Analysis",
            category="skill",
            description="Analyze things",
            token_budget=2000,
        )
        assert skill.token_budget == 2000

    def test_squirrel_index_stats(self):
        idx = SquirrelIndex(
            tier="public",
            endpoints=[
                Endpoint(
                    id="e1", name="E1", category="endpoint", description="EP"
                )
            ],
            skills=[
                Skill(id="s1", name="S1", category="skill", description="SK"),
                Skill(id="s2", name="S2", category="skill", description="SK2"),
            ],
        )
        stats = idx.get_stats()
        assert stats["endpoints"] == 1
        assert stats["skills"] == 2
        assert idx.total_items() == 3

    def test_squirrel_index_model_dump(self):
        idx = SquirrelIndex(tier="public")
        dumped = idx.model_dump()
        assert dumped["tier"] == "public"
        assert dumped["endpoints"] == []


class TestParseEndpoints:
    """Test endpoint YAML parsing."""

    def test_parse_endpoints(self, tmp_index):
        caps_dir = tmp_index / "capabilities"
        endpoints = parse_endpoints_yaml(caps_dir / "endpoints.yaml", "public")
        assert len(endpoints) == 2
        assert endpoints[0].id == "grafana_local"
        assert endpoints[0].port == 3000
        assert endpoints[1].id == "tempo_local"

    def test_parse_endpoints_missing_file(self, tmp_path):
        endpoints = parse_endpoints_yaml(tmp_path / "nonexistent.yaml", "public")
        assert endpoints == []


class TestParseSkills:
    """Test skills YAML parsing."""

    def test_parse_skills(self, tmp_index):
        caps_dir = tmp_index / "capabilities"
        skills = parse_skills_yaml(caps_dir / "skills.yaml", "public")
        assert len(skills) == 1
        assert skills[0].id == "o11y"
        assert skills[0].token_budget == 2000

    def test_parse_skills_tags_as_list(self, tmp_index):
        caps_dir = tmp_index / "capabilities"
        skills = parse_skills_yaml(caps_dir / "skills.yaml", "public")
        assert "monitoring" in skills[0].tags


class TestParseTools:
    """Test tools YAML parsing."""

    def test_parse_tools(self, tmp_index):
        caps_dir = tmp_index / "capabilities"
        tools = parse_tools_yaml(caps_dir / "tools.yaml", "public")
        assert len(tools) == 1
        assert tools[0].tool_type == "script"


class TestParseWorkflows:
    """Test workflow YAML parsing."""

    def test_parse_workflows(self, tmp_index):
        caps_dir = tmp_index / "capabilities"
        workflows = parse_workflows_yaml(caps_dir / "workflows.yaml", "public")
        assert len(workflows) == 1
        assert workflows[0].step_count == 5


class TestParseProcesses:
    """Test process YAML parsing."""

    def test_parse_processes(self, tmp_index):
        caps_dir = tmp_index / "capabilities"
        processes = parse_processes_yaml(caps_dir / "processes.yaml", "public")
        assert len(processes) == 1
        assert processes[0].is_anti_pattern is False


class TestParseProjects:
    """Test project YAML parsing."""

    def test_parse_projects(self, tmp_index):
        caps_dir = tmp_index / "capabilities"
        projects = parse_projects_yaml(caps_dir / "projects.yaml", "public")
        assert len(projects) == 1
        assert projects[0].status == "active"


class TestParseCapabilityIndex:
    """Test the master parse_capability_index function."""

    def test_parse_full_index(self, tmp_index):
        index = parse_capability_index(tmp_index)
        assert index.total_items() == 7  # 2 endpoints + 1 skill + 1 tool + 1 workflow + 1 process + 1 project

    def test_parse_nonexistent_path(self, tmp_path):
        index = parse_capability_index(tmp_path / "nonexistent")
        assert index.tier == "unknown"
        assert index.total_items() == 0

    def test_parse_empty_index(self, empty_yaml_index):
        index = parse_capability_index(empty_yaml_index)
        assert index.total_items() == 0

    def test_parse_index_with_bad_yaml(self, tmp_path):
        caps_dir = tmp_path / "capabilities"
        caps_dir.mkdir()
        (caps_dir / "endpoints.yaml").write_text("{{invalid yaml")
        index = parse_capability_index(tmp_path)
        assert index.total_items() == 0

    def test_parse_index_missing_required_fields(self, tmp_path):
        caps_dir = tmp_path / "capabilities"
        caps_dir.mkdir()
        # Item missing 'description'
        data = {"endpoints": [{"id": "e1", "name": "E1"}]}
        (caps_dir / "endpoints.yaml").write_text(yaml.dump(data))
        index = parse_capability_index(tmp_path)
        assert len(index.endpoints) == 0


class TestKnowledgeParserClass:
    """Test the KnowledgeParser wrapper class."""

    def test_parse(self, tmp_index):
        parser = KnowledgeParser(tmp_index)
        index = parser.parse()
        assert index.total_items() == 7

    def test_parse_json(self, tmp_index):
        parser = KnowledgeParser(tmp_index)
        json_str = parser.parse_json()
        import json

        data = json.loads(json_str)
        assert "endpoints" in data
        assert "skills" in data
