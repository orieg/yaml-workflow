# YAML Workflow Improvement Plan

## Current State Analysis

### Core Components

1. **Task System** (`src/yaml_workflow/tasks/`)
   - Well-structured `TaskConfig` class in `config.py`
   - Task registration via `register_task` decorator
   - Good separation of task types (file, shell, python, etc.)
   - Consistent error handling pattern but duplicated across tasks
   - **Task output handling is inconsistent**: The `outputs` field allows mapping to top-level context, creating confusion alongside the more complete `steps` namespace.

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
   - Task development guidelines (including output handling)
   - Type system usage
   - **Clear explanation of standardized output access (`steps` namespace)**

### Testing Coverage

1. **Strong Coverage**
   - Basic task functionality
   - Template resolution
   - State management
   - CLI operations
   - **Verification of standardized output access (`steps` namespace)**
   - **Tests relying on deprecated top-level output mapping need updates**

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

1. **[x] Create Error Handling Utilities** (`src/yaml_workflow/tasks/error_handling.py`)
   ```python
   def handle_task_error(task_name: str, error: Exception, config: TaskConfig) -> None:
       """Centralized error handling for tasks."""
       logger = get_task_logger(config.workspace, task_name)
       log_task_error(logger, error)
       if not isinstance(error, TaskExecutionError):
           raise TaskExecutionError(step_name=task_name, original_error=error)
       raise
   ```

2. **[x] Simplify Task Error Handling**
   - Update task implementations to use centralized error handling (e.g., shell_task)
   - Remove duplicate try/except blocks
   - Standardize error messages
   - Add error context helpers

3. **[x] Standardize error messages**
   - Update task implementations to use centralized error handling
   - Remove duplicate try/except blocks
   - Standardize error messages
   - Add error context helpers

4. **[x] Add error context helpers**
   - Update task implementations to use centralized error handling
   - Remove duplicate try/except blocks
   - Standardize error messages
   - Add error context helpers

### Phase 2: Standardize Task Output Handling & Access

**Goal:** Simplify and standardize how task outputs are stored and accessed, ensuring all task return values are stored under a dedicated `result` key within the `steps` namespace (e.g., `steps.STEP_NAME.result`) to prevent key collisions and provide a consistent access pattern.

1. **[x] Engine Refinement (`engine.py`)**: 
    - Modify `execute_step` to *always* wrap the task's return value and store it as `self.context['steps'][step_name] = {"result": return_value}`.
    - Remove the previous logic that stored dictionaries directly.

2. **[x] Task Review & Update (`tasks/`)**: 
    - Review built-in tasks to confirm their return values (single values or dictionaries) are appropriate for being stored under the `result` key. (Implicitly done for echo/shell via examples/tests).

3. **[x] Update Examples (`src/yaml_workflow/examples/`)**: 
    - Modify all example YAML files to access previous step outputs *exclusively* using the `{{ steps.STEP_NAME.result }}` or `{{ steps.STEP_NAME.result.KEY }}` pattern. (Done for complex_flow_error_handling).

4. **[x] Add/Update Tests (`tests/`)**: 
    - Add/Update tests verifying that results are correctly stored and accessible via `steps.STEP_NAME.result` or `steps.STEP_NAME.result.KEY`. (Done for complex_flow_error_handling tests).
    - Ensure no tests rely on direct access like `steps.STEP_NAME.KEY`.

### Phase 3: Documentation Enhancement (Renumbered)

1. **[x] Update/Create Task Development Guide Content** (e.g., in `docs/development.md` or `docs/tasks.md`)
   - Add/Update sections covering:
       - Using TaskConfig effectively
       - Error handling best practices (using `handle_task_error`)
       - Type safety guidelines
       - Testing requirements
       - Returning Results (Dicts vs Single Values)
       - Accessing Previous Step Outputs (Using `steps` Namespace)

2. **[x] Update Core Concepts/Usage Guides**:
   - Review existing files (`index.md`, `cli.md`, `state.md`, etc.)
   - Ensure all guides consistently use and explain the `steps.STEP_NAME.result.KEY` access pattern.
   - Remove or update sections explaining the old `outputs` top-level mapping.

