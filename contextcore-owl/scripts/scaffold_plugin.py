#!/usr/bin/env python3
"""
Asynchronous Plugin Scaffolding with contextcore-beaver SDK

Uses contextcore-beaver's LLM abstraction to generate Grafana plugin files
in batches with automatic metrics tracking and response storage.

Usage:
    python scripts/scaffold_plugin.py --plugin-type panel --name contextcore-example-panel
    python scripts/scaffold_plugin.py --plugin-type datasource --name contextcore-example-datasource

Requirements:
    pip install contextcore-beaver
    export ANTHROPIC_API_KEY=your-key

Ported from O11yBubo to contextcore-owl.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Try to import contextcore-beaver
try:
    from contextcore_beaver import LLMClient
    BEAVER_AVAILABLE = True
except ImportError:
    try:
        # Fallback to startd8 if beaver not available
        from startd8 import ClaudeAgent
        BEAVER_AVAILABLE = False
        STARTD8_AVAILABLE = True
    except ImportError:
        BEAVER_AVAILABLE = False
        STARTD8_AVAILABLE = False
        print("[WARNING] Neither contextcore-beaver nor startd8 available.")
        print("Install with: pip install contextcore-beaver")

# Configuration
SKILL_PATH = Path.home() / ".claude" / "skills" / "grafana-plugin-dev" / "SKILL.md"
OUTPUT_DIR = PROJECT_ROOT / "plugins"
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")


class PluginScaffolder:
    """
    Asynchronous plugin scaffolder using contextcore-beaver SDK.

    Generates Grafana plugin files in batches:
    - Batch 1 (parallel): metadata files (plugin.json, package.json, types.ts)
    - Batch 2 (parallel): implementation (module.ts, Panel.tsx/datasource.ts)
    - Batch 3 (sequential): integration (tests, build config)
    """

    def __init__(self, plugin_type: str, plugin_name: str, output_dir: Path):
        self.plugin_type = plugin_type
        self.plugin_name = plugin_name
        self.output_dir = output_dir / plugin_name
        self.client = None
        self.skill_content = ""
        self.results: Dict[str, Any] = {}

        # Load skill content
        if SKILL_PATH.exists():
            self.skill_content = SKILL_PATH.read_text()

        # Initialize LLM client
        if BEAVER_AVAILABLE:
            try:
                self.client = LLMClient(provider="anthropic", model=MODEL)
            except Exception as e:
                print(f"[ERROR] Failed to initialize beaver client: {e}")
        elif STARTD8_AVAILABLE:
            try:
                self.client = ClaudeAgent(name="grafana-plugin-dev", model=MODEL, max_tokens=4096)
            except Exception as e:
                print(f"[ERROR] Failed to initialize startd8 agent: {e}")

    def _create_prompt(self, file_type: str, context: str = "") -> str:
        """Create a generation prompt for a specific file type."""
        prompts = {
            "plugin.json": f"""Generate plugin.json for a Grafana {self.plugin_type} plugin.

Plugin name: {self.plugin_name}
Plugin ID: {self.plugin_name.replace('-', '')}
Type: {self.plugin_type}
Author: ContextCore

Requirements:
- Grafana 10+ compatibility
- Include all required metadata fields
- Use proper versioning
- Include keywords: contextcore, {self.plugin_type}

Return ONLY the JSON content, no markdown code blocks.""",

            "package.json": f"""Generate package.json for a Grafana {self.plugin_type} plugin.

Plugin name: {self.plugin_name}
Author: ContextCore

Requirements:
- Include @grafana/data, @grafana/ui, @grafana/runtime as dependencies
- Include necessary dev dependencies for TypeScript and testing
- Include build scripts (dev, build, test, clean)
- Node 20+ required

Return ONLY the JSON content, no markdown code blocks.""",

            "types.ts": f"""Generate types.ts for a Grafana {self.plugin_type} plugin called {self.plugin_name}.

{context}

Requirements:
- Define all necessary TypeScript interfaces
- Use proper Grafana types from @grafana/data
- Include JSDoc comments

Return ONLY the TypeScript code, no markdown code blocks.""",

            "module.ts": f"""Generate module.ts for a Grafana {self.plugin_type} plugin called {self.plugin_name}.

{context}

Requirements:
- Import from @grafana/data
- Register the plugin properly
- Configure panel options appropriately

Return ONLY the TypeScript code, no markdown code blocks.""",

            "Panel.tsx": f"""Generate Panel.tsx for a Grafana panel plugin called {self.plugin_name}.

{context}

Requirements:
- Use React functional component with hooks
- Use @grafana/ui components
- Use useStyles2 and @emotion/css for styling
- Handle errors gracefully
- Include loading states

