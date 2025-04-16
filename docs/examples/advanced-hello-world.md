# Advanced Hello World Example

This example demonstrates advanced features of the workflow engine including:
- Input validation with error handling
- Conditional execution based on validation results
- File operations in different formats (txt, json, yaml)
- Shell command execution
- Template rendering with variable substitution
- Multi-step workflow with dependencies

## Workflow Definition

```yaml
name: Advanced Hello World
description: >
  An advanced hello world workflow demonstrating:
  - Input validation
  - Conditional execution
  - Error handling
  - Multiple output formats
  - Shell commands
  - Template rendering
  - Custom module tasks

params:
  name:
    description: Name to include in the greeting
    default: World

steps:
  # Step 1: Validate the input name parameter
  - name: validate_input
    task: shell
    command: |
      mkdir -p "output/"
      if [ -z "{{ name|default('') }}" ]; then
        echo "Error: Name parameter is required" > "output/validation_result.txt"
      elif [ "{{ name|length }}" -lt 2 ]; then
        echo "Error: Name must be at least 2 characters long" > "output/validation_result.txt"
      elif [ "{{ name|length }}" -gt 50 ]; then
        echo "Error: Name must not exceed 50 characters" > "output/validation_result.txt"
      else
        echo "Valid: {{ name }}" > "output/validation_result.txt"
      fi

  # Step 2: Read validation result
  - name: check_validation
    task: read_file
    params:
      file_path: "output/validation_result.txt"
      encoding: "utf-8"
    outputs: validation_content

  # Step 3: Process validation result
  - name: process_validation
    task: shell
    command: |
      if grep -q "^Error:" "output/validation_result.txt"; then
        echo "Validation failed:" >&2
        cat "output/validation_result.txt" >&2
        printf "false" > "output/validation_passed.txt"
      else
        echo "Validation passed"
        printf "true" > "output/validation_passed.txt"
      fi

  # Step 4: Read validation flag
  - name: read_validation
    task: read_file
    params:
      file_path: "output/validation_passed.txt"
    outputs: validation_content

  # Step 5: Get current timestamp (only if validation passed)
  - name: get_timestamp
    task: shell
    command: date -u +"%Y-%m-%dT%H:%M:%SZ"
    outputs: current_timestamp
    condition: "'{{ validation_content }}' == 'true'"

  # Step 6: Create JSON greeting (only if validation passed)
  - name: create_greeting
    task: write_json
    params:
      file_path: "output/greeting.json"
      data: 
        greeting: "Hello, {{ name }}!"
        timestamp: "{{ current_timestamp }}"
        run_number: "{{ run_number }}"
        language: "en"
      indent: 2
    condition: "'{{ validation_content }}' == 'true'"

  # Step 7: Create multi-language greetings (only if validation passed)
  - name: translate_greeting
    task: write_yaml
    params:
      file_path: "output/greetings.yaml"
      data:
        English: "Hello, {{ name }}!"
        Spanish: "¡Hola, {{ name }}!"
        French: "Bonjour, {{ name }}!"
        German: "Hallo, {{ name }}!"
        Italian: "Ciao, {{ name }}!"
        Japanese: "こんにちは、{{ name }}さん！"
    condition: "'{{ validation_content }}' == 'true'"

  # Step 8: Format and display results (only if validation passed)
  - name: format_output
    task: shell
    command: |
      if [ -f "output/greeting.json" ]; then
        echo "=== Workflow Results ==="
        echo "Run #{{ run_number }} at {{ current_timestamp }}"
        echo
        echo "JSON Greeting:"
        cat "output/greeting.json"
        echo
        echo "Multiple Languages:"
        cat "output/greetings.yaml"
        echo
        echo "=== End of Results ==="
      fi
    condition: "'{{ validation_content }}' == 'true'"

  # Step 9: Handle validation errors (only if validation failed)
  - name: handle_error
    task: write_file
    params:
      file_path: "output/error_report.txt"
      content: |
        Workflow encountered an error:
        Input validation failed{% if name %} for name: {{ name }}{% else %}: name parameter not provided{% endif %}
        
        Please check the requirements and try again.
        
        Requirements:
        - Name must be provided
        - Name must be between 2 and 50 characters
        - Name must not contain special characters
    condition: "'{{ validation_content }}' == 'false'"

  # Step 10: Final status notification
  - name: notify_status
    task: shell
    command: |
      if [ "$(cat output/validation_passed.txt)" = "true" ]; then
        echo "Workflow completed successfully!"
        echo "Check the output files for detailed results:"
        echo "- greeting.json: JSON formatted greeting"
        echo "- greetings.yaml: Multi-language greetings"
        echo "- validation_result.txt: Input validation details"
      else
        echo "Workflow failed due to validation errors."
        echo "Check error_report.txt for details."
        if [ -f "output/error_report.txt" ]; then
          cat "output/error_report.txt"
        else
          cat "output/validation_result.txt"
        fi
      fi
```

## Usage Examples

1. Run with default name:
```bash
yaml-workflow run advanced-hello-world.yaml
```

2. Run with a custom name:
```bash
yaml-workflow run advanced-hello-world.yaml --name="Alice"
```

3. Test validation error (name too short):
```bash
yaml-workflow run advanced-hello-world.yaml --name="A"
```

## Key Features Demonstrated

1. **Input Validation**
   - Length checks (2-50 characters)
   - Required parameter validation
   - Validation result storage in files

2. **Conditional Execution**
   - Steps that run only if validation passes
   - Error handling steps for validation failures
   - Condition-based file operations

3. **File Operations**
   - Reading and writing files
   - Multiple formats (TXT, JSON, YAML)
   - File-based state management

4. **Variable Management**
   - Step output capture using `outputs`
   - Variable interpolation in templates
   - Built-in variables (`run_number`)

5. **Error Handling**
   - Validation error reporting
   - Custom error messages
   - Error state management

6. **Multi-language Support**
   - Greetings in multiple languages
   - Unicode text handling
   - YAML formatting

## Example Outputs

### Successful Run

```
=== Workflow Results ===
Run #1 at 2024-01-23T10:30:00Z

JSON Greeting:
{
  "greeting": "Hello, Alice!",
  "timestamp": "2024-01-23T10:30:00Z",
  "run_number": "1",
  "language": "en"
}

Multiple Languages:
English: Hello, Alice!
Spanish: ¡Hola, Alice!
French: Bonjour, Alice!
German: Hallo, Alice!
Italian: Ciao, Alice!
Japanese: こんにちは、Aliceさん！

=== End of Results ===

Workflow completed successfully!
Check the output files for detailed results:
- greeting.json: JSON formatted greeting
- greetings.yaml: Multi-language greetings
- validation_result.txt: Input validation details
```

### Failed Validation

```
Validation failed:
Error: Name must be at least 2 characters long

Workflow failed due to validation errors.
Check error_report.txt for details.
Workflow encountered an error:
Input validation failed for name: A

Please check the requirements and try again.

Requirements:
- Name must be provided
- Name must be between 2 and 50 characters
- Name must not contain special characters
``` 