# AI Integration

yaml-workflow can drive any LLM API using the built-in `http.request` task with authentication. No new dependencies are needed — just HTTP calls, Jinja2 templates, and `python_code` for response parsing.

## Supported providers out of the box

| Provider | Auth | Endpoint |
|---|---|---|
| **Ollama** (local) | None | `http://localhost:11434/api/generate` |
| **Anthropic Claude** | Bearer `ANTHROPIC_API_KEY` | `https://api.anthropic.com/v1/messages` |
| **OpenAI / compatible** | Bearer `OPENAI_API_KEY` | `https://api.openai.com/v1/chat/completions` |
| Any REST API | bearer / api_key / basic | configurable |

---

## Example 1: Text Summarizer

The `ai_summarize` example ships with yaml-workflow and supports both Ollama and Claude.

Initialize it first:
```bash
yaml-workflow init
```

### With Ollama (local, no API key)

[Install Ollama](https://ollama.ai/) and pull a model:
```bash
ollama pull llama3.2
ollama serve   # starts on http://localhost:11434
```

Run the workflow:
```bash
yaml-workflow run workflows/ai_summarize.yaml \
  text="Python is a high-level, general-purpose programming language known for its
        readability and extensive standard library. It was created by Guido van
        Rossum and first released in 1991."
```

**Output** (`output/summary.md`):
```markdown
# Summary

**Provider:** ollama
**Model:** llama3.2
**Words:** 32

---

Python is a readable, general-purpose language created by Guido van Rossum in 1991,
known for its extensive standard library and ease of use.
```

### With Anthropic Claude

```bash
export ANTHROPIC_API_KEY=sk-ant-...

yaml-workflow run workflows/ai_summarize.yaml \
  provider=claude \
  model=claude-3-5-haiku-20241022 \
  text="Python is a high-level, general-purpose programming language..."
```

---

## Example 2: AI Code Reviewer

Reviews a source file and writes a Markdown report.

```bash
# Local Ollama
yaml-workflow run workflows/ai_code_review.yaml \
  file=src/mymodule.py

# With Claude
yaml-workflow run workflows/ai_code_review.yaml \
  file=src/mymodule.py \
  provider=claude
```

**Sample output** (`output/code_review.md`):
```markdown
# Code Review: src/mymodule.py

**Reviewer:** ollama/llama3.2
**Date:** 2026-03-29

---

## Summary
The module implements a data transformation pipeline...

## Potential Issues
1. Missing error handling in `process_record()` — an invalid record will raise...

## Suggestions
- Add type hints to improve readability
- Extract the magic number `42` into a named constant

## Quality Score: 7/10
```

---

## How it works

Both examples follow the same pattern:

```
prepare_request (python_code)
    │  Build URL, body, auth config for the chosen provider
    ▼
call_llm_ollama / call_llm_claude (http.request)
    │  Conditional on provider — only one runs
    ▼
extract_response (python_code)
    │  Parse provider-specific response format
    ▼
write_output (file.write)
    │  Render Markdown report with template
    ▼
notify_done (notify)
       Log completion message
```

---

## Building your own AI workflow

### Bearer auth (Claude, OpenAI, etc.)

```yaml
- name: call_ai
  task: http.request
  inputs:
    url: https://api.openai.com/v1/chat/completions
    method: POST
    auth:
      type: bearer
      token_env: OPENAI_API_KEY   # read from environment
    body:
      model: gpt-4o-mini
      messages:
        - role: user
          content: "{{ args.prompt }}"
```

### API key in header

```yaml
- name: call_cohere
  task: http.request
  inputs:
    url: https://api.cohere.com/v2/generate
    method: POST
    auth:
      type: api_key
      header: Authorization
      key: "Bearer {{ env.COHERE_API_KEY }}"
    body:
      model: command-r
      prompt: "{{ args.prompt }}"
```

### Retry on rate limits

The `http.request` task supports automatic retries — useful for LLM APIs that enforce rate limits:

```yaml
- name: call_llm
  task: http.request
  inputs:
    url: "{{ steps.setup.result.url }}"
    method: POST
    body: "{{ steps.setup.result.body }}"
    auth:
      type: bearer
      token_env: API_KEY
    retry:
      max_attempts: 3
      delay: 2.0
      status_codes: [429, 503]   # retry on rate limit and service unavailable
```

### Batch processing multiple items

Process many items through an LLM using the `batch` task:

```yaml
- name: summarize_articles
  task: batch
  inputs:
    items: "{{ args.articles }}"
    steps:
      - name: summarize_one
        task: http.request
        inputs:
          url: http://localhost:11434/api/generate
          method: POST
          body:
            model: llama3.2
            prompt: "Summarize: {{ batch.item }}"
            stream: false
```

---

## AI + Notifications

Combine AI processing with the `notify` task to alert on completion or errors:

```yaml
- name: alert_slack
  task: notify
  inputs:
    channel: slack
    webhook_url: "{{ env.SLACK_WEBHOOK_URL }}"
    message: "AI review of {{ args.file }} complete. Score: {{ steps.extract.result.score }}/10"
    color: good
```
