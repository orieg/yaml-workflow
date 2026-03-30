# AI Integration

yaml-workflow adds real value around LLM calls — not replacing them. The combination of **batch processing with resume**, **state persistence**, **conditional branching**, and **reproducible YAML pipelines** is what makes it useful here.

## When yaml-workflow helps vs. just using Ollama/curl

| Scenario | Just use Ollama CLI | Use yaml-workflow |
|---|---|---|
| Single prompt, read answer | ✓ faster | overkill |
| Process 200 documents, resume if rate-limited | painful | ✓ `--resume` |
| Multi-step pipeline (fetch → clean → summarise → store → notify) | shell script sprawl | ✓ one YAML |
| Different providers based on a flag | if/else mess | ✓ `condition:` |
| Retry on 429, with backoff | custom code | ✓ `retry:` in http.request |
| Run the same pipeline in CI and locally | env juggling | ✓ parameterised |

---

## Example 1: AI Changelog Generator

Reads `git log`, groups commits, and writes a `## [version]` entry to `CHANGELOG.md`.

**Why not just pipe git log to Ollama?** Because you also want: templated prompt, file read/write, optional Slack notification, dry-run support, and retries — all in one place.

Initialize it:
```bash
yaml-workflow init
```

Run it:
```bash
# Local Ollama (install llama3.2 first: ollama pull llama3.2)
yaml-workflow run workflows/ai_changelog.yaml version=1.2.0

# Claude API
ANTHROPIC_API_KEY=sk-ant-... \
yaml-workflow run workflows/ai_changelog.yaml version=1.2.0 provider=claude

# Preview the git log and prompt without hitting the LLM
yaml-workflow run workflows/ai_changelog.yaml version=1.2.0 --dry-run

# Specific range from last tag
yaml-workflow run workflows/ai_changelog.yaml version=1.2.0 since=v1.1.0
```

**Sample output** prepended to `CHANGELOG.md`:
```markdown
## [1.2.0] — 2026-03-29

This release improves the HTTP task with authentication support and adds a new
notification task for webhooks and Slack.

## Features
- **http**: Bearer, API key, and Basic authentication via the `auth:` input
- **notify**: New task supporting webhook, Slack, log, and file channels

## Bug Fixes
- **engine**: Step results now correctly attached when using `always_run: true`

## Chore
- Updated CI matrix to remove `continue-on-error` for Windows
```

**Pipeline steps:**
```
get_git_log    (shell)      → git log -30 --oneline
check_commits  (python_code) → fail fast if no commits
prepare_request(python_code) → build provider-specific request body
call_ollama    (http.request)→ POST to localhost:11434  [conditional]
call_claude    (http.request)→ POST to api.anthropic.com [conditional]
extract_entry  (python_code) → parse response format
update_changelog(python_code)→ prepend to CHANGELOG.md
notify_slack   (notify)      → post to Slack [conditional on slack_webhook param]
```

---

## Example 2: AI Batch Document Digest

Processes every Markdown/text file in a directory — reads each, summarises it, then generates a combined digest with an executive overview.

**Why yaml-workflow here?** This is 200+ LLM calls. A shell script breaks down:
- No resume if the API rate-limits you at file 147
- No per-file state tracking
- No easy provider switching
- No dry-run

```bash
# Summarise all docs/ Markdown files
yaml-workflow run workflows/ai_batch_digest.yaml input_dir=docs

# Resume an interrupted run (already-done files are skipped)
yaml-workflow run workflows/ai_batch_digest.yaml input_dir=docs --resume

# Only .txt files, with Claude
ANTHROPIC_API_KEY=sk-ant-... \
yaml-workflow run workflows/ai_batch_digest.yaml \
  input_dir=reports glob="**/*.txt" provider=claude

# Preview which files would be processed
yaml-workflow run workflows/ai_batch_digest.yaml input_dir=docs --dry-run
```

**Sample output** (`output/digest.md`):
```markdown
# Document Digest

**Generated:** 2026-03-29
**Model:** ollama/llama3.2
**Documents processed:** 23

---

## Executive Overview

The documentation covers the core concepts of the workflow engine, including task
types, flow control, and state management. Several guides focus on real-world use
cases such as data pipelines and plugin development. The architecture document
provides a high-level overview of the execution model.

---

## Per-Document Summaries

- **getting-started.md**: Step-by-step guide to installing and running the first workflow.
- **configuration.md**: Reference for all workflow YAML fields including params and settings.
- **cookbook.md**: Collection of production-ready recipes for common automation patterns.
...
```

**Pipeline:**
```
find_files          (python_code) → glob for matching files
llm_config          (python_code) → resolve provider/model/URL once

summarise_files     (batch)       → one iteration per file:
  └ read_file       (file.read)
  └ build_request   (python_code) → provider-specific body
  └ call_llm        (http.request)→ with retry: max_attempts=3, status_codes=[429,503]
  └ extract_summary (python_code) → parse response

build_overview_prompt(python_code)→ combine all summaries
call_overview_*     (http.request)→ one more LLM call for exec overview
write_digest        (python_code) → assemble and write Markdown
done                (notify)      → log completion
```

---

## HTTP authentication patterns

All examples work with any REST LLM API. Change the `auth:` input and URL:

### Bearer token (Claude, OpenAI, Mistral AI, …)
```yaml
- name: call_api
  task: http.request
  inputs:
    url: https://api.openai.com/v1/chat/completions
    method: POST
    auth:
      type: bearer
      token_env: OPENAI_API_KEY    # reads from environment, never hardcoded
    body:
      model: gpt-4o-mini
      messages:
        - role: user
          content: "{{ args.prompt }}"
```

### Retry on rate limits
```yaml
    retry:
      max_attempts: 5
      delay: 10.0
      status_codes: [429, 503]
```

### API key in header (Cohere, custom APIs)
```yaml
    auth:
      type: api_key
      header: Authorization
      key: "Bearer {{ env.COHERE_KEY }}"
```

---

## Notify on completion or failure

```yaml
- name: alert_done
  task: notify
  inputs:
    channel: slack
    webhook_url: "{{ env.SLACK_WEBHOOK_URL }}"
    message: ":white_check_mark: Digest ready — {{ steps.write_digest.result.count }} docs processed"
    color: good

- name: alert_error
  task: notify
  always_run: true          # runs even if a previous step failed
  condition: "{{ workflow.failed }}"
  inputs:
    channel: slack
    webhook_url: "{{ env.SLACK_WEBHOOK_URL }}"
    message: ":x: Digest pipeline failed at step {{ workflow.failed_step }}"
    color: danger
```
