#!/usr/bin/env python3
"""
Sample script demonstrating how to emit skills to ContextCore/Tempo.

This shows the programmatic API for loading skills from this expansion pack
into your observability backend.
"""

from pathlib import Path
from datetime import datetime, timezone

# Note: Requires ContextCore to be installed
# pip install -e /path/to/ContextCore

def emit_skill_basic():
    """Basic skill emission using ContextCore CLI wrapper."""
    import subprocess

    skill_path = Path(__file__).parent.parent / "skills" / "dev-tour-guide"

    result = subprocess.run(
        ["contextcore", "skill", "emit", "--path", str(skill_path)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"Successfully emitted skill from {skill_path}")
        print(result.stdout)
    else:
        print(f"Error emitting skill: {result.stderr}")


def emit_skill_api():
    """Skill emission using ContextCore Python API."""
    try:
        from contextcore.skill import SkillEmitter, SkillManifestParser
        from contextcore.skill.models import SkillManifest
    except ImportError:
        print("ContextCore not installed. Run: pip install -e /path/to/ContextCore")
        return

    # Initialize emitter with agent context
    emitter = SkillEmitter(
        agent_id="expansion-pack-loader",
        session_id=f"session-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    )

    # Parse skill from directory
    skill_path = Path(__file__).parent.parent / "skills" / "dev-tour-guide"
    parser = SkillManifestParser()
    manifest = parser.parse(skill_path)

    # Emit to Tempo
    emitter.emit_manifest(manifest)

    # Emit individual capabilities
    for capability in manifest.capabilities:
        emitter.emit_capability(capability, parent_skill_id=manifest.skill_id)

    print(f"Emitted skill '{manifest.skill_id}' with {len(manifest.capabilities)} capabilities")


def emit_all_skills():
    """Emit all skills in the expansion pack."""
    try:
        from contextcore.skill import SkillEmitter, SkillManifestParser
    except ImportError:
        print("ContextCore not installed. Run: pip install -e /path/to/ContextCore")
        return

    skills_dir = Path(__file__).parent.parent / "skills"

    emitter = SkillEmitter(
        agent_id="expansion-pack-loader",
        session_id=f"batch-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    )
    parser = SkillManifestParser()

    for skill_path in skills_dir.iterdir():
        if skill_path.is_dir() and (skill_path / "MANIFEST.yaml").exists():
            try:
                manifest = parser.parse(skill_path)
                emitter.emit_manifest(manifest)

                for capability in manifest.capabilities:
                    emitter.emit_capability(capability, parent_skill_id=manifest.skill_id)

                print(f"  Emitted: {manifest.skill_id} ({len(manifest.capabilities)} capabilities)")
            except Exception as e:
                print(f"  Failed: {skill_path.name} - {e}")


def query_skills():
    """Query loaded skills from Tempo."""
    try:
        from contextcore.skill import SkillQuerier
    except ImportError:
        print("ContextCore not installed. Run: pip install -e /path/to/ContextCore")
        return

    querier = SkillQuerier()

    # Find all skills
    print("\n=== All Loaded Skills ===")
    skills = querier.query_skills()
    for skill in skills:
        print(f"  - {skill.skill_id}: {skill.description}")

    # Find capabilities by trigger
    print("\n=== Capabilities matching 'debug' ===")
    capabilities = querier.query_capabilities(trigger="debug")
    for cap in capabilities:
        print(f"  - {cap.skill_id}:{cap.capability_id}")
        print(f"    Triggers: {cap.triggers}")
        print(f"    Token budget: {cap.token_budget}")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python sample-skill-emission.py [emit|emit-all|query]")
        print()
        print("Commands:")
        print("  emit      - Emit dev-tour-guide skill")
        print("  emit-all  - Emit all skills in the pack")
        print("  query     - Query loaded skills from Tempo")
        return

    command = sys.argv[1]

    if command == "emit":
        emit_skill_api()
    elif command == "emit-all":
        emit_all_skills()
    elif command == "query":
        query_skills()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
