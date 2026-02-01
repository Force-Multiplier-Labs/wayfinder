"""
Data persistence analysis module for ContextCore.

This module provides tools to analyze project configurations and determine
data persistence requirements with importance scoring. It scans Docker Compose
files, observability configs, state directories, and ContextCore configuration
to identify what data needs to persist and its relative importance.

Example:
    from contextcore.persistence import PersistenceAnalyzer, AnalysisConfig
    from pathlib import Path

    config = AnalysisConfig(project_root=Path("."))
    analyzer = PersistenceAnalyzer(config)

    # Run analysis
    result = await analyzer.analyze_all()

    # Print requirements by importance
    for req in result.requirements:
        print(f"{req.category.value}: {req.path} (importance: {req.importance_score})")
"""
from __future__ import annotations
import logging
import os
import time
import yaml
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
__all__ = ['DataCategory', 'PersistenceRequirement', 'ImportanceWeights', 'AnalysisConfig', 'PersistenceAnalysisResult', 'PersistenceAnalyzer']
logger = logging.getLogger(__name__)

class DataCategory(str, Enum):
    """Categories for different types of persistent data."""
    CRITICAL = 'critical'
    IMPORTANT = 'important'
    CACHE = 'cache'
    TEMPORARY = 'temporary'
    LOGS = 'logs'
    METRICS = 'metrics'
    TRACES = 'traces'

@dataclass
class ImportanceWeights:
    """Weighting factors for importance score calculation."""
    criticality: float = 0.4
    replaceability: float = 0.3
    business_value: float = 0.2
    size_impact: float = 0.1

@dataclass
class AnalysisConfig:
    """Configuration for persistence analysis."""
    project_root: Path
    weights: ImportanceWeights = field(default_factory=ImportanceWeights)
    min_importance_threshold: int = 20
    cache_results: bool = True
    scan_hidden_files: bool = False

@dataclass
class PersistenceRequirement:
    """Model representing a data persistence requirement."""
    path: Path
    category: DataCategory
    importance_score: int
    description: str
    source_config: str
    replaceability: str
    size_estimate: Optional[int] = None
    retention_period: Optional[str] = None
    backup_frequency: Optional[str] = None

@dataclass
class PersistenceAnalysisResult:
    """Complete analysis result with recommendations."""
    requirements: List[PersistenceRequirement]
    total_estimated_size: int
    analysis_timestamp: str
    config_files_scanned: List[str]
    recommendations: List[str]

