# Editor Integration

yaml-workflow ships a [JSON Schema](https://json-schema.org/) (draft-07) that
describes the workflow file format. Point your editor at it to get **inline
validation and autocomplete** for `name`, `params`, `settings`, `imports`,
`steps`, `flows`, task types, and their inputs.

The schema lives at
[`schema/workflow-schema.json`](https://github.com/orieg/yaml-workflow/blob/main/schema/workflow-schema.json)
and is served over HTTPS at its canonical `$id`:

```
https://raw.githubusercontent.com/orieg/yaml-workflow/main/schema/workflow-schema.json
```

There are three ways to wire it up, from most to least portable.

## 1. Per-file modeline (works everywhere)

Add a `yaml-language-server` modeline as the first line of any workflow file.
This works in VS Code (Red Hat YAML extension), Neovim (via `yaml-language-server`),
and any editor that speaks the YAML Language Server — no settings file required,
and it works regardless of how the file is named:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/orieg/yaml-workflow/main/schema/workflow-schema.json
name: My Workflow
steps:
  - name: hello
    task: shell
    inputs:
      command: echo "hi"
```

Prefer a local copy (e.g. offline, or to pin a version)? Point at a schema file
on disk with a path **relative to the workflow file**. For example, if your
workflows live in a `workflows/` directory and the schema is at the project
root, use `../schema/...`:

```yaml
# yaml-language-server: $schema=../schema/workflow-schema.json
```

The schema is also bundled inside the installed package (at
`yaml_workflow/schema/workflow-schema.json`) for programmatic access via
`importlib.resources`.

## 2. VS Code workspace setting

Install the [Red Hat YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml)
and map the schema to your workflow files in `.vscode/settings.json`:

```json
{
  "yaml.schemas": {
    "https://raw.githubusercontent.com/orieg/yaml-workflow/main/schema/workflow-schema.json": [
      "**/*.yaml-workflow.yaml",
      "**/*.yaml-workflow.yml",
      "workflows/**/*.yaml"
    ]
  }
}
```

Adjust the globs to match wherever your workflow files live.

## 3. JetBrains IDEs (IntelliJ, PyCharm)

1. Open **Settings → Languages & Frameworks → Schemas and DTDs → JSON Schema Mappings**.
2. Click **+** and set **Schema file or URL** to the URL above (or a local path).
3. Set **Schema version** to `JSON Schema version 7`.
4. Add a file path pattern such as `*.yaml-workflow.yaml` or `workflows/*.yaml`.

## Recommended file-naming convention

For **zero-config** autocomplete via [SchemaStore](https://www.schemastore.org/)
(see below), name your workflow files with a `.yaml-workflow.yaml` (or
`.yaml-workflow.yml`) suffix:

```
deploy.yaml-workflow.yaml
etl/nightly.yaml-workflow.yaml
```

This distinctive suffix lets editors auto-detect the schema without any
per-project configuration, and avoids clashing with the many other tools that
use generically-named `*.yaml` files. Any filename still works with the
modeline or the explicit mappings above — the suffix is only needed for
SchemaStore auto-detection.

## SchemaStore auto-detection

The schema is [submitted to SchemaStore](https://github.com/SchemaStore/schemastore/pull/6213).
Once merged, editors that consume the SchemaStore catalog — VS Code with the
Red Hat YAML extension, JetBrains IDEs, and others — will automatically validate
and autocomplete files matching `*.yaml-workflow.yaml` / `*.yaml-workflow.yml`
with no manual configuration.

## Command-line validation

Validate workflow files in CI or a pre-commit hook with any JSON Schema
validator, for example [`check-jsonschema`](https://check-jsonschema.readthedocs.io/):

```bash
check-jsonschema \
  --schemafile https://raw.githubusercontent.com/orieg/yaml-workflow/main/schema/workflow-schema.json \
  workflows/my_workflow.yaml
```

You can also validate with the built-in command, which uses the engine's own
validator:

```bash
yaml-workflow validate workflows/my_workflow.yaml
```
