#!/usr/bin/env python3
"""
Capability Extractor

Scans a project to identify capabilities from various sources and generates
a structured YAML output for value proposition mapping.

Usage:
    python extract_capabilities.py /path/to/project --output capabilities.yaml
    python extract_capabilities.py /path/to/project --sources "skills,workflows"
"""

import argparse
import os
import re
import yaml
from pathlib import Path
from datetime import datetime


def extract_skills(project_path: Path) -> list[dict]:
    """Extract capabilities from Claude skills."""
    capabilities = []
    skills_paths = [
        project_path / ".claude" / "skills",
        Path.home() / ".claude" / "skills",
    ]

    for skills_path in skills_paths:
        if not skills_path.exists():
            continue

        for skill_dir in skills_path.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            content = skill_md.read_text()

            # Parse frontmatter
            frontmatter_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
            if frontmatter_match:
                try:
                    meta = yaml.safe_load(frontmatter_match.group(1))
                    capabilities.append({
                        "id": skill_dir.name,
                        "name": meta.get("name", skill_dir.name),
                        "category": "skill",
                        "technical": {
                            "description": meta.get("description", ""),
                            "source_files": [{"path": str(skill_md), "type": "skill"}],
                            "complexity": "medium",
                            "maturity": "stable",
                        },
                        "value": {
                            "tagline": "",  # To be filled
                            "one_liner": meta.get("description", "")[:100],
                            "pain_points_solved": [],
                            "outcomes": [],
                        },
                        "adoption": {
                            "time_to_value": "5 minutes",
                            "learning_curve": "low",
                        },
                    })
                except yaml.YAMLError:
                    pass

    return capabilities


def extract_workflows(project_path: Path) -> list[dict]:
    """Extract capabilities from GitHub Actions workflows."""
    capabilities = []
    workflows_path = project_path / ".github" / "workflows"

    if not workflows_path.exists():
        return capabilities

    for workflow_file in workflows_path.glob("*.yml"):
        content = workflow_file.read_text()

        try:
            workflow = yaml.safe_load(content)
            if not workflow:
                continue

            name = workflow.get("name", workflow_file.stem)

            # Determine triggers
            triggers = []
            on_config = workflow.get("on", {})
            if isinstance(on_config, dict):
                triggers = list(on_config.keys())
            elif isinstance(on_config, list):
                triggers = on_config
            elif isinstance(on_config, str):
                triggers = [on_config]

            capabilities.append({
                "id": workflow_file.stem,
                "name": name,
                "category": "automation",
                "technical": {
                    "description": f"GitHub Actions workflow triggered by: {', '.join(triggers)}",
                    "source_files": [{"path": str(workflow_file), "type": "workflow"}],
                    "complexity": "medium",
                    "maturity": "stable",
                },
                "value": {
                    "tagline": "",
                    "one_liner": f"Automated {name.lower()}",
                    "pain_points_solved": [],
                    "outcomes": [],
                },
                "adoption": {
                    "time_to_value": "immediate",
                    "learning_curve": "low",
                },
            })
        except yaml.YAMLError:
            pass

    return capabilities


def extract_apis(project_path: Path) -> list[dict]:
    """Extract capabilities from API definitions (OpenAPI/Swagger)."""
    capabilities = []

    api_patterns = ["openapi.yaml", "openapi.yml", "swagger.yaml", "swagger.yml", "api.yaml"]

    for pattern in api_patterns:
        for api_file in project_path.rglob(pattern):
            try:
                content = api_file.read_text()
                spec = yaml.safe_load(content)

                if not spec:
                    continue

                info = spec.get("info", {})
                paths = spec.get("paths", {})

                # Extract API as single capability
                capabilities.append({
                    "id": f"api-{api_file.stem}",
                    "name": info.get("title", "API"),
                    "category": "api",
                    "technical": {
                        "description": info.get("description", ""),
                        "source_files": [{"path": str(api_file), "type": "api"}],
                        "complexity": "high",
                        "maturity": "stable",
                    },
                    "value": {
                        "tagline": "",
                        "one_liner": info.get("description", "")[:100] if info.get("description") else "",
                        "pain_points_solved": [],
                        "outcomes": [],
                        "endpoints_count": len(paths),
                    },
                    "adoption": {
                        "time_to_value": "varies",
                        "learning_curve": "medium",
                    },
                })
            except (yaml.YAMLError, Exception):
                pass

    return capabilities


