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

### Step Results (`steps`)

   Access results from previous steps using the `steps` namespace. All primary outputs are nested under a `result` key for consistency. Step status and errors are accessed directly.

   ```yaml
   steps:
     - name: use_results
       params:
         # Access the entire result (if it's a single value or you need the whole dict)
         data: "{{ steps.process.result }}"
         
         # Access a specific key if the 'process' step's result is a dictionary
         # e.g., if steps.process.result == {'file': '/data.txt', 'count': 100}
         file_processed: "{{ steps.process.result.file }}"
         item_count: "{{ steps.process.result.count }}"
         
         # Step status (completed, failed, skipped) - accessed directly
         status: "{{ steps.process.status }}"
         # Step error message if failed - accessed directly
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
      value: "{{ steps.process.result | default(args.fallback if args.fallback is defined else 'default') }}"
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
      items: "{{ steps.get_items.result }}"
      task:
        task: python_code
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
      last_run: {{ steps.previous.result.timestamp }}
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
    task: python_code
    params:
      function: process_batch
      args:
        input: "{{ args.input_file }}"
        batch_size: "{{ args.batch_size }}"
      error_handling:
        undefined_variables: strict
    # The return value of the 'process_batch' function will be accessible
    # via 'steps.process_data.result'
```

### Batch Processing
```yaml
steps:
  - name: process_items
    task: batch
    inputs:
      # Input configuration
      items: "{{ steps.get_items.result }}"
      chunk_size: "{{ args.chunk_size }}"
      max_workers: "{{ args.max_workers }}"
      
      # Processing task
      task:
        task: python_code
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

# Accessing complex data structures
- name: access_complex_data
  task: python_code
  inputs:
    code: |
      user_name = steps.load_user.result.name
      first_permission = steps.load_user.result.permissions[0]
      result = f"User {user_name} has permission: {first_permission}"

- name: process_values
  task: python_code
  inputs:
    code: |
      print(f"Processing user: {user}")
      # Use api_key securely
      result = user + api_key

# Using includes in a Python task
- name: dynamic_python_logic
  task: python_code
  inputs:
    code: |
      {% include 'path/to/python_helper.py' %}
      
      # Now call functions defined in the included file
      result = helper_function(args.input)