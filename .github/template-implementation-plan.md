# Template Engine Centralization Plan

## Status Update: TaskConfig Implementation (2024-04-17)

The goals of this implementation plan have been achieved through a different approach: the TaskConfig interface. Instead of moving template processing to the engine level directly, we've created a standardized TaskConfig interface that handles template resolution, error handling, and state management in a consistent way across all tasks.

### Completed Goals

1. ✓ Centralized Template Processing
   - Implemented through TaskConfig's `process_inputs()` method
   - Consistent Jinja2 feature support across all components
   - Standardized error handling with TaskExecutionError
   - Comprehensive test coverage

2. ✓ Namespace Support
   - Isolated namespaces (args, env, steps, batch)
   - Consistent variable access across all tasks
   - Proper context preservation
   - Type-safe variable handling

3. ✓ Error Handling
   - Standardized TaskExecutionError
   - Detailed error context
   - Available variables listing
   - Proper error propagation

4. ✓ Task Handler Updates
   - All task handlers updated to use TaskConfig
   - Consistent interface across all tasks
   - Proper template resolution
   - Comprehensive test coverage

### Implementation Details

The TaskConfig approach provides:

1. Template Resolution:
   ```python
   @register_task("example_task")
   def example_task_handler(config: TaskConfig) -> Dict[str, Any]:
       # Process inputs with template resolution
       processed = config.process_inputs()
       
       # Access variables from different namespaces
       input_value = config.get_variable('value', namespace='args')
       env_var = config.get_variable('API_KEY', namespace='env')
       
       # Process with proper error handling
       try:
           result = process_data(input_value, env_var)
           return {
               "result": result,
               "task_name": config.name,
               "task_type": config.type
           }
       except Exception as e:
           raise TaskExecutionError(
               message=f"Task failed: {str(e)}",
               step_name=config.name,
               original_error=e
           )
   ```

2. Error Handling:
   ```python
   try:
       processed = config.process_inputs()
   except TemplateError as e:
       # Template resolution error with context
       raise TaskExecutionError(
           message="Template resolution failed",
           step_name=config.name,
           original_error=e
       )
   ```

3. Namespace Support:
   ```yaml
   steps:
     example_step:
       name: example_step
       task: shell
       inputs:
         command: |
           echo "Args: {{ args.input }}"
           echo "Env: {{ env.PATH }}"
           echo "Previous: {{ steps.prev_step.result }}"
           echo "Batch: {{ batch.item if 'batch' in vars() }}"
   ```

### Documentation

Updated documentation is available in:
- [Task Types](docs/tasks.md)
- [Features](docs/features.md)
- [Development Guide](docs/development.md)

### Next Steps

While the original plan's goals have been achieved through TaskConfig, there are some advanced features that could be considered for future implementation:

1. Template Includes
   - Support for including external templates
   - Proper file resolution
   - Security considerations

2. Custom Filters
   - Registration mechanism
   - Documentation
   - Testing framework

3. Advanced Control Structures
   - Enhanced loop support
   - Complex conditionals
   - Error recovery

These features should be implemented through the TaskConfig interface to maintain consistency.
