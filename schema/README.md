# YAML Workflow JSON Schema

`workflow-schema.json` is a [JSON Schema draft-07](https://json-schema.org/specification-links#draft-7) document
that validates yaml-workflow YAML files and provides autocompletion in supported editors.

## VS Code

1. Install the [YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) by Red Hat.
2. Add the following to your `.vscode/settings.json`:

```json
{
  "yaml.schemas": {
    "./schema/workflow-schema.json": "workflows/**/*.yaml"
  }
}
```

Adjust the glob pattern to match wherever your workflow files live.
Alternatively, add a per-file modeline comment at the top of any workflow YAML:

```yaml
# yaml-language-server: $schema=../schema/workflow-schema.json
```

## IntelliJ IDEA / PyCharm

1. Open **Preferences → Languages & Frameworks → Schemas and DTDs → JSON Schema Mappings**.
2. Click **+** to add a new mapping.
3. Set **Schema file or URL** to the path of `workflow-schema.json`.
4. Set **Schema version** to `JSON Schema version 7`.
5. Under **Mapping**, add a file path pattern such as `workflows/*.yaml` or `*.workflow.yaml`.
6. Click **OK** and reopen your workflow files — IntelliJ will validate and autocomplete them.

## Command-line validation

You can also validate workflow files with any JSON Schema validator, for example
[`check-jsonschema`](https://check-jsonschema.readthedocs.io/):

```bash
pip install check-jsonschema
check-jsonschema --schemafile schema/workflow-schema.json workflows/my_workflow.yaml
```