Return ONLY the TypeScript/React code, no markdown code blocks.""",

            "datasource.ts": f"""Generate datasource.ts for a Grafana datasource plugin called {self.plugin_name}.

{context}

Requirements:
- Extend DataSourceApi
- Implement query() method
- Return response as MutableDataFrame
- Implement testDatasource() for connection testing

Return ONLY the TypeScript code, no markdown code blocks.""",

            "QueryEditor.tsx": f"""Generate QueryEditor.tsx for a Grafana datasource plugin called {self.plugin_name}.

{context}

Requirements:
- Use React functional component
- Use @grafana/ui components
- Call onRunQuery appropriately

Return ONLY the TypeScript/React code, no markdown code blocks.""",

            "ConfigEditor.tsx": f"""Generate ConfigEditor.tsx for a Grafana datasource plugin called {self.plugin_name}.

{context}

Requirements:
- Use React functional component
- Use @grafana/ui FieldSet and InlineField
- Allow configuration of URL endpoint

Return ONLY the TypeScript/React code, no markdown code blocks.""",
        }

        base_prompt = prompts.get(file_type, f"Generate {file_type} for {self.plugin_name}")

        # Prepend skill context if available
        if self.skill_content:
            return f"""You are an expert Grafana plugin developer. Use this knowledge:

{self.skill_content[:3000]}...

Now generate the following:

{base_prompt}"""

        return base_prompt

    async def generate_file(self, file_type: str, context: str = "") -> Dict[str, Any]:
        """Generate a single file using the LLM client."""
        if not self.client:
            return {"error": "LLM client not available", "file": file_type}

        prompt = self._create_prompt(file_type, context)

        print(f"  [GENERATING] {file_type}...")
        start_time = datetime.now()

        try:
            # Use contextcore-beaver or startd8
            if BEAVER_AVAILABLE:
                response_text = self.client.complete(prompt)
                response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                total_tokens = self.client.session_tokens
            else:
                # Fallback to startd8
                response_text, response_time_ms, token_usage = self.client.generate(prompt)
                total_tokens = token_usage.total if token_usage else 0

            result = {
                "file": file_type,
                "content": response_text,
                "metrics": {
                    "response_time_ms": response_time_ms,
                    "total_tokens": total_tokens,
                },
                "success": True
            }

            print(f"  [DONE] {file_type} ({response_time_ms}ms, {total_tokens} tokens)")
            return result

        except Exception as e:
            print(f"  [ERROR] {file_type}: {e}")
            return {"file": file_type, "error": str(e), "success": False}

    async def generate_batch_parallel(self, file_types: List[str], context: str = "") -> List[Dict]:
        """Generate multiple files in parallel."""
        tasks = [self.generate_file(ft, context) for ft in file_types]
        return await asyncio.gather(*tasks)

    async def scaffold(self) -> Dict[str, Any]:
        """
        Scaffold the complete plugin using batched generation.

        Batch 1 (parallel): Metadata files
        Batch 2 (parallel): Implementation files
        """
        print(f"\n{'='*60}")
        print(f"ContextCore Grafana Plugin Scaffolder")
        print(f"{'='*60}")
        print(f"Plugin type: {self.plugin_type}")
        print(f"Plugin name: {self.plugin_name}")
        print(f"Output: {self.output_dir}")
        print(f"Model: {MODEL}")
        print(f"SDK: {'contextcore-beaver' if BEAVER_AVAILABLE else 'startd8'}")
        print(f"{'='*60}\n")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "src").mkdir(exist_ok=True)
        (self.output_dir / "src" / "components").mkdir(exist_ok=True)

        all_results = []
        total_tokens = 0
        total_time_ms = 0

        # Batch 1: Metadata (parallel)
        print("[BATCH 1] Generating metadata files (parallel)...")
        batch1_files = ["plugin.json", "package.json", "types.ts"]
        batch1_results = await self.generate_batch_parallel(batch1_files)
        all_results.extend(batch1_results)

        # Extract types for context in batch 2
        types_content = next(
            (r["content"] for r in batch1_results if r.get("file") == "types.ts" and r.get("success")),
            ""
        )

        # Batch 2: Implementation (parallel)
        print("\n[BATCH 2] Generating implementation files (parallel)...")
        if self.plugin_type == "panel":
            batch2_files = ["module.ts", "Panel.tsx"]
        else:
            batch2_files = ["module.ts", "datasource.ts", "QueryEditor.tsx", "ConfigEditor.tsx"]

        context = f"Types defined:\n{types_content[:1000]}" if types_content else ""
        batch2_results = await self.generate_batch_parallel(batch2_files, context)
        all_results.extend(batch2_results)

        # Calculate totals
        for result in all_results:
            if result.get("success") and result.get("metrics"):
                total_tokens += result["metrics"].get("total_tokens", 0)
                total_time_ms += result["metrics"].get("response_time_ms", 0)

        # Write files
        print("\n[WRITING] Saving generated files...")
        for result in all_results:
            if result.get("success") and result.get("content"):
                file_name = result["file"]
                content = result["content"]

                # Determine output path
                if file_name in ["plugin.json", "package.json"]:
                    output_path = self.output_dir / file_name
                elif file_name.endswith(".tsx"):
                    output_path = self.output_dir / "src" / "components" / file_name
                else:
                    output_path = self.output_dir / "src" / file_name

                # Clean content (remove markdown code blocks if present)
                content = self._clean_content(content, file_name)

                output_path.write_text(content)
                print(f"  [SAVED] {output_path.relative_to(self.output_dir)}")

        # Copy webpack config from existing plugin
        self._copy_build_config()

        # Summary
        print(f"\n{'='*60}")
        print(f"SCAFFOLDING COMPLETE")
        print(f"{'='*60}")
        print(f"Plugin: {self.plugin_name}")
        print(f"Files generated: {len([r for r in all_results if r.get('success')])}")
        print(f"Total tokens: {total_tokens}")
        print(f"Total time: {total_time_ms}ms")
        print(f"Output: {self.output_dir}")
        if BEAVER_AVAILABLE:
            print(f"Session cost: ${self.client.session_cost:.4f}")
        print(f"{'='*60}\n")

        print("Next steps:")
        print(f"  cd {self.output_dir}")
        print("  npm install")
        print("  npm run dev")

        return {
            "plugin_name": self.plugin_name,
            "plugin_type": self.plugin_type,
            "output_dir": str(self.output_dir),
            "results": all_results,
            "totals": {
                "tokens": total_tokens,
                "time_ms": total_time_ms,
                "files": len([r for r in all_results if r.get("success")])
            }
        }

    def _clean_content(self, content: str, file_name: str) -> str:
        """Remove markdown code blocks from generated content."""
        lines = content.strip().split("\n")

        # Remove leading ```json, ```typescript, etc.
        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        # Remove trailing ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        return "\n".join(lines)

    def _copy_build_config(self):
        """Copy webpack and TypeScript config from existing plugin."""
        # Look for config in sibling plugin directories
        existing_plugin = PROJECT_ROOT / "plugins" / "contextcore-chat-panel"
        if not existing_plugin.exists():
            print("  [INFO] No existing plugin to copy config from. Manual setup required.")
            return

        import shutil

        # Copy .config directory
        src_config = existing_plugin / ".config"
        dst_config = self.output_dir / ".config"
        if src_config.exists() and not dst_config.exists():
            shutil.copytree(src_config, dst_config)
            print("  [COPIED] .config/")

        # Copy individual config files
        config_files = ["tsconfig.json", ".eslintrc", ".gitignore"]
        for cf in config_files:
            src = existing_plugin / cf
            dst = self.output_dir / cf
            if src.exists() and not dst.exists():
                shutil.copy(src, dst)
                print(f"  [COPIED] {cf}")


async def main():
    parser = argparse.ArgumentParser(
        description="Scaffold Grafana plugin with contextcore-beaver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/scaffold_plugin.py --plugin-type panel --name contextcore-example-panel
  python scripts/scaffold_plugin.py --plugin-type datasource --name contextcore-example-ds

Requires:
  - pip install contextcore-beaver (or startd8 as fallback)
  - export ANTHROPIC_API_KEY=your-key
        """
    )
    parser.add_argument("--plugin-type", choices=["panel", "datasource", "app"], required=True,
                        help="Type of Grafana plugin to scaffold")
    parser.add_argument("--name", required=True,
                        help="Plugin name (e.g., contextcore-my-panel)")
    parser.add_argument("--output", default=str(OUTPUT_DIR),
                        help="Output directory (default: plugins/)")

    args = parser.parse_args()

    if not BEAVER_AVAILABLE and not STARTD8_AVAILABLE:
        print("[ERROR] LLM SDK required. Install with: pip install contextcore-beaver")
        sys.exit(1)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[ERROR] ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    # Validate plugin name starts with contextcore-
    if not args.name.startswith("contextcore-"):
        print(f"[WARNING] Plugin name should start with 'contextcore-' for consistency")
        print(f"         Suggested: contextcore-{args.name}")

    scaffolder = PluginScaffolder(
        plugin_type=args.plugin_type,
        plugin_name=args.name,
        output_dir=Path(args.output)
    )

    result = await scaffolder.scaffold()

    # Save manifest
    manifest_path = Path(args.output) / args.name / "scaffold-manifest.json"
    manifest_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"Manifest saved: {manifest_path}")


if __name__ == "__main__":
    asyncio.run(main())