def extract_readme(project_path: Path) -> list[dict]:
    """Extract feature mentions from README files."""
    capabilities = []

    readme_names = ["README.md", "readme.md", "README.rst", "README"]

    for readme_name in readme_names:
        readme_path = project_path / readme_name
        if not readme_path.exists():
            continue

        content = readme_path.read_text()

        # Look for Features section
        features_match = re.search(
            r'##?\s*Features?\s*\n(.*?)(?=\n##|\Z)',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if features_match:
            features_text = features_match.group(1)
            # Extract bullet points
            bullets = re.findall(r'[-*]\s+\*?\*?([^*\n]+)', features_text)

            for i, bullet in enumerate(bullets[:10]):  # Limit to 10
                feature_name = bullet.strip()
                if len(feature_name) > 5:
                    capabilities.append({
                        "id": f"feature-{i+1}",
                        "name": feature_name[:50],
                        "category": "feature",
                        "technical": {
                            "description": feature_name,
                            "source_files": [{"path": str(readme_path), "type": "documentation"}],
                            "complexity": "unknown",
                            "maturity": "unknown",
                        },
                        "value": {
                            "tagline": "",
                            "one_liner": feature_name,
                            "pain_points_solved": [],
                            "outcomes": [],
                        },
                        "adoption": {
                            "time_to_value": "unknown",
                            "learning_curve": "unknown",
                        },
                    })
        break

    return capabilities


def extract_configs(project_path: Path) -> list[dict]:
    """Extract configurable capabilities from config files."""
    capabilities = []

    config_patterns = [
        "*.config.js", "*.config.ts", "config.yaml", "config.yml",
        ".env.example", "settings.py"
    ]

    for pattern in config_patterns:
        for config_file in project_path.glob(pattern):
            if config_file.is_file():
                capabilities.append({
                    "id": f"config-{config_file.stem}",
                    "name": f"{config_file.stem} Configuration",
                    "category": "configuration",
                    "technical": {
                        "description": f"Configurable options in {config_file.name}",
                        "source_files": [{"path": str(config_file), "type": "config"}],
                        "complexity": "low",
                        "maturity": "stable",
                    },
                    "value": {
                        "tagline": "",
                        "one_liner": "Customize behavior through configuration",
                        "pain_points_solved": [],
                        "outcomes": [],
                    },
                    "adoption": {
                        "time_to_value": "5 minutes",
                        "learning_curve": "low",
                    },
                })

    return capabilities


def main():
    parser = argparse.ArgumentParser(
        description="Extract capabilities from a project for value proposition mapping"
    )
    parser.add_argument("project_path", help="Path to the project to analyze")
    parser.add_argument(
        "--output", "-o",
        default="capabilities.yaml",
        help="Output file path (default: capabilities.yaml)"
    )
    parser.add_argument(
        "--sources", "-s",
        default="skills,workflows,apis,readme,configs",
        help="Comma-separated list of sources to extract from"
    )

    args = parser.parse_args()
    project_path = Path(args.project_path).resolve()

    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        return 1

    sources = [s.strip().lower() for s in args.sources.split(",")]

    all_capabilities = []

    extractors = {
        "skills": extract_skills,
        "workflows": extract_workflows,
        "apis": extract_apis,
        "readme": extract_readme,
        "configs": extract_configs,
    }

    print(f"Extracting capabilities from: {project_path}")
    print(f"Sources: {', '.join(sources)}")
    print()

    for source in sources:
        if source in extractors:
            capabilities = extractors[source](project_path)
            print(f"  {source}: {len(capabilities)} capabilities found")
            all_capabilities.extend(capabilities)

    # Generate output
    output = {
        "metadata": {
            "extracted_from": str(project_path),
            "extracted_at": datetime.now().isoformat(),
            "sources": sources,
            "total_capabilities": len(all_capabilities),
        },
        "capabilities": all_capabilities,
    }

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        yaml.dump(output, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print()
    print(f"Extracted {len(all_capabilities)} capabilities to {output_path}")
    print()
    print("Next steps:")
    print("  1. Review extracted capabilities")
    print("  2. Fill in value propositions (tagline, pain_points_solved, outcomes)")
    print("  3. Map to personas")
    print("  4. Generate channel-specific content")

    return 0


if __name__ == "__main__":
    exit(main())
