# File Operations

This section covers the built-in tasks for file operations.

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