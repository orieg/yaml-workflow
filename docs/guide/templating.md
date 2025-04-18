# Templating Guide

YAML Workflow uses Jinja2 as its templating engine with StrictUndefined enabled, providing powerful variable substitution, control structures, and expressions in your workflows.

## Variable Namespaces

YAML Workflow organizes variables into distinct namespaces:

### Arguments (Parameters)
```yaml
steps:
  - name: process
    params:
      input: "{{ args.input_file }}"      # Access parameter
      mode: "{{ args.mode | default('fast') }}"  # With default
```

### Environment Variables
```yaml
steps:
  - name: configure
    params:
      api_url: "{{ env.API_URL }}"        # Access env var
      debug: "{{ env.DEBUG | default('false') }}"  # With default
```

### Step Outputs
```yaml
steps:
  - name: use_results
    params:
      # Direct output
      data: "{{ steps.process.output }}"
      
      # Named outputs
      result: "{{ steps.process.outputs.result }}"
      metadata: "{{ steps.process.outputs.metadata }}"
      
      # Step status
      status: "{{ steps.process.status }}"
      error: "{{ steps.process.error }}"
```

### Workflow Information
```yaml
steps:
  - name: workflow_info
    params:
      name: "{{ workflow.name }}"
      workspace: "{{ workflow.workspace }}"
      run_id: "{{ workflow.run_id }}"
      timestamp: "{{ workflow.timestamp }}"
```

## Error Handling

YAML Workflow uses StrictUndefined to catch undefined variables early:

### Undefined Variables
```yaml
# This will fail with a helpful error message:
steps:
  - name: example
    params:
      value: "{{ unknown_var }}"

# Error message will show:
# TemplateError: Variable 'unknown_var' is undefined. Available variables:
# - args: [input_file, mode, batch_size]
# - env: [API_URL, DEBUG]
# - steps: [process, transform]
```

### Safe Defaults
```yaml
steps:
  - name: safe_example
    params:
      # Use default if variable is undefined
      mode: "{{ args.mode | default('standard') }}"
      
      # Use default with type conversion
      debug: "{{ env.DEBUG | default('false') | lower }}"
      
      # Complex default with condition
      value: "{{ steps.process.output | default(args.fallback if args.fallback is defined else 'default') }}"
```

### Error Messages
```yaml
steps:
  - name: validate
    params:
      input: "{{ args.input_file }}"
    error_handling:
      undefined_variables: strict  # Raises error for undefined
      show_available: true        # Shows available variables
    on_error:
      message: "Failed: {{ error }}"  # Access error message
```

## Control Structures

### Conditionals
```yaml
steps:
  - name: conditional_step
    condition: "{{ steps.validate.status == 'completed' and args.mode == 'full' }}"
    params:
      {% if env.DEBUG | default('false') | lower == 'true' %}
      log_level: "debug"
      verbose: true
      {% else %}
      log_level: "info"
      verbose: false
      {% endif %}
```

### Loops
```yaml
steps:
  - name: batch_process
    task: batch
    inputs:
      items: "{{ steps.get_items.output }}"
      task:
        task: python
        inputs:
          code: |
            {% for opt in args.options %}
            options["{{ opt.name }}"] = "{{ opt.value }}"
            {% endfor %}
```

## Task-Specific Usage

### Template Tasks
```yaml
steps:
  - name: generate_config
    task: template
    template: |
      # Configuration
      app_name: {{ args.name }}
      environment: {{ env.ENVIRONMENT }}
      debug: {{ env.DEBUG | default('false') | lower }}
      
      # Processing
      batch_size: {{ args.batch_size | default(100) }}
      max_workers: {{ args.max_workers | default(4) }}
      
      # Previous results
      last_run: {{ steps.previous.outputs.timestamp }}
      status: {{ steps.previous.status }}
    output: "{{ args.output_file }}"
    error_handling:
      undefined_variables: strict
      show_available: true
```

### Python Tasks
```yaml
steps:
  - name: process_data
    task: python
    params:
      function: process_batch
      args:
        input: "{{ args.input_file }}"
        batch_size: "{{ args.batch_size }}"
      error_handling:
        undefined_variables: strict
    outputs:
      - processed_data
      - statistics
```

