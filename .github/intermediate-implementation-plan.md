# Intermediate Implementation Plan

This document outlines focused improvements to the YAML Workflow Engine's batch processing capabilities, building upon the template engine centralization work. These improvements maintain the system's lightweight nature while ensuring consistency with the centralized template processing approach.

## Phase 2: Batch Processing Improvements

### Goals
- Improve batch processing reliability and template resolution consistency
- Simplify error handling and recovery
- Add basic progress tracking
- Keep the system lightweight and maintainable
- Ensure seamless integration with centralized template engine
- Standardize namespace handling across components

### Integration with Template Engine Centralization
This plan builds upon the completed work in template engine centralization:
- Uses the engine's centralized template resolution
- Maintains consistent Jinja2 feature support
- Leverages improved error handling for template resolution
- Builds on the enhanced state management system
- Preserves namespace isolation (args, env, steps)

### Current Progress

#### 1. Task Interface Foundation ✓
- Implemented `TaskConfig` class with namespace support
- Added comprehensive test suite
- Implemented template resolution
- Added error handling with context
- All tests passing with 100% coverage

#### 2. Task Handler Updates

1. [✓] Noop Task (Reference Implementation)
   - Updated to use TaskConfig
   - Added proper error handling
   - Added namespace support
   - Added comprehensive tests
   - Demonstrates best practices for other handlers

2. [✓] Python Task Handler
   ```python
   @register_task("python")
   def python_task(config: TaskConfig) -> Dict[str, Any]:
       """Execute Python code with namespace support."""
       processed = config.process_inputs()
       
       # Create execution context with namespace support
       local_vars = {
           "args": config._context.get("args", {}),
           "env": config._context.get("env", {}),
           "steps": config._context.get("steps", {}),
           "batch": config._context.get("batch", {})
       }
       
       # Execute code with proper error handling
       try:
           exec(processed["code"], {}, local_vars)
           return {
               "result": local_vars.get("result"),
               "task_name": config.name,
               "task_type": config.type,
               "available_variables": config.get_available_variables()
           }
       except Exception as e:
           raise TemplateError(f"Failed to execute Python code: {str(e)}")
   ```
   Completed:
   - ✓ Updated handler signature to use TaskConfig
   - ✓ Added proper namespace support in execution context
   - ✓ Improved error handling with context
   - ✓ Added tests:
      - Template resolution in code blocks
      - Variable access from different namespaces
      - Error messages with context
      - Operation handling with processed inputs
      - Batch processing with result format

3. [✓] Shell Task Handler
   ```python
   @register_task("shell")
   def shell_task(config: TaskConfig) -> Dict[str, Any]:
       """Execute shell commands with namespace support."""
       processed = config.process_inputs()
       
       # Process command with proper escaping
       command = processed["command"]
       
       # Handle working directory
       cwd = config.workspace
       if "working_dir" in processed:
           cwd = config.workspace / processed["working_dir"]
       
       # Execute with proper environment
       env = os.environ.copy()
       if "env" in processed:
           env.update(processed["env"])
       
       try:
           result = subprocess.run(
               command,
               shell=True,
               cwd=cwd,
               env=env,
               capture_output=True,
               text=True
           )
           return {
               "stdout": result.stdout,
               "stderr": result.stderr,
               "exit_code": result.returncode,
               "task_name": config.name,
               "task_type": config.type,
               "available_variables": config.get_available_variables()
           }
       except Exception as e:
           raise TaskExecutionError(f"Shell command failed: {str(e)}")
   ```
   Completed:
   - ✓ Updated handler signature to use TaskConfig
   - ✓ Added proper working directory handling with workspace support
   - ✓ Improved environment variable handling
   - ✓ Added proper error handling with TaskExecutionError
   - ✓ Added comprehensive tests:
      - Basic command execution
      - Variable substitution
      - Working directory handling
      - Environment variable handling
      - Error messages with context
      - Command timeout handling
      - Batch context support
      - Special character handling
      - Complex command execution

