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

### Tasks

#### 1. Standardize Task Interface with Namespace Support ✓
```python
# In tasks/__init__.py
class TaskConfig:
    """Configuration class for task handlers with namespace support."""
    def __init__(self, step: Dict[str, Any], context: Dict[str, Any], workspace: Path):
        self.name = step.get("name")
        self.type = step.get("task")
        self.inputs = step.get("inputs", {})
        self._context = context
        self.workspace = workspace
        self._processed_inputs: Dict[str, Any] = {}

    def get_variable(self, name: str, namespace: Optional[str] = None) -> Any:
        """Get a variable with namespace support."""
        if namespace:
            return self._context.get(namespace, {}).get(name)
        return self._context.get(name)

    def get_available_variables(self) -> Dict[str, List[str]]:
        """Get available variables by namespace."""
        return {
            "args": list(self._context.get("args", {}).keys()),
            "env": list(self._context.get("env", {}).keys()),
            "steps": list(self._context.get("steps", {}).keys()),
            "root": [k for k in self._context.keys() if k not in ["args", "env", "steps"]]
        }

    def process_inputs(self) -> Dict[str, Any]:
        """Process task inputs with template resolution."""
        if not self._processed_inputs:
            for key, value in self.inputs.items():
                if isinstance(value, str):
                    try:
                        template = Template(value, undefined=StrictUndefined)
                        self._processed_inputs[key] = template.render(**self._context)
                    except UndefinedError as e:
                        error_msg = str(e)
                        namespace = self._get_undefined_namespace(error_msg)
                        available = self.get_available_variables()
                        raise TemplateError(
                            f"Failed to resolve template variable in input '{key}' in namespace '{namespace}'. "
                            f"Error: {error_msg}. Available variables: {available[namespace]}"
                        )
                else:
                    self._processed_inputs[key] = value
        return self._processed_inputs
```

1. ✓ Define standard task configuration
   - Added namespace-aware variable access
   - Implemented consistent error reporting with namespace context
   - Created type-safe configuration object
   - Added comprehensive test suite in `tests/test_task_interface.py`
   - All tests passing with 100% coverage for TaskConfig

2. Update task handlers to use standard interface
   - [ ] Python task handler (using TaskConfig)
     ```python
     @register_task("python")
     def python_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> Any:
         """Execute Python code with namespace support."""
         config = TaskConfig(step, context, workspace)
         processed = config.process_inputs()
         
         # Handle code execution
         if "code" in processed:
             return execute_code(processed["code"], config._context)
         
         # Handle operations (multiply, divide, etc.)
         if "operation" in processed:
             return handle_operation(processed["operation"], processed)
     ```
     Steps:
     1. Update handler to use TaskConfig
     2. Move template resolution to config.process_inputs()
     3. Update error handling to use namespace context
     4. Add tests:
        - Template resolution in code blocks
        - Variable access from different namespaces
        - Error messages with namespace context
        - Operation handling with processed inputs
     5. Verify:
        ```bash
        python -m pytest tests/test_python_tasks.py -v
        ```

   - [ ] Shell task handler (using TaskConfig)
     ```python
     @register_task("shell")
     def shell_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
         """Execute shell commands with namespace support."""
         config = TaskConfig(step, context, workspace)
         processed = config.process_inputs()
         
         # Process command with proper escaping
         command = process_command(processed["command"])
         
         # Handle working directory
         cwd = workspace
         if "working_dir" in processed:
             cwd = workspace / processed["working_dir"]
         
         return execute_command(command, cwd)
     ```
     Steps:
     1. Update handler to use TaskConfig
     2. Move command processing to config.process_inputs()
     3. Update working directory handling
     4. Add tests:
        - Command template resolution
        - Working directory with namespaces
        - Environment variable handling
        - Error messages with context
     5. Verify:
        ```bash
        python -m pytest tests/test_shell_tasks.py -v
        ```

   - [ ] File task handler (using TaskConfig)
     ```python
     @register_task("write_file")
     def write_file_task(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> Dict[str, str]:
         """Write file with namespace support."""
         config = TaskConfig(step, context, workspace)
         processed = config.process_inputs()
         
         # Resolve file path
         target_path = resolve_path(processed["path"], workspace)
         
         # Process content with template support
         content = processed.get("content", "")
         if isinstance(content, (dict, list)):
             content = process_structured_content(content, config)
         
         return write_file(target_path, content)
     ```
     Steps:
     1. Update handler to use TaskConfig
     2. Move path resolution to config.process_inputs()
     3. Update content processing for structured data
     4. Add tests:
        - Path template resolution
        - Content template processing
        - Structured data handling
        - Error messages with context
     5. Verify:
        ```bash
        python -m pytest tests/test_file_tasks.py -v
        ```

   - [ ] Test: `python -m pytest tests/test_task_handlers.py`

