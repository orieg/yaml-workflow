# Resume Testing Example

This example demonstrates the workflow resumption functionality, allowing you to:
- Test workflow failure and recovery
- Resume from failed steps
- Start from specific steps
- Handle required parameters during resumption

## Workflow File

```yaml
# Test Resume Workflow
# This workflow is designed to test the workflow resumption functionality.
# It has three steps that can be used to verify different resume scenarios:
#
# How to test:
# 1. Run without required_param - will fail at first step:
#    yaml-workflow run workflows/test_resume.yaml
#
# 2. Resume the failed workflow:
#    yaml-workflow run workflows/test_resume.yaml --resume required_param=test
#
# 3. Try to resume a completed workflow (should fail):
#    yaml-workflow run workflows/test_resume.yaml --resume
#
# 4. Start from a specific step (fresh run):
#    yaml-workflow run workflows/test_resume.yaml --start-from process_data required_param=test

name: Test Resume
description: A simple workflow to test resumption functionality

steps:
  # Step 1: Validate required parameter
  # This step will fail if required_param is not provided
  - name: check_required_param
    task: shell
    command: |
      if [ -z "{{ required_param|default('') }}" ]; then
        echo "Error: required_param is required" >&2
        exit 1
      fi
      echo "required_param is {{ required_param }}"
      echo "{{ required_param }}" > "output/check_result.txt"
    outputs:
      check_result: "{{ required_param }}"

  # Step 2: Process the data
  # Creates a file with the parameter value
  - name: process_data
    task: shell
    command: |
      echo "Processing data with {{ required_param }}"
      echo "{{ required_param }}" > "output/result.txt"
    outputs:
      process_result: "{{ required_param }}"

  # Step 3: Final verification
  # Reads and displays the processed result
  - name: final_step
    task: shell
    command: |
      echo "Final step - reading result"
      cat "output/result.txt"
    outputs:
      final_result: "$(cat output/result.txt)"
```

## Features Demonstrated

1. **Workflow Resumption**
   - Resume from failed steps
   - Start from specific steps
   - Handle required parameters

2. **Parameter Validation**
   - Required parameter checking
   - Error handling for missing parameters

3. **Step Dependencies**
   - Sequential step execution
   - Output capture between steps
   - File-based state persistence

4. **Error Handling**
   - Graceful failure on missing parameters
   - Error message output
   - Exit code handling

## Test Scenarios

### 1. Initial Failure

Run without required parameter:
```bash
yaml-workflow run workflows/test_resume.yaml
```

Expected output:
```
Error: required_param is required
Workflow failed at step 'check_required_param'
```

### 2. Resume After Failure

Resume with required parameter:
```bash
yaml-workflow run workflows/test_resume.yaml --resume required_param=test
```

Expected output:
```
required_param is test
Processing data with test
Final step - reading result
test
```

### 3. Resume Completed Workflow

Try to resume a completed workflow:
```bash
yaml-workflow run workflows/test_resume.yaml --resume
```

Expected output:
```
Error: Cannot resume workflow - no failed state found
```

### 4. Start from Specific Step

Start from the process_data step:
```bash
yaml-workflow run workflows/test_resume.yaml --start-from process_data required_param=test
```

Expected output:
```
Processing data with test
Final step - reading result
test
```

## Tips for Testing

1. **Clean State**
   ```bash
   rm -rf output/
   ```

2. **Check Output Files**
   ```bash
   cat output/check_result.txt
   cat output/result.txt
   ```

3. **Monitor Step Execution**
   - Watch for step progression
   - Check error messages
   - Verify output files 