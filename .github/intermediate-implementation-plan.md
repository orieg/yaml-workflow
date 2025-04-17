# Intermediate Implementation Plan

This document outlines focused improvements to the YAML Workflow Engine's batch processing capabilities, keeping the system lightweight and practical for local development.

## Phase 2: Batch Processing Improvements

### Goals
- Improve batch processing reliability
- Simplify error handling and recovery
- Add basic progress tracking
- Keep the system lightweight and maintainable

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
            
        # Create consistent batch context
        batch_context = {
            "workspace": workspace,
            "engine": context.get("engine"),
            "batch_name": step.get("name", "unnamed_batch"),
            "retry_config": step.get("retry", {})
        }
        
        # Execute batch processing
        return func(items, step, batch_context)
    return wrapper
```

1. Define standard batch context
   - Consistent access to workspace and engine
   - Standard retry configuration
   - Test: `python -m pytest tests/test_task_interface.py`

2. Update task handlers to use standard interface
   - Python task handler
   - Shell task handler
   - File task handler
   - Test: `python -m pytest tests/test_task_handlers.py`

✓ Checkpoint: Task interface tests pass

#### 2. Consistent Error Handling
```python
# In batch_processor.py
def process_item(self, item: Any, task_config: Dict[str, Any], context: Dict[str, Any]):
    try:
        # Process item using task handler
        result = self.task_handler(item, task_config, context)
        return {"success": True, "result": result}
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
   - Test: `python -m pytest tests/test_error_handling.py`

2. Update engine integration
   - Use standard error handling in WorkflowEngine
   - Consistent retry behavior
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
            "stats": {
                "total": 0,
                "processed": 0,
                "failed": 0,
                "retried": 0
            }
        }
```

1. Standardize state format
   - Common state structure
   - Simple statistics tracking
   - Test: `python -m pytest tests/test_state.py`

2. Integrate with engine state
   - Update WorkflowState integration
   - Keep state format simple
   - Test: `python -m pytest tests/test_state_integration.py`

✓ Checkpoint: State management tests pass

### Implementation Strategy

1. Task Interface (2 days)
   - Implement standard batch context
   - Update task handlers
   ```bash
   python -m pytest tests/test_task_*.py
   ```

2. Error Handling (2 days)
   - Implement consistent error format
   - Update engine integration
   ```bash
   python -m pytest tests/test_error_*.py
   ```

3. State Management (1 day)
   - Implement standard state format
   - Update state integration
   ```bash
   python -m pytest tests/test_state_*.py
   ```

4. Integration (2 days)
   - Verify consistency across components
   - Run full test suite
   ```bash
   python -m pytest tests/
   ```

### Success Criteria
- All task handlers follow the same interface
- Error handling is consistent across components
- State management is uniform and simple
- Changes maintain backward compatibility
- System remains lightweight and practical

### Documentation Updates
- [ ] Document standard batch task interface
- [ ] Update error handling examples
- [ ] Add state management guide
- [ ] Update troubleshooting section

### Timeline
Week 1:
- Days 1-2: Task interface standardization
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

### Compatibility
- Maintain backward compatibility
- Provide migration examples
- Document interface changes
- Keep state file format simple
