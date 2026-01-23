# Changelog

All notable changes to the ContextCore Skills Expansion Pack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-23

### Added

- Initial release of ContextCore Skills Expansion Pack
- **dev-tour-guide** skill
  - Progressive disclosure pattern (MANIFEST → index → capabilities)
  - Agent-to-agent handoff protocols
  - Infrastructure registry integration
  - 5 capability categories: observability, skills, workflows, infrastructure, knowledge
  - 3 pre-packaged actions: debug-error, check-infrastructure, create-dashboard
  - 3 communication protocols: discovery, invocation, handoff
- **capability-value-promoter** skill
  - Value type classification (direct, indirect, ripple)
  - 11 persona definitions with messaging guidance
  - 12 channel templates for content adaptation
  - Capability extraction script
  - "Audience of 1" mode for creator self-reflection
- Documentation
  - Loading skills guide
  - Customization guide
  - Example value proposition output
  - Example skill emission script

### Notes

- Skills adapted from personal development environment
- See `docs/customization.md` for path updates needed for your environment
- Requires ContextCore v0.x.x or later
