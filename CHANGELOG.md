# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.6] - 2026-08-17

### Fixed
- Pin the `mcp` extra to `>=1.0,<2.0`. The MCP server uses the mcp 1.x
  low-level `Server` API (`@server.list_tools()` / `@server.call_tool()`),
  which mcp 2.0 removed. A fresh `pip install 'yaml-workflow[mcp]'` previously
  resolved to mcp 2.0 and crashed on startup with
  `'Server' object has no attribute 'list_tools'`; the pin restores a working
  server.

## [0.9.5] - 2026-08-14

### Added
- MCP server: four always-present meta-tools — `list_workflows`,
  `validate_workflow`, `dry_run_workflow` (read-only), and `run_workflow`
  (destructive) — so an agent can discover, validate, preview, and run
  workflows even before any workflow file exists. Per-workflow convenience
  tools are still exposed. Tools carry MCP `readOnlyHint`/`destructiveHint`
  annotations.
- `glama.json` for Glama MCP server verification

### Fixed
- MCP server: pass workflow parameters correctly when running a workflow
  (previously `run(**arguments)` could raise `TypeError` for parameterized
  workflows)
- MCP server: capture engine stdout so the dry-run preview cannot corrupt the
  stdio JSON-RPC stream

## [0.9.4] - 2026-08-14

### Added
- Publish the MCP server to the official [MCP Registry](https://registry.modelcontextprotocol.io)
  as `io.github.orieg/yaml-workflow` — `server.json`, a README ownership marker,
  and an OIDC-authenticated publish job that runs on release
- Editor Integration guide and a recommended `.yaml-workflow.yaml` file-naming
  convention for zero-config schema validation and autocomplete
- Expanded MCP documentation: Claude Code, Claude Desktop, and Cursor configs,
  plus a security note on agent-triggered execution
- `SECURITY.md` with a vulnerability-reporting process and the execution security
  model (shell/Python/MCP trust boundaries)
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1)
- Pull request template and issue-template `config.yml` (routes questions to
  Discussions, security reports to private advisories)

### Fixed
- The JSON Schema (`workflow-schema.json`) is now included in the built wheel at
  `yaml_workflow/schema/`; previously it shipped only in the sdist, so
  `pip install` users could not resolve it locally
- Correct the GitHub Action reference in the README (`orieg/yaml-workflow`, not
  the non-existent `orieg/yaml-workflow-action`)
- Harden the GitHub Action against shell injection by passing inputs through
  `env:`; workflow parameters with spaces are now preserved correctly

### Changed
- Backfill CHANGELOG entries for 0.7.0 through 0.9.3
- Add `Source` and `Changelog` project URLs and refine PyPI classifiers
- Document remote-schema usage and submit the schema to SchemaStore

## [0.9.3] - 2026-08-14

### Security
- Mask declared secrets in dry-run previews and parameter-default log lines
- Clear 26 CodeQL clear-text-logging false positives across the engine

## [0.9.2] - 2026-03-31

### Fixed
- `python_code` task now runs with its working directory set to the workspace,
  matching `shell` task behavior

## [0.9.1] - 2026-03-30

### Added
- `[all]` meta-extra that installs both `serve` and `mcp` dependencies

### Changed
- Clarified `pipx`/`pip` install instructions and extras in README and docs

## [0.9.0] - 2026-03-30

### Added
- Official Docker image published to `ghcr.io/orieg/yaml-workflow` (multi-arch)
- Helm chart (`helm/yaml-workflow`) with CronJob, Ingress, and PVC templates
- Kubernetes / ArgoCD (GitOps) deployment support and guide

## [0.8.3] - 2026-03-30

### Security
- Resolve CodeQL security alerts

## [0.8.2] - 2026-03-30

### Fixed
- Strip leading `v` from release tags when comparing against the pyproject version

## [0.8.1] - 2026-03-30

### Changed
- Release workflow now publishes full releases instead of pre-releases
- Polished project positioning; added v0.8 docs and a GitHub Actions usage
  example to the README

## [0.8.0] - 2026-03-29