class PersistenceAnalyzer:
    """
    Main analyzer class for detecting persistence requirements.

    Scans project configurations to identify:
    - Docker Compose volume mounts
    - Observability service storage (Tempo, Loki, Mimir)
    - State directory contents
    - Explicit persistence config in .contextcore.yaml
    """

    def __init__(self, config: AnalysisConfig):
        """
        Initialize the analyzer.

        Args:
            config: Analysis configuration including project root and weights
        """
        self.config = config
        self.requirements: List[PersistenceRequirement] = []
        self.total_estimated_size = 0
        self.config_files_scanned: List[str] = []

    async def analyze_all(self) -> PersistenceAnalysisResult:
        """
        Run complete analysis of all configuration sources.

        Returns:
            PersistenceAnalysisResult with all requirements and recommendations
        """
        logger.info('Starting comprehensive persistence analysis')
        self.requirements = []
        self.total_estimated_size = 0
        self.config_files_scanned = []
        await self._analyze_docker_compose()
        await self._analyze_observability_configs()
        await self._analyze_state_directory()
        await self._analyze_contextcore_config()
        filtered_requirements = [req for req in self.requirements if req.importance_score >= self.config.min_importance_threshold]
        return PersistenceAnalysisResult(requirements=filtered_requirements, total_estimated_size=self.total_estimated_size, analysis_timestamp=time.strftime('%Y-%m-%d %H:%M:%S'), config_files_scanned=self.config_files_scanned, recommendations=self._generate_recommendations(filtered_requirements))

    async def _analyze_docker_compose(self) -> None:
        """Analyze docker-compose.yml for volume mounts and persistence needs."""
        compose_files = ['docker-compose.yml', 'docker-compose.yaml', 'compose.yml']
        docker_compose_path = None
        for filename in compose_files:
            path = self.config.project_root / filename
            if path.exists():
                docker_compose_path = path
                break
        if not docker_compose_path:
            logger.info('No docker-compose file found')
            return
        try:
            with open(docker_compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)
        except (yaml.YAMLError, IOError) as e:
            logger.error(f'Failed to parse {docker_compose_path}: {e}')
            return
        self.config_files_scanned.append(str(docker_compose_path))
        logger.info(f'Analyzing Docker Compose: {docker_compose_path}')
        services = compose_data.get('services', {})
        for service_name, service_config in services.items():
            await self._analyze_service_volumes(service_name, service_config or {})
        volumes = compose_data.get('volumes', {})
        for volume_name, volume_config in volumes.items():
            await self._analyze_named_volume(volume_name, volume_config or {})

    async def _analyze_service_volumes(self, service_name: str, service_config: Dict[str, Any]) -> None:
        """Analyze volumes for a specific Docker service."""
        volumes = service_config.get('volumes', [])
        for volume in volumes:
            if isinstance(volume, str):
                parts = volume.split(':')
                if len(parts) >= 2:
                    host_path, container_path = (parts[0], parts[1])
                else:
                    continue
            elif isinstance(volume, dict):
                host_path = volume.get('source', '')
                container_path = volume.get('target', '')
            else:
                continue
            category = self._classify_service_volume(service_name, container_path)
            importance_score = self._calculate_service_importance(service_name, container_path)
            size_estimate = None
            if host_path.startswith('./') or host_path.startswith('/'):
                full_path = self.config.project_root / host_path.lstrip('./')
                size_estimate = self._estimate_directory_size(full_path)
            requirement = PersistenceRequirement(path=Path(host_path) if host_path else Path(container_path), category=category, importance_score=importance_score, size_estimate=size_estimate, description=f'Docker volume for {service_name} ({container_path})', source_config=f'docker-compose.yml:{service_name}', replaceability=self._determine_replaceability(service_name, container_path))
            self.requirements.append(requirement)
            if size_estimate:
                self.total_estimated_size += size_estimate

    async def _analyze_named_volume(self, volume_name: str, volume_config: Dict[str, Any]) -> None:
        """Analyze a named Docker volume."""
        external = volume_config.get('external', False)
        category = DataCategory.IMPORTANT
        if 'db' in volume_name.lower() or 'database' in volume_name.lower():
            category = DataCategory.CRITICAL
        elif 'cache' in volume_name.lower() or 'tmp' in volume_name.lower():
            category = DataCategory.CACHE
        importance_score = self._calculate_importance_score(criticality=80 if category == DataCategory.CRITICAL else 60, replaceability='difficult' if not external else 'moderate', business_value=70, size_mb=None)
        requirement = PersistenceRequirement(path=Path(f'/var/lib/docker/volumes/{volume_name}'), category=category, importance_score=importance_score, description=f'Docker named volume: {volume_name}', source_config='docker-compose.yml:volumes', replaceability='difficult' if not external else 'moderate')
        self.requirements.append(requirement)

    async def _analyze_observability_configs(self) -> None:
        """Analyze Tempo, Loki, and Mimir configurations for data storage."""
        observability_configs = [('tempo', ['tempo.yaml', 'tempo.yml']), ('loki', ['loki.yaml', 'loki.yml']), ('mimir', ['mimir.yaml', 'mimir.yml'])]
        for service_type, filenames in observability_configs:
            for filename in filenames:
                config_path = self.config.project_root / filename
                if config_path.exists():
                    await self._analyze_observability_config(service_type, config_path)
                    break

    async def _analyze_observability_config(self, service_type: str, config_path: Path) -> None:
        """Analyze observability service configuration for storage requirements."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError) as e:
            logger.error(f'Failed to parse {config_path}: {e}')
            return
        self.config_files_scanned.append(str(config_path))
        category_map = {'tempo': DataCategory.TRACES, 'loki': DataCategory.LOGS, 'mimir': DataCategory.METRICS}
        storage_path = self._extract_storage_path(service_type, config_data)
        requirement = PersistenceRequirement(path=Path(storage_path), category=category_map[service_type], importance_score=70, description=f'{service_type.title()} data storage', source_config=str(config_path), replaceability='moderate')
        self.requirements.append(requirement)

    async def _analyze_state_directory(self) -> None:
        """Analyze state directory for persistent files and their importance."""
        state_dir = self.config.project_root / 'state'
        if not state_dir.exists() or not state_dir.is_dir():
            logger.info('No state directory found')
            return
        self.config_files_scanned.append(str(state_dir))
        logger.info(f'Analyzing state directory: {state_dir}')
        for root, dirs, files in os.walk(state_dir):
            if not self.config.scan_hidden_files:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not self.config.scan_hidden_files and file.startswith('.'):
                    continue
                file_path = Path(root) / file
                await self._analyze_state_file(file_path)

    async def _analyze_state_file(self, file_path: Path) -> None:
        """Analyze individual file in state directory."""
        try:
            file_size = file_path.stat().st_size
            category = self._classify_file_by_extension(file_path)
            importance_score = self._calculate_file_importance(file_path, file_size)
            requirement = PersistenceRequirement(path=file_path, category=category, importance_score=importance_score, size_estimate=file_size, description=f'State file: {file_path.name}', source_config='state directory scan', replaceability=self._determine_file_replaceability(file_path))
            self.requirements.append(requirement)
            self.total_estimated_size += file_size
        except OSError as e:
            logger.warning(f'Could not analyze file {file_path}: {e}')

    async def _analyze_contextcore_config(self) -> None:
        """Analyze .contextcore.yaml for explicit persistence configuration."""
        contextcore_path = self.config.project_root / '.contextcore.yaml'
        if not contextcore_path.exists():
            logger.info('No .contextcore.yaml file found')
            return
        try:
            with open(contextcore_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError) as e:
            logger.error(f'Failed to parse .contextcore.yaml: {e}')
            return
        self.config_files_scanned.append(str(contextcore_path))
        logger.info('Analyzing .contextcore.yaml configuration')
        persistence_config = config_data.get('persistence', {})
        critical_paths = persistence_config.get('critical_paths', [])
        for path_config in critical_paths:
            if isinstance(path_config, str):
                path_config = {'path': path_config}
            await self._process_contextcore_path(path_config, DataCategory.CRITICAL)
        cache_paths = persistence_config.get('cache_paths', [])
        for path_config in cache_paths:
            if isinstance(path_config, str):
                path_config = {'path': path_config}
            await self._process_contextcore_path(path_config, DataCategory.CACHE)

    async def _process_contextcore_path(self, path_config: Dict[str, Any], default_category: DataCategory) -> None:
        """Process a path configuration from .contextcore.yaml."""
        path_str = path_config.get('path', '')
        if not path_str:
            return
        path = Path(path_str)
        if not path.is_absolute():
            path = self.config.project_root / path
        importance = path_config.get('importance', 90 if default_category == DataCategory.CRITICAL else 60)
        backup_frequency = path_config.get('backup_frequency')
        retention = path_config.get('retention')
        requirement = PersistenceRequirement(path=path, category=default_category, importance_score=importance, description=path_config.get('description', f'Configured path: {path}'), source_config='.contextcore.yaml', replaceability=path_config.get('replaceability', 'difficult'), backup_frequency=backup_frequency, retention_period=retention)
        self.requirements.append(requirement)

    def _classify_service_volume(self, service_name: str, container_path: str) -> DataCategory:
        """Classify a service volume by its likely category."""
        name_lower = service_name.lower()
        path_lower = container_path.lower()
        if 'db' in name_lower or 'database' in name_lower or 'postgres' in name_lower:
            return DataCategory.CRITICAL
        elif 'tempo' in name_lower or 'trace' in path_lower:
            return DataCategory.TRACES
        elif 'loki' in name_lower or 'log' in path_lower:
            return DataCategory.LOGS
        elif 'mimir' in name_lower or 'prometheus' in name_lower:
            return DataCategory.METRICS
        elif 'cache' in name_lower or 'redis' in name_lower:
            return DataCategory.CACHE
        elif 'tmp' in path_lower or 'temp' in path_lower:
            return DataCategory.TEMPORARY
        else:
            return DataCategory.IMPORTANT

    def _calculate_service_importance(self, service_name: str, container_path: str) -> int:
        """Calculate importance score for a service volume."""
        base_score = 50
        name_lower = service_name.lower()
        if 'db' in name_lower or 'database' in name_lower:
            base_score = 90
        elif 'grafana' in name_lower:
            base_score = 70
        elif 'tempo' in name_lower or 'loki' in name_lower or 'mimir' in name_lower:
            base_score = 75
        elif 'cache' in name_lower or 'redis' in name_lower:
            base_score = 40
        return min(100, max(0, base_score))

    def _calculate_importance_score(self, criticality: int, replaceability: str, business_value: int, size_mb: Optional[int]) -> int:
        """Calculate weighted importance score."""
        weights = self.config.weights
        replaceability_scores = {'irreplaceable': 100, 'difficult': 75, 'moderate': 50, 'easy': 25}
        replaceability_score = replaceability_scores.get(replaceability, 50)
        size_score = 50
        if size_mb is not None:
            if size_mb > 1000:
                size_score = 80
            elif size_mb > 100:
                size_score = 60
            else:
                size_score = 40
        score = criticality * weights.criticality + replaceability_score * weights.replaceability + business_value * weights.business_value + size_score * weights.size_impact
        return min(100, max(0, int(score)))

    def _determine_replaceability(self, service_name: str, container_path: str) -> str:
        """Determine how replaceable the data is."""
        name_lower = service_name.lower()
        if 'db' in name_lower or 'database' in name_lower:
            return 'irreplaceable'
        elif 'cache' in name_lower or 'redis' in name_lower:
            return 'easy'
        elif 'tmp' in container_path.lower():
            return 'easy'
        else:
            return 'moderate'

    def _classify_file_by_extension(self, file_path: Path) -> DataCategory:
        """Classify a file by its extension."""
        suffix = file_path.suffix.lower()
        if suffix in ('.db', '.sqlite', '.sqlite3'):
            return DataCategory.CRITICAL
        elif suffix in ('.log', '.logs'):
            return DataCategory.LOGS
        elif suffix in ('.json', '.yaml', '.yml'):
            return DataCategory.IMPORTANT
        elif suffix in ('.tmp', '.temp', '.cache'):
            return DataCategory.TEMPORARY
        else:
            return DataCategory.IMPORTANT

    def _calculate_file_importance(self, file_path: Path, file_size: int) -> int:
        """Calculate importance score for a state file."""
        base_score = 50
        suffix = file_path.suffix.lower()
        if suffix in ('.db', '.sqlite', '.sqlite3'):
            base_score = 90
        elif suffix in ('.json', '.yaml', '.yml'):
            base_score = 70
        elif suffix in ('.log',):
            base_score = 40
        elif suffix in ('.tmp', '.temp', '.cache'):
            base_score = 20
        if file_size > 10 * 1024 * 1024:
            base_score = min(100, base_score + 10)
        return base_score

    def _determine_file_replaceability(self, file_path: Path) -> str:
        """Determine how replaceable a file is."""
        suffix = file_path.suffix.lower()
        if suffix in ('.db', '.sqlite', '.sqlite3'):
            return 'irreplaceable'
        elif suffix in ('.log',):
            return 'moderate'
        elif suffix in ('.tmp', '.temp', '.cache'):
            return 'easy'
        else:
            return 'moderate'

    def _estimate_directory_size(self, path: Path) -> Optional[int]:
        """Estimate the size of a directory in bytes."""
        if not path.exists():
            return None
        try:
            if path.is_file():
                return path.stat().st_size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = Path(dirpath) / f
                    try:
                        total_size += fp.stat().st_size
                    except OSError:
                        pass
            return total_size
        except OSError:
            return None

    def _extract_storage_path(self, service_type: str, config_data: Dict[str, Any]) -> str:
        """Extract storage path from observability service config."""
        if service_type == 'tempo':
            storage = config_data.get('storage', {})
            return storage.get('trace', {}).get('local', {}).get('path', './tempo-data')
        elif service_type == 'loki':
            storage = config_data.get('storage_config', {})
            return storage.get('filesystem', {}).get('directory', './loki-data')
        elif service_type == 'mimir':
            storage = config_data.get('blocks_storage', {})
            return storage.get('filesystem', {}).get('dir', './mimir-data')
        return f'./{service_type}-data'

    def _generate_recommendations(self, requirements: List[PersistenceRequirement]) -> List[str]:
        """Generate recommendations based on analysis results."""
        recommendations = []
        critical_count = sum((1 for r in requirements if r.category == DataCategory.CRITICAL))
        if critical_count > 0:
            recommendations.append(f'Found {critical_count} critical data paths - ensure backup strategy')
        unbacked = [r for r in requirements if r.importance_score > 70 and (not r.backup_frequency)]
        if unbacked:
            recommendations.append(f'{len(unbacked)} high-importance paths lack backup configuration')
        large_paths = [r for r in requirements if r.size_estimate and r.size_estimate > 1024 * 1024 * 1024]
        if large_paths:
            recommendations.append(f'{len(large_paths)} paths exceed 1GB - consider retention policies')
        return recommendations
__all__ = ['AnalysisConfig', 'DataCategory', 'ImportanceWeights', 'PersistenceAnalysisResult', 'PersistenceAnalyzer', 'PersistenceRequirement']