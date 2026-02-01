#!/usr/bin/env python3
"""
Dashboard Reorganization CLI Tool

Reorganizes Grafana dashboards from flat json/ folder into extension-specific folders
with updated UIDs following the contextcore-{extension}-{name} format.
"""

import json
import os
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import click
from pydantic import BaseModel, Field, ValidationError

__all__ = [
    'ExtensionType', 'DashboardInfo', 'DashboardConfig', 'DashboardAnalyzer',
    'UIDGenerator', 'DashboardReorganizer', 'cli'
]


class ExtensionType(str, Enum):
    """Enumeration of supported extension types."""
    CORE = "core"
    SQUIRREL = "squirrel"
    RABBIT = "rabbit"
    BEAVER = "beaver"
    FOX = "fox"
    COYOTE = "coyote"
    OWL = "owl"  # contextcore-owl: Grafana plugins
    EXTERNAL = "external"


@dataclass
class DashboardInfo:
    """Information about a dashboard file."""
    original_path: Path
    filename: str
    title: str
    uid: str
    extension: ExtensionType
    new_uid: str
    tags: List[str] = None


class DashboardConfig(BaseModel):
    """Pydantic model for dashboard JSON structure validation."""
    uid: str
    title: str
    tags: Optional[List[str]] = Field(default_factory=list)
    panels: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class DashboardAnalyzer:
    """Analyzes dashboard content to determine extension category."""

    # Explicit filename-to-extension mapping for known dashboards
    EXPLICIT_MAPPINGS = {
        # Core dashboards
        "portfolio.json": ExtensionType.CORE,
        "installation.json": ExtensionType.CORE,
        "project-progress.json": ExtensionType.CORE,
        "project-operations.json": ExtensionType.CORE,
        "sprint-metrics.json": ExtensionType.CORE,
        # Squirrel (skills library)
        "skills-browser.json": ExtensionType.SQUIRREL,
        "value-capabilities.json": ExtensionType.SQUIRREL,
        # Rabbit (alert automation)
        "workflow.json": ExtensionType.RABBIT,
        # Beaver (LLM abstraction)
        "beaver-lead-contractor-progress.json": ExtensionType.BEAVER,
        # Fox (context enrichment)
        "fox-alert-automation.json": ExtensionType.FOX,
        # External
        "agent-trigger.json": ExtensionType.EXTERNAL,
    }

    def __init__(self):
        # Keywords mapped to each extension type for detection (fallback)
        self.extension_keywords = {
            ExtensionType.CORE: ["portfolio", "installation", "progress", "operations", "sprint", "overview"],
            ExtensionType.SQUIRREL: ["squirrel", "skills", "value", "capabilities"],
            ExtensionType.RABBIT: ["rabbit", "workflow", "queue", "message", "trigger"],
            ExtensionType.BEAVER: ["beaver", "contractor", "llm", "provider"],
            ExtensionType.FOX: ["fox", "alert", "automation", "context"],
            ExtensionType.COYOTE: ["coyote", "agent", "pipeline", "incident"],
            ExtensionType.OWL: ["owl", "grafana", "plugin", "panel", "datasource", "chat"],
        }
    
    def detect_extension(self, dashboard_data: Dict[str, Any], filename: str) -> ExtensionType:
        """
        Detect extension type based on dashboard content.

        Uses multiple analysis methods in order of preference:
        1. Explicit filename mapping (most reliable)
        2. Filename keyword analysis
        3. Title analysis
        4. Tags analysis
        5. Panel content analysis
        """
        # First check explicit mappings
        if filename in self.EXPLICIT_MAPPINGS:
            return self.EXPLICIT_MAPPINGS[filename]

        # Analyze using various metrics in order of specificity
        extension = self._analyze_filename(filename)
        if extension:
            return extension

        extension = self._analyze_title(dashboard_data.get('title', ''))
        if extension:
            return extension

        extension = self._analyze_tags(dashboard_data.get('tags', []))
        if extension:
            return extension

        extension = self._analyze_panels(dashboard_data.get('panels', []))
        if extension:
            return extension

        # Default to external if no specific extension detected
        return ExtensionType.EXTERNAL

    def _analyze_filename(self, filename: str) -> Optional[ExtensionType]:
        """Analyze filename for extension hints."""
        filename_lower = filename.lower()
        for ext_type, keywords in self.extension_keywords.items():
            if any(keyword in filename_lower for keyword in keywords):
                return ext_type
        return None

    def _analyze_title(self, title: str) -> Optional[ExtensionType]:
        """Analyze dashboard title for extension hints."""
        title_lower = title.lower()
        for ext_type, keywords in self.extension_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return ext_type
        return None

    def _analyze_tags(self, tags: List[str]) -> Optional[ExtensionType]:
        """Analyze dashboard tags for extension hints."""
        if not tags:
            return None
            
        for tag in tags:
            tag_lower = tag.lower()
            for ext_type, keywords in self.extension_keywords.items():
                if any(keyword in tag_lower for keyword in keywords):
                    return ext_type
        return None
    
    def _analyze_panels(self, panels: List[Dict[str, Any]]) -> Optional[ExtensionType]:
        """Analyze panel queries and titles for extension hints."""
        if not panels:
            return None
            
        for panel in panels:
            # Check panel title
            title = panel.get('title', '').lower()
            for ext_type, keywords in self.extension_keywords.items():
                if any(keyword in title for keyword in keywords):
                    return ext_type
                    
            # Check panel targets/queries for datasource hints
            targets = panel.get('targets', [])
            for target in targets:
                if isinstance(target, dict):
                    expr = target.get('expr', '').lower()
                    for ext_type, keywords in self.extension_keywords.items():
                        if any(keyword in expr for keyword in keywords):
                            return ext_type
        return None