### Added
- Secrets validation — fail fast when required environment variables are missing
- Structured output via `--format json` / `--output` for CI integration
- Parallel step execution with `depends_on` — independent steps run concurrently
- GitHub Action (`orieg/yaml-workflow`) for running workflows in CI, published
  to the GitHub Actions Marketplace
- MCP server (`yaml-workflow serve-mcp`) — expose workflows as AI agent tools
- Web dashboard (`yaml-workflow serve`) — monitor runs and trigger workflows
- Schema-validation and GitHub Action integration tests

### Fixed
- DAG mode preserves sequential order for steps without `depends_on`
- Action separates stderr from stdout for clean JSON output
- Cross-platform test compatibility for Windows CI

## [0.7.0] - 2026-03-29

### Added
- JSON Schema (`schema/workflow-schema.json`) for editor validation and autocomplete
- `validate` command `--strict` and `--format` flags
- `http.request` task auth, retry, and SSL-verification options
- `notify` task for workflow notifications
- Meaningful real-world AI/LLM example pipelines (changelog generation, batch digest)
- Plugin authoring guide, cookbook, and architecture diagram

## [0.6.0] - 2026-03-29

### Added
- Workflow composition via `imports` — reuse steps/params across YAML files
  with relative paths, transitive imports, and circular detection
- Plugin discovery via entry points — `pip install yaml-workflow-myplugin`
  auto-registers tasks through `yaml_workflow.tasks` entry point group
- Watch mode (`--watch` / `-w`) — re-run workflow on file changes
  with 1.5s polling, monitors imports too
- Windows shell compatibility — auto-detect PowerShell on Windows
- Performance benchmarks via pytest-benchmark with CI artifact upload
- Public `context` and `processed_inputs` properties on TaskConfig
- GitHub ruleset for main branch protection
- 614 tests

### Changed
- Replaced all `config._context` / `config._processed_inputs` private access
  with public properties across 10 source files

## [0.5.0] - 2026-03-29

### Added
- `--dry-run` / `-n` mode to preview workflow execution without side effects
- `http.request` task for HTTP GET/POST/PUT using stdlib urllib (zero new dependencies)
- `yaml-workflow visualize` command with ASCII text (default) and Mermaid output formats
- Branching DAG visualization: adjacent conditional steps rendered side-by-side with fan-out/fan-in
- `data_pipeline.yaml` example demonstrating conditional branching (4 branches)
- Cross-platform CI: Linux, macOS, Windows test matrix
- Branch protection with required status checks
- Codecov integration with coverage badge
- 591 tests with 95% branch coverage (up from 394 tests / 86%)

### Changed
- Rewrote CLI documentation to match actual implemented commands and flags
- Updated README with visualization and dry-run example output
- Updated docs landing page and tasks reference with new features

### Fixed
- `DEFAULT_NAMESPACES` shallow copy mutation bug in state.py
- Codecov action v5 `file` → `files` parameter
- Log file handler cleanup for Windows compatibility

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

[Unreleased]: https://github.com/orieg/yaml-workflow/compare/v0.9.6...HEAD
[0.9.6]: https://github.com/orieg/yaml-workflow/compare/v0.9.5...v0.9.6
[0.9.5]: https://github.com/orieg/yaml-workflow/compare/v0.9.4...v0.9.5
[0.9.4]: https://github.com/orieg/yaml-workflow/compare/v0.9.3...v0.9.4
[0.9.3]: https://github.com/orieg/yaml-workflow/compare/v0.9.2...v0.9.3
[0.9.2]: https://github.com/orieg/yaml-workflow/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/orieg/yaml-workflow/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/orieg/yaml-workflow/compare/v0.8.3...v0.9.0
[0.8.3]: https://github.com/orieg/yaml-workflow/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/orieg/yaml-workflow/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/orieg/yaml-workflow/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/orieg/yaml-workflow/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/orieg/yaml-workflow/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/orieg/yaml-workflow/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/orieg/yaml-workflow/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/orieg/yaml-workflow/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/orieg/yaml-workflow/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/orieg/yaml-workflow/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/orieg/yaml-workflow/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/orieg/yaml-workflow/compare/v0.1.2...v0.1.4
[0.1.2]: https://github.com/orieg/yaml-workflow/releases/tag/v0.1.2
