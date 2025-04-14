# Shell Tasks

Shell tasks allow you to execute commands in a shell environment with full control over execution context and output handling.

## Basic Usage

```yaml
steps:
  list_files:
    type: shell
    inputs:
      command: ls -la
      working_dir: /path/to/directory

  build_project:
    type: shell
    inputs:
      command: make build
      env:
        BUILD_ENV: production
        DEBUG: "false"
```

## Configuration Options

### Command Execution
- `command`: The shell command to execute (required)
- `shell`: Shell to use (default: `/bin/bash` on Unix, `cmd.exe` on Windows)
- `args`: List of command arguments (alternative to embedding in command string)

### Environment Variables
- `env`: Dictionary of environment variables to set
- `inherit_env`: Whether to inherit parent process environment (default: true)
- `expand_env`: Whether to expand environment variables in command (default: true)

### Working Directory
- `working_dir`: Directory to execute command in
- `create_dir`: Create working directory if it doesn't exist (default: false)

### Output Handling
- `capture_output`: Capture command output (default: true)
- `output_encoding`: Encoding for output capture (default: utf-8)
- `stream_output`: Stream output in real-time (default: false)
- `output_format`: Format for captured output (text/json)

### Error Handling
- `fail_on_error`: Whether to fail workflow on non-zero exit code (default: true)
- `ignore_errors`: List of acceptable error patterns to ignore
- `retry`:
  - `max_attempts`: Maximum retry attempts (default: 1)
  - `delay`: Delay between retries in seconds
  - `backoff_factor`: Exponential backoff factor

## Examples

### Basic Command Execution
```yaml
steps:
  simple_command:
    type: shell
    inputs:
      command: echo "Hello World"
```

### Environment Variables
```yaml
steps:
  env_example:
    type: shell
    inputs:
      command: echo "Building ${APP_NAME} in ${ENV}"
      env:
        APP_NAME: my-app
        ENV: production
```

### Working Directory
```yaml
steps:
  build_in_dir:
    type: shell
    inputs:
      command: npm run build
      working_dir: ./frontend
      create_dir: true
```

### Output Capture and Processing
```yaml
steps:
  process_output:
    type: shell
    inputs:
      command: git status --porcelain
      capture_output: true
      output_format: text
    
  use_output:
    type: shell
    inputs:
      command: echo "Modified files: {{ steps.process_output.result }}"
```

### Error Handling and Retries
```yaml
steps:
  retry_example:
    type: shell
    inputs:
      command: curl https://api.example.com/data
      retry:
        max_attempts: 3
        delay: 5
        backoff_factor: 2
      ignore_errors:
        - "Connection timed out"
```

### Parallel Command Execution
```yaml
steps:
  parallel_tests:
    type: shell
    parallel:
      max_parallel: 4
    for_each: ["test1", "test2", "test3", "test4"]
    inputs:
      command: npm run test {{ item }}
```

## Best Practices

1. **Security**:
   - Avoid embedding sensitive data in commands
   - Use environment variables for secrets
   - Validate and sanitize input variables

2. **Error Handling**:
   - Set appropriate retry policies for unreliable commands
   - Use `ignore_errors` for known acceptable failures
   - Capture and log error output

3. **Output Management**:
   - Use `capture_output` when output needs to be processed
   - Enable `stream_output` for long-running commands
   - Consider output encoding for non-ASCII content

4. **Working Directory**:
   - Use absolute paths when working directory might change
   - Enable `create_dir` when directory creation is expected
   - Clean up temporary directories when done

5. **Environment**:
   - Use `inherit_env` carefully in secure environments
   - Document required environment variables
   - Set sensible defaults for optional variables

## Features

### Command Execution

The `shell` task executes commands in a shell environment with:
- Variable substitution
- Output capture
- Error handling
- Working directory management

### Variable Substitution

Use double curly braces for variable substitution in commands:

```yaml
steps:
  - name: build
    task: shell
    command: |
      make build \
        VERSION={{ version }} \
        TARGET={{ target }} \
        DEBUG={{ env.DEBUG }}
```

### Output Capture

Capture command output using shell command substitution:

