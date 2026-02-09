# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-XX-XX

### Added

- Initial release of ContextCore Coyote (Wiisagi-ma'iingan)
- Repackaged from agent-pipeline as a ContextCore expansion pack
- Core pipeline orchestration:
  - `Pipeline` class for multi-stage execution
  - `Incident` model for error/issue representation
  - `StageResult` for stage outputs
- Pre-built agent personalities:
  - `Investigator` - Root cause analysis
  - `Designer` - Fix specification
  - `Implementer` - Code generation
  - `Tester` - Validation
  - `KnowledgeAgent` - Lessons learned
- Observability integration:
  - `O11yClient` for querying Prometheus, Loki, Tempo
  - Query templates for common investigation patterns
- Knowledge management:
  - `LessonsLearned` for capturing and querying lessons
  - ContextCore InsightEmitter integration
- CLI for local execution
- Optional ContextCore telemetry integration

### Changed

- Refactored from GitHub Actions workflows to Python SDK
- Agent prompts now bundled as package resources

### Migration from agent-pipeline

The agent-pipeline project has been repackaged as contextcore-coyote.

**GitHub Actions workflows**: The original `.github/workflows/` files can still be used alongside this package. The Python SDK provides the core logic that workflows can invoke.

**Agent prompts**: Prompts from `agents/pipeline/` are now bundled in the package and can be customized via configuration.
