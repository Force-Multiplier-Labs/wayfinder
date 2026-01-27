#!/usr/bin/env python3
"""
Unified emitter for ContextCore Squirrel.
Emits both lessons learned and knowledge items to Tempo.

Usage:
    python squirrel_emit_all.py \\
        --lessons ~/Documents/craft/Lessons_Learned/ \\
        --knowledge ./skills/dev-tour-guide/index/

    python squirrel_emit_all.py --lessons ~/Documents/craft/Lessons_Learned/
    python squirrel_emit_all.py --knowledge ./skills/dev-tour-guide/index/
    python squirrel_emit_all.py --lessons ... --knowledge ... --dry-run
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional

# Environment setup BEFORE imports to ensure OTEL configuration
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

try:
    from lessons_learned_emitter import LessonsEmitter
    from lessons_learned_parser import parse_all_domains, to_dict
    from squirrel_knowledge_emitter import SquirrelEmitter
    from squirrel_knowledge_parser import parse_capability_index
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    print("Please ensure all emitter and parser modules are installed and accessible.", file=sys.stderr)
    sys.exit(1)


def validate_paths(lessons_path_str: Optional[str], knowledge_path_str: Optional[str]) -> Tuple[bool, bool]:
    """
    Validate provided paths and return availability flags.
    
    Args:
        lessons_path_str: Optional path string to lessons directory
        knowledge_path_str: Optional path string to knowledge directory
        
    Returns:
        Tuple of (lessons_available, knowledge_available) booleans
    """
    lessons_available = False
    knowledge_available = False

    if lessons_path_str:
        lessons_path = Path(lessons_path_str).resolve()
        if not lessons_path.exists():
            print(f"Warning: Lessons path '{lessons_path}' does not exist. Skipping lessons.", file=sys.stderr)
        elif not lessons_path.is_dir():
            print(f"Warning: Lessons path '{lessons_path}' is not a directory. Skipping lessons.", file=sys.stderr)
        else:
            lessons_available = True
    else:
        print("Info: No lessons path provided. Skipping lessons.", file=sys.stderr)

    if knowledge_path_str:
        knowledge_path = Path(knowledge_path_str).resolve()
        if not knowledge_path.exists():
            print(f"Warning: Knowledge path '{knowledge_path}' does not exist. Skipping knowledge.", file=sys.stderr)
        elif not knowledge_path.is_dir():
            print(f"Warning: Knowledge path '{knowledge_path}' is not a directory. Skipping knowledge.", file=sys.stderr)
        else:
            knowledge_available = True
    else:
        print("Info: No knowledge path provided. Skipping knowledge.", file=sys.stderr)

    return lessons_available, knowledge_available


def emit_lessons(lessons_path: Path, endpoint: str, dry_run: bool) -> Dict:
    """
    Emit lessons learned and return statistics.

    Args:
        lessons_path: Path to lessons directory
        endpoint: OTEL endpoint for emission
        dry_run: Whether to perform dry run

    Returns:
        Dictionary with emission statistics
    """
    print(f"\n--- Processing Lessons Learned from: {lessons_path} ---")
    stats = {"emitted": 0, "failed": 0, "errors": []}

    try:
        # parse_all_domains returns list of LessonDomain objects
        domains = parse_all_domains(lessons_path)

        if not domains:
            print(f"Info: No lesson domains found in '{lessons_path}'.")
            return stats

        # Extract all lessons from domains -> legs -> lessons
        all_lessons = []
        for domain in domains:
            for leg in getattr(domain, 'legs', []):
                for lesson in getattr(leg, 'lessons', []):
                    all_lessons.append(lesson)

        total_lessons = len(all_lessons)
        print(f"Found {len(domains)} domains with {total_lessons} total lessons.")

        if total_lessons == 0:
            print(f"Info: No individual lessons found.")
            return stats

        if dry_run:
            print("Dry run: Would emit the following lessons:")
            for i, lesson in enumerate(all_lessons[:10]):  # Show first 10
                title = getattr(lesson, 'title', 'Untitled')
                domain = getattr(lesson, 'domain', 'unknown')
                print(f"  {i+1}. [{domain}] {title}")
            if total_lessons > 10:
                print(f"  ... and {total_lessons - 10} more")
            stats["emitted"] = total_lessons
            return stats

        lessons_emitter = LessonsEmitter(endpoint)

        for i, lesson in enumerate(all_lessons):
            try:
                lesson_dict = to_dict(lesson) if not isinstance(lesson, dict) else lesson

                success = lessons_emitter.emit_lesson(lesson_dict)
                if success:
                    stats["emitted"] += 1
                else:
                    stats["failed"] += 1
                    title = lesson_dict.get('title', 'Untitled')
                    error_msg = f"Failed to emit lesson {i+1}: '{title}'"
                    stats["errors"].append(error_msg)
            except Exception as e:
                stats["failed"] += 1
                error_msg = f"Error processing lesson {i+1}: {e}"
                stats["errors"].append(error_msg)

        print(f"  ✓ Emitted {stats['emitted']} lessons")
        if stats["failed"] > 0:
            print(f"  ✗ Failed: {stats['failed']}")

    except Exception as e:
        error_msg = f"Error processing lessons directory: {e}"
        stats["failed"] += 1
        stats["errors"].append(error_msg)
        print(f"Error: {error_msg}", file=sys.stderr)

    return stats


def emit_knowledge(knowledge_path: Path, endpoint: str, dry_run: bool) -> Dict:
    """
    Emit knowledge items and return statistics.

    Args:
        knowledge_path: Path to knowledge directory
        endpoint: OTEL endpoint for emission
        dry_run: Whether to perform dry run

    Returns:
        Dictionary with emission statistics
    """
    print(f"\n--- Processing Knowledge Items from: {knowledge_path} ---")
    stats = {"emitted": 0, "failed": 0, "errors": []}

    try:
        # parse_capability_index returns a SquirrelIndex object
        index = parse_capability_index(knowledge_path)
        total_items = index.total_items()

        if total_items == 0:
            print(f"Info: No knowledge items found in '{knowledge_path}'.")
            return stats

        print(f"Found {total_items} knowledge items to process.")
        print(f"  Endpoints: {len(index.endpoints)}")
        print(f"  Skills: {len(index.skills)}")
        print(f"  Tools: {len(index.tools)}")
        print(f"  Workflows: {len(index.workflows)}")
        print(f"  Processes: {len(index.processes)}")
        print(f"  Projects: {len(index.projects)}")

        if dry_run:
            print("\nDry run: Would emit the above knowledge items.")
            stats["emitted"] = total_items
            return stats

        # Use SquirrelEmitter to emit the entire index
        knowledge_emitter = SquirrelEmitter(endpoint=endpoint, dry_run=False)

        try:
            knowledge_emitter.emit_index(index)
            emitter_stats = knowledge_emitter.get_stats()
            stats["emitted"] = emitter_stats["total_spans"]
            print(f"  ✓ Emitted {stats['emitted']} spans")
        except Exception as e:
            stats["failed"] += 1
            error_msg = f"Error emitting knowledge index: {e}"
            stats["errors"].append(error_msg)
            print(f"  ✗ {error_msg}", file=sys.stderr)
        finally:
            knowledge_emitter.shutdown()

    except Exception as e:
        error_msg = f"Error processing knowledge directory: {e}"
        stats["failed"] += 1
        stats["errors"].append(error_msg)
        print(f"Error: {error_msg}", file=sys.stderr)

    return stats


def print_combined_stats(stats: Dict) -> None:
    """Print formatted combined statistics for both emission types."""
    print("\n" + "="*50)
    print("           Combined Emission Statistics")
    print("="*50)

    lessons_stats = stats["lessons"]
    knowledge_stats = stats["knowledge"]

    print(f"\nLessons Learned:")
    print(f"  Emitted: {lessons_stats['emitted']}")
    print(f"  Failed:  {lessons_stats['failed']}")

    print(f"\nKnowledge Items:")
    print(f"  Emitted: {knowledge_stats['emitted']}")
    print(f"  Failed:  {knowledge_stats['failed']}")

    total_emitted = lessons_stats["emitted"] + knowledge_stats["emitted"]
    total_failed = lessons_stats["failed"] + knowledge_stats["failed"]

    print("\n" + "-"*50)
    print(f"Total Emitted:     {total_emitted}")
    print(f"Total Failed:      {total_failed}")
    print("-" * 50)

    # Show detailed errors if any occurred
    all_errors = lessons_stats.get("errors", []) + knowledge_stats.get("errors", [])
    if all_errors:
        print(f"\nErrors encountered ({len(all_errors)}):")
        for i, err in enumerate(all_errors[:10]):  # Limit to first 10 errors
            print(f"  {i+1}. {err}")
        if len(all_errors) > 10:
            print(f"  ... and {len(all_errors) - 10} more errors")

    if total_failed > 0:
        print("\n⚠️  Some operations failed. Review error messages above.")
    else:
        print("\n✅ All operations completed successfully.")


def main() -> None:
    """Main entry point with argument parsing and orchestration."""
    parser = argparse.ArgumentParser(
        description="Unified emitter for ContextCore Squirrel. Emits both lessons learned and knowledge items to Tempo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --lessons ~/Documents/craft/Lessons_Learned/ --knowledge ./skills/dev-tour-guide/index/
  %(prog)s --lessons ~/Documents/craft/Lessons_Learned/
  %(prog)s --knowledge ./skills/dev-tour-guide/index/
  %(prog)s --lessons ... --knowledge ... --dry-run
        """
    )
    parser.add_argument(
        "--lessons",
        type=str,
        help="Path to directory containing lessons learned markdown files",
        default=None
    )
    parser.add_argument(
        "--knowledge",
        type=str,
        help="Path to directory containing knowledge items (capability index)",
        default=None
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        help="OTEL Collector endpoint for emitting telemetry data (default: %(default)s)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run - show what would be emitted without sending data"
    )

    args = parser.parse_args()

    # Validate that at least one path is provided
    if not any([args.lessons, args.knowledge]):
        print("Error: At least one of --lessons or --knowledge must be provided.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Validate paths
    lessons_available, knowledge_available = validate_paths(args.lessons, args.knowledge)

    # Exit if no valid paths
    if not lessons_available and not knowledge_available:
        print("\nError: No valid paths provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Set up OTEL endpoint
    if args.endpoint:
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = args.endpoint
        print(f"OTEL endpoint: {args.endpoint}")

    # Initialize combined statistics
    combined_stats = {
        "lessons": {"emitted": 0, "failed": 0, "errors": []},
        "knowledge": {"emitted": 0, "failed": 0, "errors": []},
    }

    exit_code = 0

    try:
        # Process lessons if available
        if lessons_available:
            lessons_stats = emit_lessons(Path(args.lessons).resolve(), args.endpoint, args.dry_run)
            combined_stats["lessons"] = lessons_stats
            if lessons_stats["failed"] > 0:
                exit_code = 2  # Partial failure

        # Process knowledge if available
        if knowledge_available:
            knowledge_stats = emit_knowledge(Path(args.knowledge).resolve(), args.endpoint, args.dry_run)
            combined_stats["knowledge"] = knowledge_stats
            if knowledge_stats["failed"] > 0:
                exit_code = 2  # Partial failure

    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nUnhandled error during execution: {e}", file=sys.stderr)
        exit_code = 1

    # Print final statistics
    print_combined_stats(combined_stats)

    # Determine final exit code
    total_emitted = combined_stats["lessons"]["emitted"] + combined_stats["knowledge"]["emitted"]
    total_failed = combined_stats["lessons"]["failed"] + combined_stats["knowledge"]["failed"]

    if total_failed > 0 and total_emitted == 0:
        exit_code = 1  # Complete failure
    elif total_failed > 0:
        exit_code = 2  # Partial success
    else:
        exit_code = 0  # Success

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
