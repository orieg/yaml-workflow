# YAML Workflow Improvement Plan

## Current State Analysis

### Core Components

1. **Task System** (`src/yaml_workflow/tasks/`)
   - Well-structured `TaskConfig` class in `config.py`
   - Task registration via `register_task` decorator
   - Good separation of task types (file, shell, python, etc.)
   - Consistent error handling pattern but duplicated across tasks

2. **Workflow Engine** (`src/yaml_workflow/engine.py`)
   - Robust workflow execution with flow support
   - Good error handling and state management
   - Template resolution and variable management
   - Some complex error handling logic could be simplified

3. **State Management** (`src/yaml_workflow/state.py`)
   - Clear state persistence
   - Good namespace isolation
   - Retry state handling
   - Could benefit from better type hints

### Documentation Coverage

1. **Well Documented**
   - Basic task usage
   - Workflow structure
   - Error handling patterns
   - CLI usage

2. **Documentation Gaps**
   - Advanced error handling strategies
   - Flow configuration best practices
   - Task development guidelines
   - Type system usage

### Testing Coverage

1. **Strong Coverage**
   - Basic task functionality
   - Template resolution
   - State management
   - CLI operations

2. **Testing Gaps**
   - Complex error scenarios
   - Flow transitions
   - Task type combinations
   - Performance testing

## Improvement Plan

### Phase 1: Error Handling Consolidation

1. **Create Error Handling Utilities** (`src/yaml_workflow/utils/error_handling.py`)
   ```python
   def handle_task_error(task_name: str, error: Exception, config: TaskConfig) -> None:
       """Centralized error handling for tasks."""
       logger = get_task_logger(config.workspace, task_name)
       log_task_error(logger, error)
       if not isinstance(error, TaskExecutionError):
           raise TaskExecutionError(step_name=task_name, original_error=error)
       raise
   ```

2. **Simplify Task Error Handling**
   - Update task implementations to use centralized error handling
   - Remove duplicate try/except blocks
   - Standardize error messages
   - Add error context helpers

### Phase 2: Documentation Enhancement

1. **Task Development Guide** (`docs/guide/task-development.md`)
   ```markdown
   # Task Development Guide
   
   ## Creating New Tasks
   - Using TaskConfig effectively
   - Error handling best practices
   - Type safety guidelines
   - Testing requirements
   
   ## Error Handling Patterns
   - Standard error scenarios
   - Custom error messages
   - Retry strategies
   - Error propagation
   ```

2. **Flow Configuration Guide** (`docs/guide/flows.md`)
   ```markdown
   # Flow Configuration Guide
   
   ## Flow Types
   - Linear flows
   - Conditional flows
   - Error handling flows
   - Parallel execution
   
   ## Best Practices
   - Flow organization
   - Step reuse
   - Error recovery
   - State management
   ```

### Phase 3: Testing Enhancement

1. **Error Scenario Tests**
   ```python
   def test_complex_error_handling():
       """Test complex error scenarios with multiple handlers."""
       # Test error propagation
       # Test retry behavior
       # Test notification chains
       # Test error recovery
   ```

2. **Flow Transition Tests**
   ```python
   def test_flow_transitions():
       """Test transitions between different flows."""
       # Test flow switching
       # Test state preservation
       # Test variable scope
       # Test error recovery
   ```

## Implementation Strategy

### Guidelines

1. **Error Handling**
   - Use centralized error utilities
   - Maintain consistent error patterns
   - Preserve error context
   - Clear error messages

2. **Documentation**
   - Update docs with code changes
   - Include practical examples
   - Document error patterns
   - Add troubleshooting guides

3. **Testing**
   - Test error scenarios first
   - Maintain test coverage
   - Include edge cases
   - Document test patterns

### Quality Gates

Every code change MUST pass these checks before commit:
```bash
# Format and lint
black .
isort .
mypy .

# Run tests
pytest

# Verify
- All tests pass
- Coverage >= 90% for new code
- Documentation updated
```

## Core Changes

1. **Error Handling Core** (`tasks/error_handling.py`)
   ```python
   from dataclasses import dataclass
   from typing import Optional, Dict, Any
   from pathlib import Path
   
   @dataclass
   class ErrorContext:
       step_name: str
       task_type: str
       error: Exception
       retry_count: int = 0
       task_config: Optional[Dict[str, Any]] = None
       template_context: Optional[Dict[str, Any]] = None
   
   def handle_task_error(context: ErrorContext) -> None:
       """Centralized error handling for tasks."""
       logger = get_task_logger(context.task_config.workspace, context.step_name)
       log_task_error(logger, context.error)
       if not isinstance(context.error, TaskExecutionError):
           raise TaskExecutionError(
               step_name=context.step_name,
               original_error=context.error,
               task_config=context.task_config
           )
       raise
   ```

2. **Base Updates** (`tasks/base.py`)
   - Enhance `log_task_error` to use `ErrorContext`
   - Update `get_task_logger` for error state tracking

