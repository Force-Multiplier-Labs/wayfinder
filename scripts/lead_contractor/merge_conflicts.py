#!/usr/bin/env python3
"""
Merge conflicts by combining multiple generated files into target files.

This script intelligently merges conflicting files based on their content.
"""
import sys
from pathlib import Path
from typing import List, Dict

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.lead_contractor.integrate_backlog import (
    scan_backlog, generate_integration_plan, clean_markdown_code_blocks
)

def _merge_python_sources(sources: List[Dict], label: str = "files") -> str:
    """
    Shared AST merge for all Python source types.

    Uses AST-based merging to properly handle:
    - Decorators attached to classes (@dataclass)
    - Class dependency ordering (MessageRole before Message)
    - Multi-line strings and docstrings
    - Import deduplication with __future__ first

    Legacy text-based fallback is disabled — it corrupts files.
    """
    try:
        from scripts.lead_contractor.ast_merge import parse_python_file, merge_parsed_files
    except ImportError as e:
        print(f"  ERROR: AST merge module not available ({e})")
        print(f"  Legacy merge disabled — it corrupts files. Fix the import error.")
        return ""

    parsed_files = []
    for src in sources:
        src_path = Path(src['source'])
        if not src_path.exists():
            continue
        try:
            parsed_files.append(parse_python_file(src_path))
        except SyntaxError as e:
            print(f"  Warning: Skipping {src_path.name} due to syntax error: {e}")

    if not parsed_files:
        return ""

    try:
        result = merge_parsed_files(parsed_files)
    except Exception as e:
        print(f"  ERROR: AST merge failed for {label} ({e})")
        print(f"  Legacy merge disabled — it corrupts files. Fix the AST error.")
        return ""

    for warning in result.warnings:
        print(f"  Warning: {warning}")

    return result.content


def merge_parts_files(sources: List[Dict]) -> str:
    """Merge multiple parts-related files into a single parts.py file."""
    return _merge_python_sources(sources, label="parts")


def merge_otel_genai_files(sources: List[Dict]) -> str:
    """Merge OTel GenAI files using AST-based merge."""
    return _merge_python_sources(sources, label="otel_genai")


def merge_handoff_files(sources: List[Dict]) -> str:
    """Merge handoff files using AST-based merge."""
    return _merge_python_sources(sources, label="handoff")

def merge_installtracking_statefile_files(sources: List[Dict]) -> str:
    """
    Merge install tracking statefile - use the larger/more complete one.
    """
    files_content = []
    for src in sources:
        src_path = Path(src['source'])
        if src_path.exists():
            with open(src_path, 'r', encoding='utf-8') as f:
                content = clean_markdown_code_blocks(f.read())
                files_content.append((src['feature'], len(content), content))
    
    if files_content:
        files_content.sort(key=lambda x: x[1], reverse=True)
        return files_content[0][2]
    
    return ""

def main():
    """Main merge function."""
    files = scan_backlog()
    plan = generate_integration_plan(files)
    
    conflicts = plan.get('conflicts', {})
    duplicate_targets = plan.get('duplicate_targets', {})
    
    if not conflicts:
        print("No conflicts to merge!")
        return
    
    print(f"Found {len(conflicts)} conflict(s) to merge\n")
    
    # Merge each conflict
    merged_files = {}
    
    for target_str, conflict_info in conflicts.items():
        target_path = Path(target_str)
        sources = duplicate_targets.get(target_str, [])
        
        print(f"Merging: {target_path.relative_to(PROJECT_ROOT)}")
        print(f"  Sources: {len(sources)} files")
        
        # Choose merge strategy based on target
        target_name = target_path.name
        
        if target_name == 'parts.py':
            merged_content = merge_parts_files(sources)
        elif target_name == 'otel_genai.py':
            merged_content = merge_otel_genai_files(sources)
        elif target_name == 'handoff.py':
            merged_content = merge_handoff_files(sources)
        elif 'installtracking_statefile' in target_name:
            merged_content = merge_installtracking_statefile_files(sources)
        else:
            # Default: use largest file
            files_content = []
            for src in sources:
                src_path = Path(src['source'])
                if src_path.exists():
                    with open(src_path, 'r', encoding='utf-8') as f:
                        content = clean_markdown_code_blocks(f.read())
                        files_content.append((len(content), content))
            
            if files_content:
                files_content.sort(key=lambda x: x[0], reverse=True)
                merged_content = files_content[0][1]
            else:
                merged_content = ""
        
        if merged_content:
            merged_files[target_path] = merged_content
            print(f"  ✓ Merged {len(merged_content)} bytes")
        else:
            print(f"  ✗ Failed to merge")
    
    # Write merged files
    print(f"\nWriting {len(merged_files)} merged file(s)...")
    for target_path, content in merged_files.items():
        # Create backup
        if target_path.exists():
            backup = target_path.with_suffix(f"{target_path.suffix}.backup")
            import shutil
            shutil.copy2(target_path, backup)
            print(f"  Backed up: {backup.name}")
        
        # Write merged content
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Wrote: {target_path.relative_to(PROJECT_ROOT)}")

if __name__ == '__main__':
    main()
