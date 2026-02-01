#!/usr/bin/env python3
"""Import pending tasks from the offline task store into ContextCore.

Usage:
    python3 scripts/import_pending_tasks.py /path/to/pending_tasks.json

Environment:
    OTEL_EXPORTER_OTLP_ENDPOINT - OTLP endpoint (default: http://localhost:4317)
"""

import json
import os
import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from contextcore.tracker import TaskTracker


def import_tasks(json_file: Path):
    """Import tasks from a pending_tasks.json file."""
    with open(json_file) as f:
        data = json.load(f)
    
    project_id = data["project"]["id"]
    project_name = data["project"]["name"]
    
    print(f"\n🕷️  Importing tasks for: {project_name}")
    print(f"   Project ID: {project_id}")
    print(f"   Tasks: {len(data['spans'])}")
    print()
    
    tracker = TaskTracker(project=project_id)
    default_author = os.environ.get("USER", "importer")
    
    # Build parent map for hierarchy
    parent_map = {}
    for span in data["spans"]:
        if "parent_span_id" in span:
            parent_map[span["span_id"]] = span["parent_span_id"]
    
    # Import each task
    imported = 0
    for span in data["spans"]:
        attrs = span["attributes"]
        task_id = attrs["task.id"]
        title = attrs["task.title"]
        task_type = attrs.get("task.type", "task")
        status = attrs.get("task.status", "pending")
        description = attrs.get("task.description", "")
        blocked_by = attrs.get("task.blocked_by", [])
        
        # Map status to ContextCore status
        status_map = {
            "pending": "backlog",
            "in_progress": "in_progress",
            "completed": "done",
            "cancelled": "cancelled"
        }
        mapped_status = status_map.get(status, "backlog")
        
        # Find parent task ID if exists
        parent_task_id = None
        if "parent_span_id" in span:
            # Find the parent span's task ID
            for s in data["spans"]:
                if s["span_id"] == span["parent_span_id"]:
                    parent_task_id = s["attributes"]["task.id"]
                    break
        
        try:
            # Build kwargs, excluding None values
            kwargs = {
                "task_id": task_id,
                "title": title,
                "task_type": task_type,
                "status": mapped_status,
            }
            if parent_task_id:
                kwargs["parent_id"] = parent_task_id
            if blocked_by:
                kwargs["depends_on"] = blocked_by
            
            tracker.start_task(**kwargs)
            
            if description:
                tracker.add_comment(task_id, author=default_author, text=description)

            status_icon = "🟡" if status == "in_progress" else "⚪"
            print(f"  {status_icon} {task_id}: {title[:50]}...")
            imported += 1
            
        except Exception as e:
            print(f"  ❌ {task_id}: {e}")
    
    print(f"\n✅ Imported {imported}/{len(data['spans'])} tasks to project '{project_id}'")
    return imported


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable task files:")
        task_store = Path.home() / "Documents/pers/persOS/context-core"
        if task_store.exists():
            for project_dir in task_store.iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith("."):
                    for json_file in project_dir.glob("*_pending_tasks.json"):
                        print(f"  {json_file}")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"❌ File not found: {json_file}")
        sys.exit(1)
    
    import_tasks(json_file)


if __name__ == "__main__":
    main()