### Batch Processing
```yaml
steps:
  - name: process_items
    task: batch
    inputs:
      # Input configuration
      items: "{{ steps.get_items.output }}"
      chunk_size: "{{ args.chunk_size }}"
      max_workers: "{{ args.max_workers }}"
      
      # Processing task
      task:
        task: python
        inputs:
          code: "process_item()"
      
      # Optional argument name for items (defaults to "item")
      arg_name: data_item
```

## Best Practices

1. **Use Namespaced Variables**
   ```yaml
   # Good: Clear variable source
   input: "{{ args.input_file }}"
   api_key: "{{ env.API_KEY }}"
   
   # Bad: Unclear source
   input: "{{ input_file }}"
   ```

2. **Enable Strict Mode**
   ```yaml
   # Good: Catches errors early
   error_handling:
     undefined_variables: strict
     show_available: true
   
   # Bad: Silent failures
   value: "{{ maybe_undefined }}"
   ```

3. **Use Type-Safe Defaults**
   ```yaml
   # Good: Type-safe conversion
   debug: "{{ env.DEBUG | default('false') | lower in ['true', 'yes', '1'] }}"
   
   # Bad: Potential type issues
   debug: "{{ env.DEBUG }}"
   ```

4. **Clear Error Messages**
   ```yaml
   # Good: Context in errors
   {% if not args.input_file %}
   {{ raise('Input file is required. Available args: ' ~ args.keys()) }}
   {% endif %}
   
   # Bad: Unclear errors
   {{ args.input_file }}  # Raises UndefinedError
   ```

5. **Document Dependencies**
   ```yaml
   # Required variables:
   # args:
   #   - input_file: Path to input file
   #   - batch_size: Number of items to process
   # env:
   #   - API_KEY: Service API key
   #   - ENVIRONMENT: Deployment environment
   
   steps:
     - name: documented_step
       # ... step configuration ...
   ```

## Security Considerations

1. **Variable Access**
   - Use appropriate namespaces for variables
   - Validate variable existence before use
   - Use strict mode to catch undefined variables

2. **Error Handling**
   - Enable strict undefined checking
   - Show available variables in error messages
   - Use appropriate error handlers

3. **Type Safety**
   - Use type-safe conversions
   - Provide appropriate defaults
   - Validate variable types

4. **File Operations**
   - Use workspace-relative paths
   - Validate file paths
   - Check file permissions

## Basic Syntax

### Variable Substitution

Use double curly braces to substitute variables:
```yaml
steps:
  - name: greet
    task: template
    template: |
      Hello, {{ name }}!
      This is run #{{ run_number }} of the {{ workflow_name }} workflow.
```

### Expressions

You can use expressions inside the curly braces:
```yaml
steps:
  - name: calculate
    task: template
    template: "Result: {{ value * 2 + 5 }}"
```

## Available Variables

### Built-in Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `workflow_name` | Name of the current workflow | `{{ workflow_name }}` |
| `run_number` | Current run number | `{{ run_number }}` |
| `workspace` | Path to workspace directory | `{{ workspace }}` |
| `timestamp` | Current timestamp | `{{ timestamp }}` |

### Environment Variables

Access environment variables through the `env` object:
```yaml
steps:
  - name: show_env
    task: template
    template: |
      API URL: {{ env.API_URL }}
      Debug Mode: {{ env.DEBUG | default('false') }}
```

### Parameters

Access workflow parameters directly or through the `params` object:
```yaml
steps:
  - name: use_params
    task: template
    template: |
      Direct access: {{ name }}
      Via params: {{ params.name }}
      With default: {{ params.optional | default('default_value') }}
```

### Step Outputs

Access outputs from previous steps:
```yaml
steps:
  - name: first_step
    task: shell
    command: echo "Hello"
    outputs: greeting

  - name: second_step
    task: template
    template: "Previous step said: {{ steps.first_step.output }}"
```

## Filters

Jinja2 provides several built-in filters to transform data:

### String Filters
```