Implementation Strategy for Each Handler:
1. Create handler-specific test file if not exists
2. Add namespace-aware test cases
3. Update handler implementation
4. Verify existing functionality
5. Add namespace-specific error handling
6. Run full test suite

Success Criteria for Handlers:
- Uses TaskConfig for all template resolution
- Preserves existing functionality
- Provides clear namespace-aware error messages
- Handles structured data appropriately
- Maintains backward compatibility
- Passes all tests with >80% coverage

✓ Checkpoint: Task interface implementation complete
✓ Checkpoint: Task interface tests passing

#### 2. Enhanced Batch Context
```python
class BatchContext:
    """Context manager for batch processing with namespace support."""
    def __init__(self, config: TaskConfig):
        self.name = config.name
        self.engine = config.get_variable("engine")
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

    def get_error_context(self, error: Exception) -> Dict[str, Any]:
        """Get error context with namespace information."""
        return {
            "error": str(error),
            "available_variables": self.get_available_variables(),
            "namespaces": list(self._context.keys())
        }
```

1. Standardize batch context
   - Namespace-aware variable access
   - Type-safe batch operations
   - Consistent error context
   - Test: `python -m pytest tests/test_batch_context.py`

2. Update batch processor
   - Use enhanced batch context
   - Preserve namespace isolation
   - Improve error handling
   - Test: `python -m pytest tests/test_batch_processor.py`

✓ Checkpoint: Batch context tests pass

#### 3. Simplified State Management
```python
class BatchState:
    """State manager for batch processing with namespace support."""
    def __init__(self, workspace: Path, name: str):
        self.state = {
            "processed": [],  # Keep order for resume
            "failed": {},     # item -> error info
            "template_errors": {},  # Track template resolution failures
            "namespaces": {   # Track namespace states
                "args": {},
                "env": {},
                "steps": {},
                "batch": {}
            },
            "stats": {
                "total": 0,
                "processed": 0,
                "failed": 0,
                "template_failures": 0,
                "retried": 0
            }
        }
```

1. Standardize state format
   - Namespace-aware state tracking
   - Simple statistics tracking
   - Template resolution state tracking
   - Test: `python -m pytest tests/test_state.py`

2. Integrate with engine state
   - Update WorkflowState integration
   - Keep state format simple
   - Preserve namespace states
   - Test: `python -m pytest tests/test_state_integration.py`

✓ Checkpoint: State management tests pass

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
   ```bash
   python -m pytest tests/test_batch_*.py
   ```

3. State Management (1 day)
   - Implement BatchState
   - Update state integration
   - Add namespace state tracking
   ```bash
   python -m pytest tests/test_state_*.py
   ```

4. Integration (2 days)
   - Verify namespace consistency
   - Test template resolution
   - Run full test suite
   ```bash
   python -m pytest tests/
   ```

### Success Criteria
- All task handlers use TaskConfig interface
- Batch processing preserves namespace isolation
- Error handling includes namespace context
- State management tracks namespace states
- Changes maintain backward compatibility
- System remains lightweight and practical

### Documentation Updates
- [ ] Document TaskConfig interface
- [ ] Update error handling examples with namespace context
- [ ] Add state management guide with namespace support
- [ ] Update troubleshooting section
- [ ] Add namespace best practices guide

### Timeline
Week 1:
- Days 1-2: TaskConfig implementation
- Days 3-4: BatchContext implementation
- Day 5: State management updates

Week 2:
- Days 1-2: Integration and testing
- Days 3-4: Documentation and examples
- Day 5: Final review and cleanup

### Test Requirements
- Each component must use TaskConfig
- Error handling must include namespace context
- State management must track namespaces
- Coverage >80% for new code
- Tests should verify namespace isolation
- Template resolution tests must cover:
  - Variable substitution in each namespace
  - Error handling for undefined variables
  - State preservation during resume
  - Complex template expressions
  - Nested variable access

### Compatibility
- Maintain backward compatibility
- Provide migration examples
- Document interface changes
- Keep state file format simple
- Ensure template resolution follows engine standards
- Preserve existing namespace behavior