3. **Task Updates**
   Update each task file to use centralized error handling:
   ```python
   try:
       # task logic
   except Exception as e:
       context = ErrorContext(
           step_name=task_name,
           task_type=self.task_type,
           error=e,
           task_config=self.config.dict()
       )
       handle_task_error(context)
   ```

   Order of updates:
   1. `base.py` - Core error utilities
   2. `config.py` - Error template handling
   3. `batch.py`, `batch_context.py` - Batch processing
   4. File operations: `file_tasks.py`, `file_utils.py`
   5. Execution tasks: `python_tasks.py`, `shell_tasks.py`
   6. Template handling: `template_tasks.py`
   7. Simple tasks: `basic_tasks.py`, `noop.py`

4. **Engine Updates** (`engine.py`)
   - Add error flow handling
   - Implement retry mechanism
   - Update state tracking

5. **State Management** (`state.py`)
   - Add error state persistence
   - Implement retry tracking
   - Add error recovery state

## Test Structure

1. **Core Tests** (`test_error_handling.py`)
   ```python
   def test_error_context_creation():
       """Test error context creation and validation."""
       
   def test_error_handling():
       """Test centralized error handling."""
       
   def test_error_logging():
       """Test error logging functionality."""
   ```

2. **Integration Tests** (`test_error_integration.py`)
   ```python
   def test_error_flow():
       """Test error handling across tasks."""
       
   def test_retry_mechanism():
       """Test retry functionality."""
       
   def test_state_persistence():
       """Test error state handling."""
   ```

3. **Task-Specific Tests**
   Add error handling tests to each task's test file:
   ```python
   def test_task_error_handling():
       """Test task-specific error scenarios."""
       
   def test_task_retry():
       """Test task retry behavior."""
   ```

## Implementation Steps

1. Create `error_handling.py` with core functionality
2. Update `base.py` with enhanced error logging
3. Update each task file in specified order
4. Update engine and state handling
5. Add all test cases
6. Update documentation

Each commit should:
- Focus on one logical change
- Include tests
- Pass all quality gates
- Update relevant documentation

## Implementation Order

Each task below MUST pass all quality gates before proceeding:

1. **Error Handling Core**
   - Create `tasks/error_handling.py`:
     ```python
     # Key functions to implement:
     def handle_task_error(context: ErrorContext) -> None:
         """Centralized error handling for tasks."""
         logger = get_task_logger(context.task_config.workspace, context.step_name)
         log_task_error(logger, context.error)
         if not isinstance(context.error, TaskExecutionError):
             raise TaskExecutionError(
                 step_name=context.step_name,
                 original_error=context.error,
                 task_config=context.task_config
             )
         raise
     ```
   - Add tests in `tests/tasks/test_error_handling.py`
   - Success criteria:
     - All error handling functions typed and documented
     - Test coverage > 90% for new code
     - No mypy errors
   - ✓ Run quality gates
   - Commit changes

2. **Task Implementation Updates**
   - Update tasks in this order:
     1. `base.py` (core error handling)
     2. `config.py` (error configuration)
     3. `batch.py` and `batch_context.py`
     4. `file_tasks.py` and `file_utils.py`
     5. `python_tasks.py`
     6. `shell_tasks.py`
     7. `template_tasks.py`
     8. `basic_tasks.py`
     9. `noop.py`
   - For each task file:
     ```python
     # Update imports
     from ..utils.error_handling import handle_task_error, ErrorContext
     
     # Replace try/except blocks with:
     try:
         # task logic
     except Exception as e:
         context = ErrorContext(
             step_name=task_name,
             task_type=self.task_type,
             error=e,
             task_config=self.config.dict()
         )
         handle_task_error(context)
     ```
   - Success criteria:
     - Consistent error handling across all tasks
     - No duplicate error handling code
     - All tests pass
     - Type safety in all task files
   - ✓ Run quality gates
   - Commit changes

3. **Documentation Enhancement**
   - Create new files:
     - `docs/guide/task-development.md`
     - `docs/guide/flows.md`
     - `docs/guide/error-handling.md`
   - Update existing docs:
     - `docs/workflow-structure.md`
     - `docs/tasks.md`
   - Success criteria:
     - All new features documented
     - Examples for each error scenario
     - Updated workflow examples
   - ✓ Run quality gates
   - Commit changes

4. **Test Suite Enhancement**
   - Add new test files:
     - `tests/test_error_scenarios.py`
     - `tests/test_flow_transitions.py`
   - Success criteria:
     - Coverage > 90% for error handling
     - All edge cases tested
     - Performance tests added
   - ✓ Run quality gates
   - Commit changes

5. **Example Updates**
   - Update examples:
     ```yaml
     # example_workflow.yaml
     steps:
       read_file:
         type: file
         inputs:
           file_path: data.txt
         on_error:
           next: error_handler
     ```
   - Success criteria:
     - All examples runnable
     - Error handling demonstrated
     - Documentation matches examples
   - ✓ Run quality gates
   - Commit changes

### Version Control Guidelines

1. **Commit Messages**
   ```
   Format:
   [component] Brief description
   
   - Detailed change 1
   - Detailed change 2
   
   Quality gates:
   - ✓ black
   - ✓ isort
   - ✓ mypy
   - ✓ pytest
   ```

2. **Branch Strategy**
   - Create feature branch for each task
   - Name format: `feature/error-handling-utils`
   - Merge only after all quality gates pass

Each step should be implemented incrementally with thorough testing to ensure stability. NO changes should be committed until all quality gates pass. Each commit should be atomic and focused on a single logical change. 