3. **[x] Update/Create Flow Configuration Guide Content** (e.g., in `docs/workflow-structure.md` or a new `docs/guide/flows.md`)
   - Add/Update sections covering:
       - Flow Types (Linear, Conditional, Error Handling, etc.)
       - Best Practices (Organization, Reuse, Recovery, State)

4. **[x] Update/Create Error Handling Patterns Guide Content** (e.g., in `docs/workflow-structure.md` or a new `docs/guide/error-handling.md`)
   - Add/Update sections covering:
       - Standard error scenarios (`on_error`: retry, continue, next)
       - Custom error messages
       - Error propagation

5. **[x] Add Runnable Examples to Guides**
   - Integrate small, runnable examples directly into relevant documentation sections.

### Phase 4: Testing Enhancement (Renumbered)

1. **[x] Add specific complex error scenario tests** (Addressed via `test_examples.py` for `complex_flow_error_handling.yaml`. Consider adding more if needed.)

2. **[x] Add specific flow transition tests** (Addressed via `test_examples.py` for `complex_flow_error_handling.yaml`. Consider adding more if needed.)

3. **[x] Add example workflow integration tests** (`tests/test_examples.py`) (Partially done for `complex_flow_error_handling.yaml`. Review other examples.)

4. **[ ] Add performance tests**
    - Create `tests/test_performance.py`.
    - Add tests measuring execution time for common/complex workflows.
    - Add tests measuring memory usage (if feasible).

5. **[~] Improve overall test coverage and fix existing issues**
    - Run `pytest --cov=src/yaml_workflow --cov-report term-missing` to check coverage.
    - Identify and test uncovered code paths.
    - Aim for a target coverage percentage (e.g., 90%).

### Implementation Strategy

### Guidelines

1. **Error Handling**
   - Use centralized error utilities
   - Maintain consistent error patterns
   - Preserve error context
   - Clear error messages

2. **Output Handling**
   - Standardize on `steps.STEP_NAME.KEY` access.
   - Ensure tasks return predictable structures (dicts or single values).
   - Remove/Deprecate top-level context mapping via `outputs`.

3. **Documentation**
   - Update docs with code changes (error handling, output handling)
   - Include practical examples
   - Document error patterns
   - Add troubleshooting guides

4. **Testing**
   - Test error scenarios first
   - **Test standardized output access patterns**
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
   - [x] 3. Update tasks (e.g., shell_task)
   - [x] 4. Add error handling tests
   Success Criteria:
   - All error handling tests pass
   - No duplicate error code
   - Coverage > 90%

- [x] 3. **Standardize Task Output Handling Phase**
   Implementation Order:
   - [x] 1. Refine engine `execute_step` to ensure results stored under `steps.STEP_NAME.result`.
   - [x] 2. Review and update tasks for consistent returns.
   - [x] 3. Update examples to use `steps.` namespace.
   - [x] 4. Add/Update tests for `steps.` namespace access.
   Success Criteria:
   - All task outputs accessed via `steps.STEP_NAME.result` or `steps.STEP_NAME.result.KEY`.
   - Top-level output mapping is removed or warned.

- [x] 4. **Documentation Phase** (Renumbered)
   ```
   Implementation Order:
   - [x] 1. Update task development guide (incl. output handling).
   - [x] 2. Update core guides to reflect standardized output access.
   - [x] 3. Document error handling patterns.
   - [ ] 4. Review/Update other core docs (index, cli, state, etc.).
   - [x] 5. Add runnable examples to guides.
   Success Criteria:
   - Documentation accurately reflects current error handling and output access patterns.

- [ ] 5. **Testing Enhancement Phase** (Renumbered - excluding work already done in examples)
   Implementation Order:
   - [ ] 1. Add performance tests.
   - [~] 2. Review and improve overall test coverage. (Partially addressed by CLI test additions)
   - [ ] 3. Run coverage checks (`pytest --cov`).
   Success Criteria:
   - Added tests cover remaining gaps.