4. [✓] File Task Handler
   ```python
   @register_task("write_file")
   def write_file_task(config: TaskConfig) -> Dict[str, str]:
       """Write file with namespace support."""
       processed = config.process_inputs()
       
       # Resolve file path
       target_path = config.workspace / processed["path"]
       
       # Process content with template support
       content = processed.get("content", "")
       
       try:
           target_path.parent.mkdir(parents=True, exist_ok=True)
           target_path.write_text(content)
           return {
               "path": str(target_path),
               "task_name": config.name,
               "task_type": config.type,
               "available_variables": config.get_available_variables()
           }
       except Exception as e:
           raise TaskExecutionError(f"Failed to write file: {str(e)}")
   ```
   Completed:
   - ✓ Updated handler signature to use TaskConfig
   - ✓ Added proper path handling with workspace
   - ✓ Added proper error handling with TaskExecutionError
   - ✓ Added tests:
      - Path template resolution
      - Content template processing
      - Error messages with context
      - File operations (read, write, append, copy, move, delete)
      - JSON/YAML handling
      - Special characters and encoding
      - Directory operations

#### 3. Batch Processing Updates

1. [✓] Update BatchContext
   ```python
   class BatchContext:
       """Context manager for batch processing with namespace support."""
       def __init__(self, config: TaskConfig):
           self.name = config.name
           self.workspace = config.workspace
           self.retry_config = config.inputs.get("retry", {})
           self._context = config._context

       def create_item_context(self, item: Any, index: int) -> Dict[str, Any]:
           """Create context for a batch item while preserving namespaces."""
           return {
               "args": self._context.get("args", {}),
               "env": self._context.get("env", {}),
               "steps": self._context.get("steps", {}),
               "batch": {
                   "item": item,
                   "index": index,
                   "name": self.name
               }
           }
   ```
   Completed:
   - ✓ Added proper namespace support
   - ✓ Improved error handling
   - ✓ Added comprehensive tests
   - ✓ Verified template resolution
   - ✓ Tested parallel execution
   - ✓ Tested chunk processing
   - ✓ Tested failure handling

2. [✓] Update Batch Task Handler
   ```python
   @register_task("batch")
   def batch_task(config: TaskConfig) -> Dict[str, Any]:
       """Process multiple items in parallel with namespace support."""
       processed = config.process_inputs()
       items = processed.get("items", [])
       
       # Initialize batch context
       batch_ctx = BatchContext(config)
       
       # Process items with proper error handling and state tracking
       results = []
       for index, item in enumerate(items):
           try:
               item_context = batch_ctx.create_item_context(item, index)
               item_config = TaskConfig(processed["task"], item_context, config.workspace)
               result = process_item(item_config)
               results.append({"index": index, "result": result})
           except Exception as e:
               results.append({"index": index, "error": str(e)})
       
       return {
           "results": results,
           "task_name": config.name,
           "task_type": config.type,
           "available_variables": config.get_available_variables()
       }
   ```
   Completed:
   - ✓ Added proper error handling
   - ✓ Added state tracking
   - ✓ Added comprehensive tests
   - ✓ Verified template resolution
   - ✓ Tested parallel execution
   - ✓ Tested chunk processing
   - ✓ Tested failure handling

#### Next Steps (Prioritized)

1. Implement Python task handler with TaskConfig
   - Update handler signature
   - Add namespace support
   - Add tests
   - Verify error handling

2. Implement Shell task handler
   - Update handler signature
   - Add working directory support
   - Add environment handling
   - Add tests

3. Implement File task handler
   - Update handler signature
   - Add path handling
   - Add tests

4. Update batch processing
   - Update BatchContext
   - Update batch task handler
   - Add tests

5. Update documentation
   - Add namespace examples
   - Document error handling
   - Add batch processing guide

#### Success Criteria
- All task handlers use TaskConfig interface
- Comprehensive test coverage
- Clear error messages with context
- Proper namespace isolation
- Consistent return format
- Updated documentation

#### Testing Strategy

1. Unit Tests
   - Test each task handler with TaskConfig
   - Verify namespace isolation
   - Check error handling with context
   - Validate template resolution

2. Integration Tests
   - Test task combinations
   - Verify state preservation
   - Check batch processing
   - Validate error recovery

3. Documentation
   - Update task handler docs
   - Add namespace examples
   - Document error handling
   - Add batch processing guide

### Implementation Strategy

1. Task Interface (2 days)
   - Implement TaskConfig with namespace support
   - Update task handlers
   - Verify namespace isolation
   ```bash
   python -m pytest tests/test_task_*.py
   ```

2. Batch Context (2 days)
   - Implement enhanced BatchContext
   - Update batch processor
   - Add namespace-aware error handling
   ```