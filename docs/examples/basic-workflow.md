# Basic Workflow Example

This example demonstrates a simple data processing workflow that:
1. Validates input files
2. Processes data
3. Saves results
4. Sends notifications

## Workflow Definition

```yaml
name: Basic Data Processing
description: Process CSV files and generate reports

params:
  input_file:
    description: Input CSV file path
    type: string
    required: true
  output_dir:
    description: Output directory for results
    type: string
    default: "output"
  notify_email:
    description: Email for notifications
    type: string
    required: true

env:
  PYTHONPATH: "."
  TEMP_DIR: "./temp"

steps:
  # Step 1: Validate input file
  - name: validate_input
    task: file_check
    params:
      path: "{{ input_file }}"
      required: true
      readable: true
      extension: ".csv"

  # Step 2: Create output directory
  - name: setup_output
    task: shell
    command: |
      mkdir -p "{{ output_dir }}"
      mkdir -p "{{ env.TEMP_DIR }}"

  # Step 3: Process data
  - name: process_data
    task: shell
    command: python scripts/process_data.py --input "{{ input_file }}" --output "{{ output_dir }}/processed.json"
    retry:
      max_attempts: 3
      delay: 5
    output_var: process_result

  # Step 4: Generate report
  - name: generate_report
    task: write_json
    params:
      file_path: "{{ output_dir }}/report.json"
      data:
        input_file: "{{ input_file }}"
        processed_at: "{{ current_timestamp }}"
        results: "{{ process_result }}"
      indent: 2

  # Step 5: Send notification
  - name: notify
    task: shell
    command: echo "Processing complete for {{ input_file }}" | mail -s "Workflow Complete" {{ notify_email }}
    condition: "{{ process_result is defined }}"
```

## Usage

1. Save the workflow as `workflows/data_process.yaml`

2. Create the processing script (`scripts/process_data.py`):
```python
import argparse
import pandas as pd
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    # Read and process data
    df = pd.read_csv(args.input)
    result = df.describe().to_dict()

    # Save results
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    main()
```

3. Run the workflow:
```bash
yaml-workflow run workflows/data_process.yaml \
  input_file=data/sample.csv \
  output_dir=output \
  notify_email=user@example.com
```

## Flow Control

You can define multiple flows for different purposes:

```yaml
flows:
  default: process
  definitions:
    - process: [validate_input, setup_output, process_data, generate_report, notify]
    - validate: [validate_input]
    - cleanup: [setup_output]
```

Then run specific flows:
```bash
yaml-workflow run workflows/data_process.yaml --flow validate \
  input_file=data/sample.csv
```

## Error Handling

The workflow includes several error handling features:

1. Input validation using `file_check`
2. Automatic directory creation
3. Retry logic for data processing
4. Conditional notification
5. Output variable capture

## Next Steps

- Learn about [more complex workflows](data-pipeline.md)
- Explore [HTTP integration examples](api-integration.md)
- See [task reference](../guide/tasks/index.md) for all available tasks 