class UIDGenerator:
    """Generates new UIDs in contextcore-{extension}-{name} format."""
    
    def __init__(self):
        self.used_uids: set[str] = set()
    
    def generate_uid(self, extension: ExtensionType, name: str) -> str:
        """
        Generate unique UID for dashboard.
        
        Format: contextcore-{extension}-{sanitized_name}
        Handles duplicates by appending numeric suffix.
        """
        sanitized_name = self._sanitize_name(name)
        base_uid = f"contextcore-{extension.value}-{sanitized_name}"
        
        # Check if UID is already used
        if base_uid not in self.used_uids:
            self.used_uids.add(base_uid)
            return base_uid
        
        # Handle duplicates with numeric suffix
        counter = 2
        while f"{base_uid}-{counter}" in self.used_uids:
            counter += 1
        
        final_uid = f"{base_uid}-{counter}"
        self.used_uids.add(final_uid)
        return final_uid
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize name for use in UID.
        
        Converts non-alphanumeric characters to hyphens and removes
        leading/trailing hyphens.
        """
        # Replace non-alphanumeric chars with hyphens, collapse multiple hyphens
        sanitized = ''.join(c if c.isalnum() else '-' for c in name.lower())
        # Remove multiple consecutive hyphens and strip leading/trailing hyphens
        sanitized = '-'.join(part for part in sanitized.split('-') if part)
        return sanitized[:50]  # Limit length to avoid overly long UIDs


class DashboardReorganizer:
    """Main class for reorganizing dashboards."""
    
    def __init__(self, source_dir: Path, target_dir: Path):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.analyzer = DashboardAnalyzer()
        self.uid_generator = UIDGenerator()
        self.mapping_log: List[Tuple[str, str]] = []  # (old_uid, new_uid) pairs
    
    def reorganize(self, dry_run: bool = True) -> Dict[str, List[str]]:
        """
        Main reorganization method.
        
        Returns dictionary mapping extension names to lists of dashboard UIDs.
        """
        click.echo(f"{'DRY RUN: ' if dry_run else ''}Reorganizing dashboards...")
        click.echo(f"Source: {self.source_dir}")
        click.echo(f"Target: {self.target_dir}")
        
        # Create target directories
        if not dry_run:
            self._create_directories()
        
        dashboard_infos = []
        total_processed = 0
        errors = 0

        # Scan and analyze all dashboard files
        dashboard_files = self._scan_dashboards()
        click.echo(f"Found {len(dashboard_files)} dashboard files to process")

        for dashboard_file in dashboard_files:
            try:
                dashboard_info = self._analyze_dashboard(dashboard_file)
                dashboard_infos.append(dashboard_info)
                total_processed += 1
                
                # Show progress for each dashboard
                click.echo(f"  {dashboard_info.filename} -> {dashboard_info.extension.value}/ "
                          f"(UID: {dashboard_info.new_uid})")
                
            except (ValidationError, json.JSONDecodeError, KeyError) as e:
                click.echo(f"Warning: Skipping {dashboard_file} - {str(e)}", err=True)
                errors += 1
                continue
            except Exception as e:
                click.echo(f"Error processing {dashboard_file}: {str(e)}", err=True)
                errors += 1
                continue
        
        # Process dashboards (move files and update content)
        if not dry_run and dashboard_infos:
            click.echo("Moving and updating dashboards...")
            for dashboard_info in dashboard_infos:
                try:
                    self._process_dashboard(dashboard_info)
                except Exception as e:
                    click.echo(f"Error processing {dashboard_info.filename}: {str(e)}", err=True)
                    errors += 1
            
            # Write mapping log
            self._write_mapping_log()
        
        # Generate summary report
        results = self._generate_summary(dashboard_infos)
        
        click.echo(f"\nSummary:")
        click.echo(f"  Processed: {total_processed} dashboards")
        click.echo(f"  Errors: {errors}")
        
        for ext_name, uids in results.items():
            click.echo(f"  {ext_name}: {len(uids)} dashboards")
        
        return results
    
    def _scan_dashboards(self) -> List[Path]:
        """Scan source directory for dashboard JSON files."""
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Source directory {self.source_dir} does not exist")
        
        json_files = list(self.source_dir.glob('*.json'))
        if not json_files:
            click.echo("Warning: No JSON files found in source directory", err=True)
        
        return json_files
    
    def _analyze_dashboard(self, file_path: Path) -> DashboardInfo:
        """Analyze single dashboard file and extract metadata."""
        try:
            with file_path.open('r', encoding='utf-8') as f:
                dashboard_data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in {file_path.name}: {str(e)}", "", 0)
        
        if not isinstance(dashboard_data, dict):
            raise ValueError(f"Dashboard data must be a JSON object in {file_path.name}")
        
        # Extract dashboard metadata
        title = dashboard_data.get('title', 'Untitled Dashboard')
        if not title or not isinstance(title, str):
            title = f"Dashboard-{file_path.stem}"
        
        original_uid = dashboard_data.get('uid', '')
        extension = self.analyzer.detect_extension(dashboard_data, file_path.name)
        new_uid = self.uid_generator.generate_uid(extension, title)
        tags = dashboard_data.get('tags', []) if isinstance(dashboard_data.get('tags'), list) else []
        
        return DashboardInfo(
            original_path=file_path,
            filename=file_path.name,
            title=title,
            uid=original_uid,
            extension=extension,
            new_uid=new_uid,
            tags=tags
        )
    
    def _create_directories(self):
        """Create extension-specific directories in target location."""
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        for ext in ExtensionType:
            target_path = self.target_dir / ext.value
            target_path.mkdir(parents=True, exist_ok=True)
    
    def _process_dashboard(self, dashboard_info: DashboardInfo):
        """Process single dashboard: update UID/title and move file."""
        # Read and update dashboard JSON
        with dashboard_info.original_path.open('r', encoding='utf-8') as f:
            dashboard_data = json.load(f)
        
        # Update UID and optionally title with extension prefix
        old_uid = dashboard_data.get('uid', '')
        dashboard_data['uid'] = dashboard_info.new_uid
        
        # Add extension prefix to title if not already present
        current_title = dashboard_data.get('title', '')
        ext_prefix = f"[{dashboard_info.extension.value.upper()}]"
        if not current_title.startswith(ext_prefix):
            dashboard_data['title'] = f"{ext_prefix} {current_title}"
        
        # Write to new location
        target_path = self.target_dir / dashboard_info.extension.value / dashboard_info.filename
        with target_path.open('w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        
        # Log the mapping for reference
        self.mapping_log.append((old_uid, dashboard_info.new_uid))
    
    def _write_mapping_log(self):
        """Write UID mapping log to file for reference."""
        if not self.mapping_log:
            return
            
        log_file_path = self.target_dir / "uid_mapping.log"
        with log_file_path.open('w', encoding='utf-8') as log_file:
            log_file.write("# Dashboard UID Mapping Log\n")
            log_file.write("# Format: OLD_UID -> NEW_UID\n\n")
            
            for old_uid, new_uid in self.mapping_log:
                log_file.write(f"{old_uid or 'NO_UID'} -> {new_uid}\n")
        
        click.echo(f"UID mapping log written to: {log_file_path}")
    
    def _generate_summary(self, dashboard_infos: List[DashboardInfo]) -> Dict[str, List[str]]:
        """Generate summary report of reorganization results."""
        results = {}
        
        for ext in ExtensionType:
            matching_dashboards = [
                dashboard_info.new_uid 
                for dashboard_info in dashboard_infos 
                if dashboard_info.extension == ext
            ]
            results[ext.value] = matching_dashboards
        
        return results


@click.group()
def cli():
    """Dashboard reorganization CLI tool."""
    pass


@cli.command()
@click.option('--source', '-s', type=click.Path(path_type=Path),
              default=None,
              help='Source directory containing dashboard JSON files')
@click.option('--target', '-t', type=click.Path(path_type=Path),
              default=None,
              help='Target directory for reorganized dashboards')
@click.option('--dry-run', is_flag=True, default=True,
              help='Preview changes without executing them (default)')
@click.option('--execute', is_flag=True, default=False,
              help='Execute changes (overrides --dry-run)')
def reorganize(source: Optional[Path], target: Optional[Path], dry_run: bool, execute: bool):
    """Reorganize dashboards into extension-specific folders."""

    # Determine script location to find json/ folder
    script_dir = Path(__file__).parent.resolve()

    # Set defaults relative to script location
    if source is None:
        source = script_dir / 'json'
    if target is None:
        target = script_dir

    # Validate source directory
    if not source.is_dir():
        raise click.BadParameter(f"Source directory {source} does not exist")

    # Determine actual dry_run mode
    actual_dry_run = not execute

    # Run reorganization
    reorganizer = DashboardReorganizer(source, target)
    results = reorganizer.reorganize(dry_run=actual_dry_run)

    if actual_dry_run:
        click.echo("\n[DRY RUN] No changes were made. Use --execute to apply changes.")


@cli.command()
@click.option('--source', '-s', type=click.Path(path_type=Path),
              default=None,
              help='Source directory containing dashboard JSON files')
def analyze(source: Optional[Path]):
    """Analyze dashboards and show extension categorization without making changes."""

    script_dir = Path(__file__).parent.resolve()
    if source is None:
        source = script_dir / 'json'

    if not source.is_dir():
        raise click.BadParameter(f"Source directory {source} does not exist")

    analyzer = DashboardAnalyzer()
    uid_generator = UIDGenerator()

    click.echo(f"Analyzing dashboards in: {source}\n")
    click.echo(f"{'Filename':<45} {'Extension':<12} {'New UID'}")
    click.echo("-" * 90)

    for json_file in sorted(source.glob('*.json')):
        try:
            with json_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
            title = data.get('title', json_file.stem)
            extension = analyzer.detect_extension(data, json_file.name)
            new_uid = uid_generator.generate_uid(extension, title)
            click.echo(f"{json_file.name:<45} {extension.value:<12} {new_uid}")
        except Exception as e:
            click.echo(f"{json_file.name:<45} ERROR: {e}", err=True)


if __name__ == '__main__':
    cli()