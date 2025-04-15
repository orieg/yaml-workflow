# Templating Guide

YAML Workflow uses Jinja2 as its templating engine, providing powerful variable substitution, control structures, and expressions in your workflows.

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

### Control Structures

#### Conditionals
```yaml
{% if env.DEBUG %}
debug: true
log_level: debug
{% else %}
debug: false
log_level: info
{% endif %}
```

#### Loops
```yaml
services:
{% for service in services %}
  - name: {{ service.name }}
    port: {{ service.port }}
{% endfor %}
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
```yaml
{{ name | upper }}  # Convert to uppercase
{{ name | lower }}  # Convert to lowercase
{{ name | title }}  # Title case
{{ text | trim }}   # Remove whitespace
```

### Default Values
```yaml
{{ optional_var | default('fallback') }}  # Use fallback if undefined
```

### Number Filters
```yaml
{{ number | round }}     # Round number
{{ number | abs }}       # Absolute value
{{ number | int }}       # Convert to integer
```

### List Filters
```yaml
{{ list | join(', ') }}  # Join list items
{{ list | first }}       # Get first item
{{ list | last }}        # Get last item
{{ list | length }}      # Get list length
```

## Error Handling

### Undefined Variables

By default, YAML Workflow uses `StrictUndefined`, which means accessing undefined variables will raise an error:
```yaml
# This will fail if 'unknown_var' is not defined
{{ unknown_var }}

# This will use a default value instead
{{ unknown_var | default('fallback') }}
```

### Safe String
```yaml
# Escape HTML/XML special characters
{{ user_input | escape }}

# Mark string as safe (no escaping)
{{ html_content | safe }}
```

## Task-Specific Usage

### Template Tasks
```yaml
steps:
  - name: render_template
    task: template
    template: |
      # Configuration
      name: {{ name }}
      environment: {{ env.ENVIRONMENT }}
      debug: {{ debug | lower }}
    output: config.yaml
```

### Shell Tasks
```yaml
steps:
  - name: run_script
    task: shell
    command: |
      python process.py \
        --input "{{ input_file }}" \
        --output "{{ output_dir }}/result.json" \
        --debug {{ env.DEBUG | lower }}
```

### Python Tasks
```yaml
steps:
  - name: python_step
    task: python
    params:
      function: process_data
      args:
        input: "{{ input_file }}"
        config: 
          debug: {{ env.DEBUG | lower }}
          max_items: {{ max_items | default(100) }}
```

## Best Practices

1. **Use Default Values**
   ```yaml
   # Good: Provides fallback
   debug: {{ env.DEBUG | default('false') }}
   
   # Bad: May fail if DEBUG is not set
   debug: {{ env.DEBUG }}
   ```

2. **Type Safety**
   ```yaml
   # Good: Ensures boolean
   debug: {{ env.DEBUG | lower in ['true', '1', 'yes'] }}
   
   # Bad: Direct use may cause type issues
   debug: {{ env.DEBUG }}
   ```

3. **Complex Logic**
   ```yaml
   # Good: Use intermediate variables
   {% set is_valid = length > 0 and status == 'ready' %}
   {% if is_valid %}
   status: valid
   {% endif %}
   
   # Bad: Complex inline conditions
   {% if length > 0 and status == 'ready' %}
   ```

4. **Error Messages**
   ```yaml
   # Good: Clear error context
   {% if not input_file %}
   {{ raise('Input file is required') }}
   {% endif %}
   
   # Bad: Unclear errors
   {{ input_file }}  # Will raise UndefinedError
   ```

5. **Documentation**
   ```yaml
   # Good: Document expected variables
   # Required variables:
   # - input_file: Path to input file
   # - env.API_KEY: API key for service
   
   # Bad: No documentation
   {{ input_file }}
   {{ env.API_KEY }}
   ```

## Security Considerations

1. **Input Validation**
   - Always validate user-provided input before using in templates
   - Use the `escape` filter for user-provided content

2. **Environment Variables**
   - Don't expose sensitive environment variables in template output
   - Use appropriate permissions for output files

3. **File Paths**
   - Validate and sanitize file paths
   - Use workspace-relative paths when possible

## Examples

### Configuration Template
```yaml
steps:
  - name: generate_config
    task: template
    template: |
      # Application Configuration
      # Generated: {{ timestamp }}
      
      [app]
      name: {{ app_name }}
      environment: {{ env.ENVIRONMENT }}
      debug: {{ env.DEBUG | default('false') | lower }}
      
      [database]
      host: {{ env.DB_HOST }}
      port: {{ env.DB_PORT | default('5432') }}
      name: {{ env.DB_NAME }}
      
      [logging]
      level: {{ env.LOG_LEVEL | default('INFO') | upper }}
      file: {{ workspace }}/logs/app.log
    output: config.ini
```

### Data Processing
```yaml
steps:
  - name: process_data
    task: python
    params:
      function: process_data
      args:
        input_file: "{{ input_file }}"
        options:
          batch_size: {{ batch_size | default(100) }}
          max_retries: {{ max_retries | default(3) }}
          timeout: {{ timeout | default(30) }}
        filters:
          {% for filter in filters %}
          - type: {{ filter.type }}
            value: {{ filter.value }}
          {% endfor %}
```

### Report Generation
```yaml
steps:
  - name: generate_report
    task: template
    template: |
      # Processing Report
      Generated: {{ timestamp }}
      Run: #{{ run_number }}
      
      ## Input Files
      {% for file in input_files %}
      - {{ file.name }}: {{ file.status }}
      {% endfor %}
      
      ## Statistics
      - Processed: {{ stats.processed }}
      - Succeeded: {{ stats.succeeded }}
      - Failed: {{ stats.failed }}
      
      ## Errors
      {% if errors %}
      {% for error in errors %}
      - {{ error.message }} ({{ error.code }})
      {% endfor %}
      {% else %}
      No errors reported.
      {% endif %}
    output: report.md
``` 