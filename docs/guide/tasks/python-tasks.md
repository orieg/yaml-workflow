# Python Tasks

The YAML Workflow Engine allows you to execute Python code directly in your workflows using the `python` task.

## Task Configuration

### Required Fields

Either `code` or `operation` must be specified for a Python task:

```yaml
steps:
  - name: example_task
    task: python
    code: |  # Either specify code...
      result = x * 2
    
  - name: another_task
    task: python
    operation: multiply  # ...or specify an operation
    inputs:
      a: 5
      b: 3
```

Omitting both will raise a ValueError with the message "Either code or operation must be specified for Python task".

## Result Handling

### Setting Task Results

There are two ways a Python task can produce a result:

1. **Explicit Result Assignment** (Recommended)
   ```yaml
   steps:
     - name: calculate
       task: python
       code: |
         x = float(input_value)
         result = x * 2  # Explicitly assign to 'result' variable
       inputs:
         input_value: "5.0"
   ```

2. **Last Expression Value** (Fallback)
   ```yaml
   steps:
     - name: calculate
       task: python
       code: |
         x = float(input_value)
         x * 2  # Last expression's value becomes the result
       inputs:
         input_value: "5.0"
   ```

### Important Notes on Result Handling

1. **Explicit Assignment**
   - Always prefer explicitly assigning to the `result` variable
   - The final value of `result` will be stored
   - Multiple assignments are allowed; the last one wins
   ```yaml
   code: |
     result = initial_value
     # ... some processing ...
     result = final_value  # This value will be stored
   ```

2. **Last Expression Fallback**
   - Only used if no `result` variable is set
   - Must be a valid expression, not just an assignment
   - Not recommended for complex code
   ```yaml
   code: |
     x = 5        # Assignment - not used as result
     y = 3        # Assignment - not used as result
     x * y        # Expression - this becomes the result
   ```

3. **No Result Cases**
   - If no `result` is set and no valid last expression exists, result will be `None`
   - Comments and empty lines are ignored
   ```yaml
   code: |
     x = 5  # Just assignments
     y = 3  # No result set
     # Final line is a comment
     # Result will be None
   ```

4. **Conditional Results**
   - Results can be set conditionally
   - The final value of `result` is used, regardless of where it was set
   ```yaml
   code: |
     if condition:
         result = value1
     else:
         result = value2
   ```

### Accessing Results in Other Tasks

Task results are stored in the workflow context and can be accessed by subsequent tasks:

```yaml
steps:
  - name: first_task
    task: python
    code: |
      result = calculate_something()

  - name: second_task
    task: python
    code: |
      # Access previous task's result
      previous_result = context['execution_state']['step_outputs']['first_task']['result']
      result = process_further(previous_result)
```

### Return Values

Results are captured through the `result` variable assignment:
- Simple types (str, int, float, bool)
- Lists and dictionaries
- JSON-serializable objects

```yaml
steps:
  - name: analyze
    task: python
    code: |
      result = {
          'status': 'success',
          'metrics': {
              'mean': sum(values) / len(values),
              'count': len(values)
          }
      }
    inputs:
      values: [1, 2, 3, 4, 5]
    outputs: analysis
```

### Error Handling

Python exceptions are caught and handled:

```yaml
steps:
  - name: validate
    task: python
    code: |
      if not isinstance(data, dict):
          result = {'valid': False, 'error': 'Input must be a dictionary'}
      else:
          result = {'valid': True}
    inputs:
      data: "{{ input_data }}"
    on_error:
      action: continue
      message: "Validation failed: {{ error }}"
```

## Task Types

### Execute Code

Run arbitrary Python code:

```yaml
task: python
code: |
  # Your Python code here
  result = calculated_value
```

### Predefined Operations

The Python task includes several predefined operations:

#### Multiply
Multiply two numbers:
```yaml
task: python
operation: multiply
inputs:
  a: 5
  b: 3
outputs: product  # Returns 15
```

#### Divide
Divide two numbers with error handling:
```yaml
task: python
operation: divide
inputs:
  a: 10
  b: 2
outputs: quotient  # Returns 5
```

#### Print Variables
Debug task by printing available variables:
```yaml
task: python
operation: print_vars
```

## Configuration Options

### Basic Configuration

```yaml
steps:
  - name: python_task
    task: python
    description: "Execute Python code"
    code: string | null        # Python code to execute
    operation: string | null   # Predefined operation to run
    inputs: object            # Input variables
    outputs: string | object  # Where to store results
    packages: [string]        # Additional packages to import
    timeout: int             # Execution timeout in seconds
```

### Input Options

The task accepts inputs in various formats:

```yaml
inputs:
  # Simple values
  x: 42
  text: "Hello"
  flag: true

  # Template variables
  data: "{{ previous_step.output }}"
  config: "{{ params.settings }}"

  # Lists and dictionaries
  items: [1, 2, 3]
  options: 
    key1: value1
    key2: value2
```

### Output Options

Results can be captured in different ways:

```yaml
# Single variable
outputs: result_var

# Multiple outputs
outputs:
  data: result.data
  status: result.status
  count: result.count

# Conditional outputs
outputs:
  success: "result.get('success', False)"
  error: "result.get('error', '')"
```

## Features

### Code Execution

The `python` task executes Python code in an isolated environment with:
- Access to workflow context variables
- Standard Python library
- Additional installed packages
- Error handling and output capture

### Input Variables

Access input variables in your Python code:

```yaml
steps:
  - name: calculate
    task: python
    code: |
      x = float(x)
      y = float(y)
      return x * y
    inputs:
      x: "{{ params.value_x }}"
      y: "{{ params.value_y }}"
    outputs: product
```

### Return Values

Return values are automatically captured and can be:
- Simple types (str, int, float, bool)
- Lists and dictionaries
- JSON-serializable objects

```yaml
steps:
  - name: analyze
    task: python
    code: |
      return {
          'status': 'success',
          'metrics': {
              'mean': sum(values) / len(values),
              'count': len(values)
          }
      }
    inputs:
      values: [1, 2, 3, 4, 5]
    outputs: analysis
```

### Error Handling

Python exceptions are caught and handled:

```yaml
steps:
  - name: validate
    task: python
    code: |
      if not isinstance(data, dict):
          raise ValueError("Input must be a dictionary")
      return {'valid': True}
    inputs:
      data: "{{ input_data }}"
    on_error:
      action: continue
      message: "Validation failed: {{ error }}"
```

### Package Management

Specify additional packages to import:

```yaml
steps:
  - name: process_data
    task: python
    packages: 
      - pandas
      - numpy
      - scikit-learn
    code: |
      import pandas as pd
      import numpy as np
      from sklearn.preprocessing import StandardScaler
      
      # Process data using imported packages
      df = pd.DataFrame(data)
      scaled = StandardScaler().fit_transform(df)
      return scaled.tolist()
    inputs:
      data: "{{ raw_data }}"
    outputs: processed_data
```

## Best Practices

1. **Result Assignment**
   - Always explicitly assign to the `result` variable
   - Don't rely on last expression behavior
   - Use clear and descriptive variable names
   ```yaml
   code: |
     # Good
     result = calculate_total(values)

     # Avoid
     calculate_total(values)  # Relying on last expression
   ```

2. **Error Handling**
   - Use try/except blocks when needed
   - Set appropriate result values for error cases
   ```yaml
   code: |
     try:
         value = process_data(input_data)
         result = {"status": "success", "value": value}
     except Exception as e:
         result = {"status": "error", "message": str(e)}
   ```

3. **Type Safety**
   - Convert input strings to appropriate types
   - Validate inputs before processing
   ```yaml
   code: |
     # Convert and validate inputs
     try:
         x = float(x)
         y = float(y)
         if x <= 0 or y <= 0:
             result = {"error": "Values must be positive"}
         else:
             result = {"value": x * y}
     except ValueError:
         result = {"error": "Invalid number format"}
   ```

4. **Context Access**
   - Use proper context paths for accessing task outputs
   - Handle missing values gracefully
   ```yaml
   code: |
     # Safe context access
     prev_output = context.get('execution_state', {}).get('step_outputs', {}).get('prev_step', {}).get('result')
     if prev_output is None:
         result = {"error": "Previous step output not found"}
     else:
         result = process_output(prev_output)
   ```

## Examples

### Data Processing

```yaml
steps:
  - name: process_data
    task: python
    code: |
      import json
      
      # Process input data
      try:
          data = json.loads(input_json)
          processed = [item['value'] * 2 for item in data]
          result = {
              "status": "success",
              "count": len(processed),
              "data": processed
          }
      except Exception as e:
          result = {
              "status": "error",
              "message": str(e)
          }
    inputs:
      input_json: "{{ previous_step.output }}"
```

### Conditional Processing

```yaml
steps:
  - name: conditional_calc
    task: python
    code: |
      value = float(input_value)
      
      if value < 0:
          result = {
              "status": "error",
              "message": "Value must be positive"
          }
      elif value < 10:
          result = {
              "status": "success",
              "category": "small",
              "processed": value * 2
          }
      else:
          result = {
              "status": "success",
              "category": "large",
              "processed": value * 1.5
          }
    inputs:
      input_value: "{{ params.value }}"
```

### Data Transformation

```yaml
steps:
  - name: transform_data
    task: python
    code: |
      def transform_record(record):
          return {
              'id': record['id'],
              'name': record['name'].upper(),
              'score': float(record['score']),
              'grade': 'A' if float(record['score']) >= 90 else 'B'
          }
      
      # Transform all records
      result = [transform_record(r) for r in records]
    inputs:
      records: "{{ input_records }}"
    outputs: transformed_data
```

### File Processing

```yaml
steps:
  - name: process_csv
    task: python
    code: |
      import csv
      from io import StringIO
      
      # Parse CSV data
      reader = csv.DictReader(StringIO(csv_content))
      data = list(reader)
      
      # Calculate statistics
      values = [float(row['value']) for row in data]
      result = {
          'count': len(values),
          'sum': sum(values),
          'average': sum(values) / len(values)
      }
    inputs:
      csv_content: "{{ steps.read_file.outputs.content }}"
    outputs: statistics
```

### API Integration

```yaml
steps:
  - name: process_api_data
    task: python
    code: |
      import json
      import urllib.parse
      
      # Process API response
      data = json.loads(api_response)
      
      # Extract and transform data
      items = data.get('items', [])
      processed = [{
          'id': item['id'],
          'url': urllib.parse.urljoin(base_url, item['path']),
          'metadata': item.get('metadata', {})
      } for item in items]
      
      result = {
          'items': processed,
          'count': len(processed)
      }
    inputs:
      api_response: "{{ steps.api_call.outputs.response }}"
      base_url: "https://api.example.com"
    outputs: processed_data
``` 