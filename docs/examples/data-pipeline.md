# Data Pipeline Example

This example demonstrates how to build a data processing pipeline using YAML Workflow. The pipeline downloads data from an API, processes it, and generates reports.

## Workflow File

```yaml
name: Data Processing Pipeline
description: Downloads, processes, and analyzes data from an API

# Environment variables for configuration
env:
  API_BASE_URL: "https://api.example.com/v1"
  DATA_DIR: "data"
  REPORT_DIR: "reports"

# Pipeline parameters
params:
  date:
    description: "Date to process data for (YYYY-MM-DD)"
    required: true
    pattern: "^\\d{4}-\\d{2}-\\d{2}$"
  report_format:
    description: "Output format for reports (json or csv)"
    default: "csv"
    enum: ["json", "csv"]

# Define reusable flow patterns
flows:
  error_handler:
    - task: shell
      command: |
        echo "Error occurred in step: {{ step.name }}" >&2
        echo "Error details: {{ step.error }}" >&2
        # Notify team (example)
        curl -X POST \
          -H "Content-Type: application/json" \
          -d '{"text": "Pipeline failed: {{ step.name }}"}' \
          "https://hooks.slack.com/services/YOUR_WEBHOOK"

# Pipeline steps
steps:
  # Step 1: Create necessary directories
  - name: setup_directories
    task: shell
    command: |
      mkdir -p "{{ env.DATA_DIR }}/{{ params.date }}"
      mkdir -p "{{ env.REPORT_DIR }}/{{ params.date }}"

  # Step 2: Download data from API
  - name: download_data
    task: http_request
    url: "{{ env.API_BASE_URL }}/data"
    method: GET
    params:
      date: "{{ params.date }}"
    headers:
      Accept: "application/json"
    output_file: "{{ env.DATA_DIR }}/{{ params.date }}/raw_data.json"
    on_error: error_handler

  # Step 3: Validate downloaded data
  - name: validate_data
    task: shell
    command: |
      # Check file exists and is not empty
      if [ ! -s "{{ env.DATA_DIR }}/{{ params.date }}/raw_data.json" ]; then
        echo "Error: Downloaded data is empty" >&2
        exit 1
      fi
      # Validate JSON structure
      jq '.' "{{ env.DATA_DIR }}/{{ params.date }}/raw_data.json" > /dev/null
    on_error: error_handler

  # Step 4: Process and transform data
  - name: process_data
    task: shell
    command: |
      # Transform data using jq
      jq '
        .data[] |
        select(.value > 0) |
        {
          id: .id,
          timestamp: .timestamp,
          value: .value,
          category: .metadata.category
        }
      ' "{{ env.DATA_DIR }}/{{ params.date }}/raw_data.json" > \
        "{{ env.DATA_DIR }}/{{ params.date }}/processed_data.json"
    outputs:
      processed_file: "{{ env.DATA_DIR }}/{{ params.date }}/processed_data.json"
    on_error: error_handler

  # Step 5: Generate report
  - name: generate_report
    task: shell
    command: |
      if [ "{{ params.report_format }}" = "json" ]; then
        # Generate JSON report
        jq -s '
          group_by(.category) |
          map({
            category: .[0].category,
            count: length,
            total_value: map(.value) | add
          })
        ' "{{ steps.process_data.outputs.processed_file }}" > \
          "{{ env.REPORT_DIR }}/{{ params.date }}/report.json"
      else
        # Generate CSV report
        echo "category,count,total_value" > \
          "{{ env.REPORT_DIR }}/{{ params.date }}/report.csv"
        jq -r '
          group_by(.category) |
          map({
            category: .[0].category,
            count: length,
            total_value: map(.value) | add
          }) |
          .[] |
          [.category, .count, .total_value] |
          @csv
        ' "{{ steps.process_data.outputs.processed_file }}" >> \
          "{{ env.REPORT_DIR }}/{{ params.date }}/report.csv"
      fi
    outputs:
      report_file: "{{ env.REPORT_DIR }}/{{ params.date }}/report.{{ params.report_format }}"
    on_error: error_handler

  # Step 6: Archive raw data
  - name: archive_data
    task: shell
    command: |
      tar -czf \
        "{{ env.DATA_DIR }}/{{ params.date }}/archive.tar.gz" \
        -C "{{ env.DATA_DIR }}/{{ params.date }}" \
        raw_data.json processed_data.json
    on_error: error_handler
```

## Features Demonstrated

1. **Advanced Configuration**
   - Environment variables
   - Required parameters with validation
   - Enum parameter constraints
   - Directory structure management

2. **HTTP Integration**
   - API data fetching
   - Query parameter handling
   - Header configuration
   - Response file handling

3. **Data Processing**
   - JSON transformation with `jq`
   - Data validation
   - Multiple output formats (JSON/CSV)
   - File operations

4. **Error Handling**
   - Custom error flow
   - Webhook notifications
   - Step-specific error handling
   - Data validation checks

5. **Output Management**
   - Step output capture
   - Dynamic file paths
   - Archive creation
   - Report generation

## Usage Examples

### 1. Run Pipeline with CSV Report

```bash
yaml-workflow run data-pipeline.yaml date=2024-03-15
```

### 2. Generate JSON Report

```bash
yaml-workflow run data-pipeline.yaml date=2024-03-15 report_format=json
```

### 3. Process Multiple Dates

```bash
for date in 2024-03-{13..15}; do
  yaml-workflow run data-pipeline.yaml date=$date
done
```

## Directory Structure

After running the pipeline:
```
.
├── data/
│   └── 2024-03-15/
│       ├── raw_data.json
│       ├── processed_data.json
│       └── archive.tar.gz
└── reports/
    └── 2024-03-15/
        └── report.csv
```

## Tips and Best Practices

1. **API Configuration**
   - Store API credentials in environment variables
   - Use appropriate timeouts for HTTP requests
   - Implement rate limiting if needed

2. **Data Handling**
   - Validate data before processing
   - Keep raw data for audit purposes
   - Archive data regularly
   - Use appropriate file permissions

3. **Error Recovery**
   - Monitor webhook notifications
   - Check error logs
   - Resume from failed steps when possible

4. **Performance**
   - Process data in chunks for large datasets
   - Use efficient data transformation tools
   - Clean up temporary files

## Dependencies

- `jq`: JSON processor
- `curl`: HTTP client
- `tar`: Archive creation
- Basic shell utilities (`mkdir`, `echo`, etc.) 