# File Operations

File operations provide a comprehensive set of tasks for managing files and their contents, supporting various formats including plain text, JSON, and YAML.

## Available Operations

### Basic File Operations

#### write_file
Writes content to a file:
```yaml
steps:
  create_file:
    type: file
    operation: write_file
    inputs:
      path: output.txt
      content: "Hello World"
      mode: "w"  # w=write (default), a=append
      encoding: utf-8
```

#### read_file
Reads content from a file:
```yaml
steps:
  read_content:
    type: file
    operation: read_file
    inputs:
      path: input.txt
      encoding: utf-8
```

#### append_file
Appends content to an existing file:
```yaml
steps:
  append_content:
    type: file
    operation: append_file
    inputs:
      path: log.txt
      content: "New log entry"
      encoding: utf-8
```

#### copy_file
Copies a file to a new location:
```yaml
steps:
  backup_file:
    type: file
    operation: copy_file
    inputs:
      source: config.yaml
      destination: backups/config.yaml
      create_dirs: true
```

#### move_file
Moves/renames a file:
```yaml
steps:
  rename_file:
    type: file
    operation: move_file
    inputs:
      source: old_name.txt
      destination: new_name.txt
```

#### delete_file
Deletes a file:
```yaml
steps:
  cleanup:
    type: file
    operation: delete_file
    inputs:
      path: temporary.txt
      ignore_missing: true
```

### JSON Operations

#### read_json
Reads and parses JSON file:
```yaml
steps:
  load_config:
    type: file
    operation: read_json
    inputs:
      path: config.json
      encoding: utf-8
```

#### write_json
Writes data as JSON:
```yaml
steps:
  save_config:
    type: file
    operation: write_json
    inputs:
      path: config.json
      content:
        name: example
        version: 1.0
      indent: 2
      sort_keys: true
```

### YAML Operations

#### read_yaml
Reads and parses YAML file:
```yaml
steps:
  load_yaml_config:
    type: file
    operation: read_yaml
    inputs:
      path: config.yaml
      encoding: utf-8
```

#### write_yaml
Writes data as YAML:
```yaml
steps:
  save_yaml_config:
    type: file
    operation: write_yaml
    inputs:
      path: config.yaml
      content:
        name: example
        version: 1.0
      default_flow_style: false
```

## Common Parameters

### Path Handling
- `path`: Target file path
- `source`: Source file path for copy/move operations
- `destination`: Destination path for copy/move operations
- `create_dirs`: Create parent directories if missing (default: false)

### Content Options
- `content`: Content to write
- `encoding`: File encoding (default: utf-8)
- `mode`: Write mode (w=write, a=append)

### Error Handling
- `ignore_missing`: Don't fail if file is missing (default: false)
- `overwrite`: Allow overwriting existing files (default: false)
- `backup`: Create backup before modifying (default: false)

### Format-Specific Options
- JSON:
  - `indent`: Indentation level
  - `sort_keys`: Sort dictionary keys
- YAML:
  - `default_flow_style`: YAML flow style
  - `explicit_start`: Include document start marker

## Examples

### Complex File Operations

#### File Processing Pipeline
```yaml
steps:
  read_input:
    type: file
    operation: read_json
    inputs:
      path: input.json

  transform_data:
    type: template
    inputs:
      template: |
        name: {{ data.name }}
        version: {{ data.version }}
        updated: {{ now() }}
      variables:
        data: "{{ steps.read_input.result }}"
    
  save_output:
    type: file
    operation: write_yaml
    inputs:
      path: output.yaml
      content: "{{ steps.transform_data.result }}"
```

#### Backup and Update
```yaml
steps:
  backup_config:
    type: file
    operation: copy_file
    inputs:
      source: config.yaml
      destination: "config.yaml.{{ date('YYYYMMDD') }}"
      
  update_config:
    type: file
    operation: write_yaml
    inputs:
      path: config.yaml
      content:
        updated_at: "{{ now() }}"
        settings: "{{ steps.backup_config.result }}"
```

## Best Practices

1. **Path Handling**:
   - Use absolute paths when working directory might change
   - Enable `create_dirs` for new file locations
   - Use path validation and normalization

2. **Error Handling**:
   - Set appropriate `ignore_missing` flags
   - Use `backup` for critical files
   - Validate file existence before operations

3. **Content Management**:
   - Choose appropriate encodings
   - Validate content before writing
   - Use proper indentation for structured formats

4. **Security**:
   - Validate file paths
   - Restrict file permissions
   - Handle sensitive data appropriately

5. **Performance**:
   - Use appropriate file modes
   - Handle large files efficiently
   - Clean up temporary files

## File Check Task

The `file_check` task validates file existence and permissions.

### Parameters

- `path` (string, required): Path to the file to check
- `required` (boolean, default: true): Whether the file must exist
- `readable` (boolean, default: true): Check if file is readable
- `writable` (boolean, default: false): Check if file is writable
- `extension` (string, optional): Expected file extension

### Example

```yaml
- name: validate_input
  task: file_check
  params:
    path: "{{ input_file }}"
    required: true
    readable: true
    extension: ".csv"
```

## Write File Task

The `write_file` task writes content to a file.

### Parameters

- `file_path` (string, required): Path where to write the file
- `content` (string, required): Content to write
- `mode` (string, default: "w"): File open mode ("w" or "a")
- `encoding` (string, default: "utf-8"): File encoding

### Example

```yaml
- name: save_output
  task: write_file
  params:
    file_path: "output/result.txt"
    content: "{{ process_result }}"
    mode: "w"
    encoding: "utf-8"
```

## Copy File Task

The `copy_file` task copies files from one location to another.

### Parameters

- `source` (string, required): Source file path
- `destination` (string, required): Destination file path
- `overwrite` (boolean, default: false): Whether to overwrite existing files

### Example

```yaml
- name: backup_data
  task: copy_file
  params:
    source: "data/input.csv"
    destination: "backup/input_{{ current_timestamp }}.csv"
    overwrite: true
```

## Delete File Task

The `delete_file` task deletes files.

### Parameters

- `path` (string, required): Path to the file to delete
- `ignore_missing` (boolean, default: true): Don't error if file doesn't exist

### Example

```yaml
- name: cleanup_temp
  task: delete_file
  params:
    path: "{{ temp_file }}"
    ignore_missing: true
```

## Directory Operations

### Create Directory

The `mkdir` task creates directories.

```yaml
- name: setup_dirs
  task: mkdir
  params:
    path: "output/reports"
    parents: true  # Create parent directories if needed
    exist_ok: true  # Don't error if directory exists
```

### List Directory

The `list_dir` task lists directory contents.

```yaml
- name: find_inputs
  task: list_dir
  params:
    path: "data"
    pattern: "*.csv"
    recursive: true
  output_var: input_files
``` 