```yaml
steps:
  - name: get_version
    task: shell
    command: git describe --tags
    outputs:
      version: $(git describe --tags)
      branch: $(git rev-parse --abbrev-ref HEAD)
```

### Error Handling

Handle command failures with retry and error flows:

```yaml
steps:
  - name: deploy
    task: shell
    command: |
      kubectl apply -f {{ manifest }}
    retry:
      max_attempts: 3
      delay: 5
    on_error:
      - task: echo
        inputs:
          message: "Deployment failed: {{ error }}"
```

### Working Directory

Specify a working directory for command execution:

```yaml
steps:
  - name: build_docs
    task: shell
    command: |
      mkdocs build
    working_dir: docs/
```

## Environment Variables

Access environment variables in commands:

1. **Workflow Variables**
   ```yaml
   steps:
     - name: show_info
       task: shell
       command: |
         echo "Workflow: {{ workflow_name }}"
         echo "Run: {{ run_number }}"
         echo "Workspace: {{ workspace }}"
   ```

2. **Custom Variables**
   ```yaml
   steps:
     - name: setup_env
       task: shell
       command: |
         export PATH="{{ env.CUSTOM_PATH }}:$PATH"
         export PYTHONPATH="{{ env.PYTHONPATH }}"
   ```

## Best Practices

1. **Command Organization**
   - Use multiline commands for clarity
   - Group related commands
   - Add comments for complex operations

2. **Error Handling**
   - Set appropriate exit codes
   - Use error handling flows
   - Implement retries for flaky commands

3. **Security**
   - Validate input variables
   - Avoid shell injection
   - Use proper permissions

4. **Performance**
   - Minimize command execution
   - Use efficient shell operations
   - Consider parallel execution

## Examples

### File Processing

```yaml
steps:
  - name: process_files
    task: shell
    command: |
      # Create output directory
      mkdir -p output/
      
      # Process each file
      for file in data/*.csv; do
        filename=$(basename "$file")
        python process.py \
          --input "$file" \
          --output "output/${filename%.csv}.json"
      done
    outputs:
      files: $(ls output/)
```

### System Commands

```yaml
steps:
  - name: system_info
    task: shell
    command: |
      # Collect system information
      echo "=== System Info ==="
      uname -a
      
      echo "=== Memory Usage ==="
      free -h
      
      echo "=== Disk Usage ==="
      df -h
    outputs:
      kernel: $(uname -r)
      memory: $(free -h | awk '/^Mem:/ {print $3}')
```

### Git Operations

```yaml
steps:
  - name: git_ops
    task: shell
    command: |
      # Ensure we're on the right branch
      git checkout {{ branch }}
      
      # Update dependencies
      npm install
      
      # Build and test
      npm run build
      npm test
      
      # Create release tag
      git tag -a v{{ version }} -m "Release {{ version }}"
      git push origin v{{ version }}
    outputs:
      commit: $(git rev-parse HEAD)
      tag: v{{ version }}
```

### Docker Commands

```yaml
steps:
  - name: docker_build
    task: shell
    command: |
      # Build image
      docker build \
        --tag {{ image }}:{{ tag }} \
        --build-arg VERSION={{ version }} \
        --file Dockerfile \
        .
      
      # Run tests
      docker run --rm \
        -e TEST_MODE=1 \
        {{ image }}:{{ tag }} \
        npm test
      
      # Push if tests pass
      docker push {{ image }}:{{ tag }}
    outputs:
      image_id: $(docker images -q {{ image }}:{{ tag }})
```

### Database Operations

```yaml
steps:
  - name: db_backup
    task: shell
    command: |
      # Set timestamp
      timestamp=$(date +%Y%m%d_%H%M%S)
      
      # Create backup
      pg_dump \
        -h {{ env.DB_HOST }} \
        -U {{ env.DB_USER }} \
        -d {{ env.DB_NAME }} \
        -F c \
        -f "backup_${timestamp}.dump"
      
      # Compress backup
      gzip "backup_${timestamp}.dump"
      
      # Upload to storage
      aws s3 cp \
        "backup_${timestamp}.dump.gz" \
        "s3://{{ env.BACKUP_BUCKET }}/db/"
    outputs:
      backup_file: backup_${timestamp}.dump.gz
``` 