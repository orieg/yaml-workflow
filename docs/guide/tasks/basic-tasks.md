# Basic Tasks

Simple utility tasks for common operations.

## Available Tasks

### Echo Task

Print a message to the console:

```yaml
task: echo
inputs:
  message: string       # Required: Message to print
  level: string        # Optional: Log level (info, warning, error)
```

### Fail Task

Deliberately fail a workflow (useful for testing):

```yaml
task: fail
inputs:
  message: string      # Optional: Custom failure message
  code: int           # Optional: Exit code (default: 1)
```

### Add Numbers Task

Add two numbers together:

```yaml
task: add_numbers
inputs:
  a: number          # Required: First number
  b: number          # Required: Second number
outputs: sum         # Result of a + b
```

### Join Strings Task

Concatenate strings:

```yaml
task: join_strings
inputs:
  strings: [string]  # Required: List of strings to join
  separator: string  # Optional: Separator (default: '')
outputs: result     # Joined string
```

## Examples

Here are some examples of using basic tasks:

```yaml
steps:
  - name: greet
    task: echo
    inputs:
      message: "Starting workflow..."
      level: info

  - name: calculate
    task: add_numbers
    inputs:
      a: 10
      b: 20
    outputs: sum

  - name: report
    task: echo
    inputs:
      message: "The sum is {{ sum }}"
```

## Error Handling

All basic tasks support standard error handling:

```yaml
steps:
  - name: example
    task: echo
    inputs:
      message: "Test message"
    retry:
      max_attempts: 3
      delay: 5
    on_error:
      action: continue
      message: "Echo failed, continuing..."
``` 