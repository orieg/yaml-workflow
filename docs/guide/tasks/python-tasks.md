# Python Tasks

The YAML Workflow Engine allows you to execute Python code directly in your workflows using the `python` task.

## Basic Usage

```yaml
steps:
  - name: process_data
    task: python
    code: |
      import json
      
      # Process input data
      data = json.loads(input_json)
      result = {
          'count': len(data),
          'total': sum(item['value'] for item in data)
      }
      
      # Return results
      return result
    inputs:
      input_json: "{{ previous_step.output }}"
    outputs: processing_result
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
      - task: echo
        inputs:
          message: "Validation failed: {{ error }}"
```

### Module Imports

Import and use Python modules:

```yaml
steps:
  - name: process_dates
    task: python
    code: |
      from datetime import datetime, timedelta
      
      start = datetime.strptime(start_date, '%Y-%m-%d')
      end = datetime.strptime(end_date, '%Y-%m-%d')
      days = (end - start).days
      
      return {
          'days': days,
          'weeks': days // 7,
          'months': days // 30
      }
    inputs:
      start_date: "2024-01-01"
      end_date: "2024-12-31"
    outputs: duration
```

## Best Practices

1. **Code Organization**
   - Keep Python code concise and focused
   - Use functions for complex logic
   - Follow PEP 8 style guidelines

2. **Error Handling**
   - Use try/except blocks for specific errors
   - Provide clear error messages
   - Return structured error information

3. **Data Processing**
   - Validate input data
   - Use appropriate data types
   - Handle edge cases

4. **Performance**
   - Minimize memory usage
   - Use efficient algorithms
   - Consider batch processing

## Examples

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
      return [transform_record(r) for r in records]
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
      return {
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
  - name: prepare_request
    task: python
    code: |
      import hashlib
      import time
      
      # Create API signature
      timestamp = str(int(time.time()))
      message = f"{api_key}{timestamp}{endpoint}"
      signature = hashlib.sha256(message.encode()).hexdigest()
      
      return {
          'headers': {
              'X-API-Key': api_key,
              'X-Timestamp': timestamp,
              'X-Signature': signature
          }
      }
    inputs:
      api_key: "{{ env.API_KEY }}"
      endpoint: "/data"
    outputs: request_info
``` 