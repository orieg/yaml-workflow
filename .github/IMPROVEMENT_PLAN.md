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

## Project Setup

1. **Virtual Environment**
   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```

2. **Development Installation**
   ```bash
   # Install package in editable mode with all development dependencies
   pip install -e ".[dev,test,doc]"
   ```

3. **Dependencies Groups**
   ```toml
   # pyproject.toml
   [project.optional-dependencies]
   dev = [
       "black",
       "isort",
       "mypy",
   ]
   test = [
       "pytest>=7.0",
       "pytest-cov",
   ]
   doc = [
       "sphinx",
       "sphinx-rtd-theme",
   ]
   ```

4. **Verify Setup**
   ```bash
   # Verify installation and dependencies
   python -c "import yaml_workflow; print(yaml_workflow.__version__)"
   pytest --version
   black --version
   ```

## Improvement Plan

### Phase 1: Error Handling Consolidation

1. **Create Error Handling Utilities** (`src/yaml_workflow/tasks/error_handling.py`)
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

### Version Control Process

1. **Branch Strategy**
   ```bash
   # Create feature branch
   git checkout -b feature/error-handling-utils

   # Regular commits during development
   # Prepare the multi-line commit message in /tmp/commit_msg.txt according to the format below.
   # (Ensure the file is created correctly before committing, see note below)
   git add .
   git commit -F /tmp/commit_msg.txt # Use -F for multi-line messages from file

   # After passing quality gates
   git push origin feature/error-handling-utils
   ```

2. **Commit Message Format**
   ```
   [type] Short summary (50 chars)
   <blank line>
   Detailed explanation of the change, wrapped at 72 characters.
   Explain what and why vs. how.
   <blank line>
   - Bullet points for specific changes
   - Start with verbs in imperative mood
   ```

   Types: [feat], [fix], [docs], [test], [refactor], [chore]

   *Note: To ensure proper formatting for multi-line commit messages like the one described above, it's recommended to use `git commit -F <file>` or pipe the message via `git commit -F -`. If using automation, verify that the temporary file `/tmp/commit_msg.txt` is created with the exact required multi-line content before running the commit command. Manual file creation might be necessary if the automation tool struggles with reliable multi-line file generation.*

### Implementation Order

- [x] 1. **Setup Phase**
   ```bash
   # Verify directories (already exist)
   # src/yaml_workflow/utils/
   # src/yaml_workflow/tasks/
   # src/yaml_workflow/tests/
   # docs/guide/

   # Virtual Environment (assuming already active or managed externally)
   # python -m venv .venv
   # source .venv/bin/activate

   # Dependencies (assuming already installed or managed externally)
   # pip install -e ".[dev,test,doc]"

   # Verify Installation
   python -c "import yaml_workflow; print(yaml_workflow.__version__)"
   ```
   Success Criteria:
   - Required directories exist
   - Virtual environment is active (if used)
   - Development dependencies are installed
   - Package is importable and basic checks pass

- [x] 2. **Error Handling Phase**
   ```bash
   # Create/Verify files
   # touch src/yaml_workflow/tasks/error_handling.py
   # touch src/yaml_workflow/tasks/__init__.py  # Ensure it exists
   # touch tests/test_error_handling.py
   ```
   Implementation Order:
   - [x] 1. Create ErrorContext class
   - [x] 2. Implement handle_task_error
   3. Update base task class (Skipped/Defered - Handled within handle_task_error)
   - [x] 4. Add error handling tests
   Success Criteria:
   - All error handling tests pass
   - No duplicate error code
   - Coverage > 90%

- [ ] 3. **Documentation Phase**
   ```bash
   # Create/Verify doc files
   # touch docs/guide/task-development.md
   # touch docs/guide/flows.md
   # touch docs/guide/error-handling.md
   ```
   Implementation Order:
   1. Write task development guide
   2. Document error handling patterns
   3. Create flow configuration guide
   4. Add runnable examples
   Success Criteria:
   - All guides complete
   - Examples tested and working
   - No broken links
   - Documentation builds

- [ ] 4. **Testing Phase**
   ```bash
   # Create/Verify test files
   # touch tests/test_error_scenarios.py
   # touch tests/test_flow_transitions.py
   ```
   Implementation Order:
   1. Implement error scenario tests
   2. Add flow transition tests
   3. Add performance tests
   4. Verify coverage
   Success Criteria:
   - All tests pass
   - Coverage meets targets
   - Performance tests pass
   - Edge cases covered

### Quality Verification

Each phase must pass these checks:
```bash
# 1. Code Quality
black . && isort . && mypy .

# 2. Tests
pytest --cov=yaml_workflow tests/

# 3. Documentation Build (using MkDocs)
mkdocs build --clean --strict

# 4. Git Status
git status  # Ensure all changes committed
git push    # Push to remote
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
       logger = get_task_logger(context.task_config.get('workspace', '.'), context.step_name)
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
   1. `base.py` - Core error utilities (Skipped/Defered - Handled within handle_task_error)
   - [x] 2. `config.py` - Error template handling
   - [x] 3. `batch.py`, `batch_context.py` - Batch processing
   - [x] 4. File operations: `file_tasks.py`, `file_utils.py`
   - [x] 5. Execution tasks: `python_tasks.py`
   - [x] 5. Execution tasks: `shell_tasks.py`
   - [ ] 6. Template handling: `template_tasks.py`
   - [ ] 7. Simple tasks: `basic_tasks.py`, `noop.py`

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
       """Test centralized error handling logic."""
       
   def test_error_logging():
       """Test error logging functionality."""
   ```

2. **Integration Tests** (`test_error_integration.py`)
   ```python
   def test_error_flow():
       """Test error handling across multiple tasks and flows."""
       
   def test_retry_mechanism():
       """Test retry functionality integrated with engine."""
       
   def test_state_persistence():
       """Test error state persistence and recovery."""
   ```

3. **Task-Specific Tests**
   Add error handling tests to each task's test file:
   ```python
   def test_file_task_error_handling():
       """Test task-specific error scenarios (e.g., file not found)."""
       
   def test_file_task_retry():
       """Test task retry behavior for file operations."""
   ```

## Example Updates

Update examples to demonstrate new error handling features:
```yaml
# example_workflow.yaml
steps:
  read_file:
    type: file
    inputs:
      file_path: non_existent_data.txt
    on_error:
      next: error_handler
      retry: 3

  error_handler:
    type: noop # Or a specific error reporting task
    # ... configuration for error handling step ...
```

Each step should be implemented incrementally with thorough testing to ensure stability. NO changes should be committed until all quality gates pass. Each commit should be atomic and focused on a single logical change. 