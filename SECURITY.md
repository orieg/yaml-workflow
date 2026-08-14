# Security Policy

## Supported versions

yaml-workflow is pre-1.0 and follows a rolling-release model. Security fixes are
applied to the latest release on PyPI. Please upgrade to the latest release
before reporting an issue.

| Version | Supported |
| ------- | --------- |
| Latest release | :white_check_mark: |
| Older releases | :x: |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report privately using GitHub's [private vulnerability reporting](https://github.com/orieg/yaml-workflow/security/advisories/new)
("Report a vulnerability" under the repository's **Security** tab). If that is
unavailable, email the maintainer at **nicolas@brousse.info** with the details.

Please include:

- A description of the vulnerability and its impact
- Steps to reproduce (a minimal workflow YAML is ideal)
- The yaml-workflow version and how it was invoked (CLI, MCP server, Action, Docker)

You can expect an initial acknowledgement of your report. Once a fix is
available, a patched release will be published to PyPI and a GitHub Security
Advisory issued with credit to the reporter (unless anonymity is requested).

## Security model — what you are trusting

yaml-workflow **executes the workflows you give it**. This is by design, but it
means workflow files are executable code and should be treated with the same
trust as a shell script or a `Makefile`:

- The **`shell`** task runs arbitrary shell commands.
- The **`python_code` / `python_function` / `python_module` / `python_script`**
  tasks execute arbitrary Python in the host process.
- **Jinja2 templating** is rendered with access to the workflow's variable
  namespaces (`args`, `env`, `steps`, `batch`).
- The **`http.request`** task makes outbound network calls.

**Only run workflow files you trust.** Do not run untrusted or third-party
workflow YAML without reviewing it first, the same way you would review a script
before running it.

### Running via the MCP server or an AI agent

The MCP server (`yaml-workflow serve-mcp`) exposes each workflow in a directory
as a callable tool. An AI agent (or anything else) connected to the server can
therefore **trigger execution of those workflows**, which may run shell commands
and Python. When exposing workflows to an agent:

- Only serve a directory of workflows you have reviewed and trust.
- Run the server with least privilege (a dedicated user, container, or sandbox),
  not as root and not with broad filesystem or network access it does not need.
- Treat workflow parameters coming from an agent as untrusted input.

### Secrets

Declared secrets are masked in logs and in `--dry-run` previews. Even so, avoid
committing secrets into workflow files — pass them via environment variables and
declare their names in the workflow's top-level `secrets:` list so they are
validated at startup and masked in output.
