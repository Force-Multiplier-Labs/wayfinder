"""
Unified emitter for ContextCore Squirrel.
Emits both lessons learned and knowledge items to Tempo.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter
from contextcore_squirrel.knowledge_parser import parse_capability_index
from contextcore_squirrel.lessons_emitter import LessonsEmitter
from contextcore_squirrel.lessons_parser import parse_all_domains, to_dict

logger = logging.getLogger(__name__)


def validate_paths(
    lessons_path_str: Optional[str], knowledge_path_str: Optional[str]
) -> Tuple[bool, bool]:
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
            logger.warning(f"Lessons path '{lessons_path}' does not exist. Skipping lessons.")
        elif not lessons_path.is_dir():
            logger.warning(f"Lessons path '{lessons_path}' is not a directory. Skipping lessons.")
        else:
            lessons_available = True
    else:
        logger.info("No lessons path provided. Skipping lessons.")

    if knowledge_path_str:
        knowledge_path = Path(knowledge_path_str).resolve()
        if not knowledge_path.exists():
            logger.warning(
                f"Knowledge path '{knowledge_path}' does not exist. Skipping knowledge."
            )
        elif not knowledge_path.is_dir():
            logger.warning(
                f"Knowledge path '{knowledge_path}' is not a directory. Skipping knowledge."
            )
        else:
            knowledge_available = True
    else:
        logger.info("No knowledge path provided. Skipping knowledge.")

    return lessons_available, knowledge_available


def emit_lessons(lessons_path: Path, endpoint: str, dry_run: bool) -> Dict:
    """
    Emit lessons learned with domain→leg→lesson hierarchy and return statistics.

    Args:
        lessons_path: Path to lessons directory
        endpoint: OTEL endpoint for emission
        dry_run: Whether to perform dry run

    Returns:
        Dictionary with emission statistics
    """
    logger.info(f"Processing Lessons Learned from: {lessons_path}")
    stats: Dict = {"emitted": 0, "failed": 0, "errors": []}

    try:
        domains = parse_all_domains(lessons_path)

        if not domains:
            logger.info(f"No lesson domains found in '{lessons_path}'.")
            return stats

        total_lessons = sum(d.lesson_count for d in domains)
        logger.info(f"Found {len(domains)} domains with {total_lessons} total lessons.")

        if total_lessons == 0:
            logger.info("No individual lessons found.")
            return stats

        # Convert to dicts for the emitter
        domains_data = [to_dict(d) for d in domains]

        # Use emit_all which preserves domain→leg→lesson hierarchy
        emitter = LessonsEmitter(endpoint=endpoint, dry_run=dry_run)
        try:
            emitter_stats = emitter.emit_all(domains_data)
            stats["emitted"] = emitter_stats["lessons_emitted"]
        finally:
            emitter.shutdown()

        logger.info(f"Emitted {stats['emitted']} lessons across {len(domains)} domains")

    except Exception as e:
        error_msg = f"Error processing lessons directory: {e}"
        stats["failed"] += 1
        stats["errors"].append(error_msg)
        logger.error(error_msg)

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
    logger.info(f"Processing Knowledge Items from: {knowledge_path}")
    stats: Dict = {"emitted": 0, "failed": 0, "errors": []}

    try:
        index = parse_capability_index(knowledge_path)
        total_items = index.total_items()

        if total_items == 0:
            logger.info(f"No knowledge items found in '{knowledge_path}'.")
            return stats

        logger.info(f"Found {total_items} knowledge items to process.")

        if dry_run:
            logger.info("Dry run: Would emit the above knowledge items.")
            stats["emitted"] = total_items
            return stats

        knowledge_emitter = KnowledgeEmitter(endpoint=endpoint, dry_run=False)

        try:
            knowledge_emitter.emit_index(index)
            emitter_stats = knowledge_emitter.get_stats()
            stats["emitted"] = emitter_stats["total_spans"]
            logger.info(f"Emitted {stats['emitted']} spans")
        except Exception as e:
            stats["failed"] += 1
            error_msg = f"Error emitting knowledge index: {e}"
            stats["errors"].append(error_msg)
            logger.error(error_msg)
        finally:
            knowledge_emitter.shutdown()

    except Exception as e:
        error_msg = f"Error processing knowledge directory: {e}"
        stats["failed"] += 1
        stats["errors"].append(error_msg)
        logger.error(error_msg)

    return stats


def emit_all(
    lessons_path: Optional[str] = None,
    knowledge_path: Optional[str] = None,
    endpoint: str = "http://localhost:4317",
    dry_run: bool = False,
) -> Dict:
    """
    Emit both lessons and knowledge items.

    Args:
        lessons_path: Path to lessons directory
        knowledge_path: Path to knowledge directory
        endpoint: OTEL endpoint
        dry_run: Whether to perform dry run

    Returns:
        Combined statistics dictionary
    """
    lessons_available, knowledge_available = validate_paths(lessons_path, knowledge_path)

    combined_stats: Dict = {
        "lessons": {"emitted": 0, "failed": 0, "errors": []},
        "knowledge": {"emitted": 0, "failed": 0, "errors": []},
    }

    if lessons_available:
        combined_stats["lessons"] = emit_lessons(
            Path(lessons_path).resolve(), endpoint, dry_run
        )

    if knowledge_available:
        combined_stats["knowledge"] = emit_knowledge(
            Path(knowledge_path).resolve(), endpoint, dry_run
        )

    return combined_stats
