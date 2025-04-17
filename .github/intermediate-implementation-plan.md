# Intermediate Implementation Plan

This document outlines focused improvements to the YAML Workflow Engine's batch processing capabilities, building upon the template engine centralization work. These improvements maintain the system's lightweight nature while ensuring consistency with the centralized template processing approach.

## Phase 2: Batch Processing Improvements

### Goals
- Improve batch processing reliability and template resolution consistency
- Simplify error handling and recovery
- Add basic progress tracking
- Keep the system lightweight and maintainable
- Ensure seamless integration with centralized template engine

### Integration with Template Engine Centralization
This plan builds upon the completed work in template engine centralization:
- Uses the engine's centralized template resolution
- Maintains consistent Jinja2 feature support
- Leverages improved error handling for template resolution
- Builds on the enhanced state management system

### Tasks

#### 1. Standardize Task Interface
```python
# In tasks/__init__.py
def create_batch_task_handler(func):
    """Decorator to standardize batch task handling."""
    def wrapper(step: Dict[str, Any], context: Dict[str, Any], workspace: Path):
        # Standard pre-processing
        items = step.get("items") or step.get("iterate_over")
        if not items:
            raise ValueError("No items provided for batch processing")
            
        # Create consistent batch context with template engine access
        batch_context = {
            "workspace": workspace,
            "engine": context.get("engine"),  # Used for centralized template resolution
            "batch_name": step.get("name", "unnamed_batch"),
            "retry_config": step.get("retry", {}),
            "template_context": context.get("template_context", {})  # Template variables
        }
        
        # Execute batch processing
        return func(items, step, batch_context)
    return wrapper
```

1. Define standard batch context
   - Consistent access to workspace and engine
   - Standard retry configuration
   - Integration with template engine context
   - Test: `python -m pytest tests/test_task_interface.py`

2. Update task handlers to use standard interface
   - Python task handler (using engine.resolve_template)
   - Shell task handler (using engine.resolve_template)
   - File task handler (using engine.resolve_template)
   - Test: `python -m pytest tests/test_task_handlers.py`

✓ Checkpoint: Task interface tests pass

#### 2. Consistent Error Handling
```python
# In batch_processor.py
def process_item(self, item: Any, task_config: Dict[str, Any], context: Dict[str, Any]):
    try:
        # Process item using task handler with template resolution
        resolved_config = context["engine"].resolve_template(
            task_config,
            {"item": item, **context.get("template_context", {})}
        )
        result = self.task_handler(item, resolved_config, context)
        return {"success": True, "result": result}
    except TemplateError as te:
        error_info = {
            "success": False,
            "error": str(te),
            "item": item,
            "template_context": te.context,  # Include available variables
            "retryable": False
        }
        self.logger.error(f"Template error processing item {item}: {te}", extra=error_info)
        return error_info
    except Exception as e:
        error_info = {
            "success": False,
            "error": str(e),
            "item": item,
            "retryable": isinstance(e, (IOError, TimeoutError))
        }
        self.logger.error(f"Failed to process item {item}: {e}", extra=error_info)
        return error_info
```

1. Standardize error format
   - Common error structure
   - Consistent retry hints
   - Template-specific error handling
   - Test: `python -m pytest tests/test_error_handling.py`

2. Update engine integration
   - Use standard error handling in WorkflowEngine
   - Consistent retry behavior
   - Template resolution error propagation
   - Test: `python -m pytest tests/test_engine_integration.py`

✓ Checkpoint: Error handling tests pass

#### 3. Simplified State Management
```python
# In batch_processor.py
class BatchProcessor:
    def __init__(self, workspace: Path, name: str):
        self.state = {
            "processed": [],  # Keep order for resume
            "failed": {},     # item -> error info
            "template_errors": {},  # Track template resolution failures
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
   - Common state structure
   - Simple statistics tracking
   - Template resolution state tracking
   - Test: `python -m pytest tests/test_state.py`

2. Integrate with engine state
   - Update WorkflowState integration
   - Keep state format simple
   - Preserve template context for resume
   - Test: `python -m pytest tests/test_state_integration.py`

✓ Checkpoint: State management tests pass

### Implementation Strategy

1. Task Interface (2 days)
   - Implement standard batch context
   - Update task handlers to use engine.resolve_template
   - Verify template resolution consistency
   ```bash
   python -m pytest tests/test_task_*.py
   ```

2. Error Handling (2 days)
   - Implement consistent error format
   - Update engine integration
   - Add template-specific error cases
   ```bash
   python -m pytest tests/test_error_*.py
   ```

3. State Management (1 day)
   - Implement standard state format
   - Update state integration
   - Add template resolution state
   ```bash
   python -m pytest tests/test_state_*.py
   ```

4. Integration (2 days)
   - Verify consistency across components
   - Test template resolution in batch context
   - Run full test suite
   ```bash
   python -m pytest tests/
   ```

### Success Criteria
- All task handlers follow the same interface and use engine.resolve_template
- Error handling is consistent across components, including template errors
- State management is uniform and simple
- Changes maintain backward compatibility
- System remains lightweight and practical
- Template resolution is consistent across all batch operations

### Documentation Updates
- [ ] Document standard batch task interface
- [ ] Update error handling examples, including template errors
- [ ] Add state management guide
- [ ] Update troubleshooting section with template resolution examples
- [ ] Add migration guide for template resolution changes

### Timeline
Week 1:
- Days 1-2: Task interface standardization and template integration
- Days 3-4: Error handling consistency
- Day 5: State management updates

Week 2:
- Days 1-2: Integration and testing
- Days 3-4: Documentation and examples
- Day 5: Final review and cleanup

### Test Requirements
- Each component must follow standard interfaces
- Error handling must be consistent
- State management must be uniform
- Coverage >80% for new code
- Tests should verify consistency
- Template resolution tests must cover:
  - Variable substitution in batch items
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
