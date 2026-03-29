# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `--dry-run` / `-n` mode to preview workflow execution without side effects
- `http.request` task for HTTP GET/POST/PUT using stdlib urllib (zero new dependencies)
- `yaml-workflow visualize` command with ASCII text (default) and Mermaid output formats
- Unicode box-drawing for regular steps, diamond shapes for conditional steps in ASCII output
- Codecov configuration and coverage settings in pyproject.toml

### Changed
- Rewrote CLI documentation to match actual implemented commands and flags
- Updated docs landing page and tasks reference with new features
- README now includes visualize and dry-run example output

## [0.4.1] - 2026-03-28

### Added
- README badges (PyPI, CI, coverage, license, Python versions)
- "Why yaml-workflow?" comparison section in README
- CONTRIBUTING.md for contributor onboarding
- GitHub issue templates (bug report, feature request)
- CHANGELOG.md for tracking changes
- MkDocs footer with portfolio backlink, Open Graph meta tags
- GitHub repository topics for discoverability

### Changed
- Reduced sdist package size from 1.5MB to ~58KB by excluding docs/tests from distribution
- Refactored broad `except Exception` catches (46 -> 10) with specific exception types
- Fixed inaccurate README example to use actual task types (template, shell)

## [0.4.0] - 2025-04-21

### Added
- Template task include support
- Workspace creation helpers and tests
- Improved error handling throughout the engine

### Changed
- Refactored Python tasks into specific variants (`python_code`, `python_function`, `python_module`, `python_script`)
- Standardized `python_code` task output
- Aligned args namespace handling across the engine

### Fixed
- Engine initialization order and template method restoration
- Argument/result handling in Python tasks
- Type errors in state and error handling
- Code formatting with Black

## [0.3.0] - 2025-04-14

### Added
- Batch processing with parallel execution
- State persistence and resume capability
- Flow control with custom step sequences

## [0.2.0] - 2025-04-14

### Added
- Template variable substitution via Jinja2
- Shell task execution
- File operation tasks (read, write, copy, delete)

## [0.1.4] - 2025-04-14

### Fixed
- Package distribution fixes

## [0.1.2] - 2025-04-14

### Added
- Initial release
- YAML-driven workflow definition
- Basic task execution (print, noop)
- CLI interface (`run`, `list`, `validate`, `init`)
- Input/output variable management
- Error handling with retry mechanisms

[Unreleased]: https://github.com/orieg/yaml-workflow/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/orieg/yaml-workflow/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/orieg/yaml-workflow/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/orieg/yaml-workflow/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/orieg/yaml-workflow/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/orieg/yaml-workflow/compare/v0.1.2...v0.1.4
[0.1.2]: https://github.com/orieg/yaml-workflow/releases/tag/v0.1.2
