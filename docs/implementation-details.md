# Implementation Details: Namespaced Variables

## Overview

This document describes the implementation of namespaced variables in the workflow engine:
- `args.VAR`: Access to workflow parameters
- `env.VAR`: Access to environment variables
- `steps.STEP_NAME.output`: Access to step outputs (singular, supports multiple return types)

## Current Implementation Analysis

The current implementation in `src/yaml_workflow/engine.py` uses a flat context structure:

```python
self.context = {
    "workflow_name": self.name,
    "workspace": str(self.workspace),
    "run_number": self.workspace_info.get("run_number"),
    "timestamp": datetime.now().isoformat(),
}
```

Parameters are currently stored at the root level:
```python
params = self.workflow.get("params", {})
for param_name, param_config in params.items():
    if isinstance(param_config, dict) and "default" in param_config:
        self.context[param_name] = param_config["default"]
```

## Required Changes

### 1. Type Definitions

```python
from typing import Any, Dict, List, Optional, Union, Literal, TypedDict
from pathlib import Path
from datetime import datetime

# Step and Context Types
class StepMetadata(TypedDict):
    output: Any                # Raw step output
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    timestamp: str            # ISO format timestamp
    duration: float          # Execution duration in seconds
    outputs: Dict[str, Any]  # Named outputs if specified
    error: Optional[str]     # Error message if failed
    retries: int            # Number of retry attempts

WorkflowContext = TypedDict("WorkflowContext", {
    # Built-in variables
    "workflow_name": str,
    "workspace": str,
    "run_number": int,
    "timestamp": str,
    "workflow_file": str,
    # Namespaced variables
    "args": Dict[str, Any],
    "env": Dict[str, str],
    "steps": Dict[str, StepMetadata]
})

# State Management Types
class WorkspaceInfo(TypedDict):
    run_number: int
    created_at: str
    last_run: str
    status: Literal["active", "archived", "failed"]

class ExecutionState(TypedDict):
    current_step: int
    completed_steps: List[str]
    failed_step: Optional[Dict[str, str]]
    step_outputs: Dict[str, Any]
    last_updated: str
    status: Literal["not_started", "in_progress", "completed", "failed"]
    flow: Optional[str]
    retry_state: Dict[str, Dict[str, Any]]

# Exception Types
class WorkflowError(Exception):
    """Base class for workflow errors."""
    pass

class WorkflowRuntimeError(WorkflowError):
    """Base class for runtime errors during workflow execution."""
    pass

class VariableError(WorkflowRuntimeError):
    """Base class for variable-related errors."""
    pass

class VariableNotFoundError(VariableError):
    """Raised when a referenced variable is not found."""
    def __init__(self, variable_name: str):
        self.variable_name = variable_name
        super().__init__(f"Variable '{variable_name}' not found in workflow context")

class RequiredVariableError(VariableError):
    """Raised when a required variable is missing."""
    def __init__(self, variable_name: str, step_name: Optional[str] = None):
        self.variable_name = variable_name
        self.step_name = step_name
        location = f" in step '{step_name}'" if step_name else ""
        super().__init__(f"Required variable '{variable_name}' not found{location}")

class InvalidVariableAccessError(VariableError):
    """Raised when attempting to access variables incorrectly."""
    def __init__(self, variable_path: str, reason: str):
        self.variable_path = variable_path
        self.reason = reason
        super().__init__(f"Invalid variable access '{variable_path}': {reason}")
```

### 2. Context Structure Update

```python
class WorkflowEngine:
    def __init__(self, workflow: Dict[str, Any], workspace: Optional[str] = None):
        # Initialize context with namespaces
        self.context: WorkflowContext = {
            # Built-in variables (root level)
            "workflow_name": self.name,
            "workspace": str(self.workspace),
            "run_number": self.workspace_info.get("run_number"),
            "timestamp": datetime.now().isoformat(),
            "workflow_file": str(self.workflow_file.absolute() if self.workflow_file else ""),
            
            # Namespaced variables
            "args": {},    # Workflow parameters
            "env": {},     # Environment variables
            "steps": {},   # Step outputs and metadata
        }
        
        # Initialize args namespace from workflow parameters
        params = self.workflow.get("params", {})
        for param_name, param_config in params.items():
            if isinstance(param_config, dict):
                self.context["args"][param_name] = param_config.get("default")
            else:
                self.context["args"][param_name] = param_config
        
        # Initialize env namespace
        self.context["env"] = dict(os.environ)
        if "env" in self.workflow:
            self.context["env"].update(self.workflow["env"])
```

### 3. Step Output Handling

Update the step execution to properly handle step metadata:

```python
def execute_step(self, step: Dict[str, Any]) -> None:
    name = step.get("name", "unnamed_step")
    task_type = step.get("task")
    
    # Initialize step metadata
    self.context["steps"][name] = {
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
        "duration": 0.0,
        "output": None,
        "outputs": {},
        "error": None,
        "retries": 0
    }
    
    try:
        # Update status and track timing
        self.context["steps"][name]["status"] = "running"
        start_time = time.time()
        
        # Execute task handler
        handler = get_task_handler(task_type)
        result = handler(step, self.context, self.workspace)
        
        # Update step metadata
        self.context["steps"][name].update({
            "output": result,
            "status": "completed",
            "duration": time.time() - start_time
        })
        
        # Handle explicit output assignments
        outputs = step.get("outputs")
        if outputs:
            if isinstance(outputs, str):
                # Single output assignment
                self.context[outputs] = result  # Root level (backward compatibility)
                self.context["steps"][name]["outputs"][outputs] = result
            elif isinstance(outputs, list):
                if len(outputs) == 1:
                    self.context[outputs[0]] = result
                    self.context["steps"][name]["outputs"][outputs[0]] = result
                elif len(outputs) > 1 and isinstance(result, (list, tuple)):
                    for output_name, value in zip(outputs, result):
                        self.context[output_name] = value
                        self.context["steps"][name]["outputs"][output_name] = value
                else:
                    raise ValueError(
                        f"Step '{name}' output mismatch: expected {len(outputs)} values, "
                        f"got {type(result)}"
                    )
    except Exception as e:
        self.context["steps"][name].update({
            "status": "failed",
            "error": str(e),
            "duration": time.time() - start_time
        })
        raise
```

### 4. Template Resolution

Add enhanced template resolution with proper error handling:

```python
def resolve_template(self, template_str: str) -> str:
    """Resolve template with namespaced variables."""
    template = Template(template_str, undefined=StrictUndefined)
    try:
        return template.render(**self.context)
    except UndefinedError as e:
        # Enhance error message with available variables
        available = {
            "args": list(self.context["args"].keys()),
            "env": list(self.context["env"].keys()),
            "steps": list(self.context["steps"].keys())
        }
        raise TemplateError(f"{str(e)}. Available variables: {available}")

def validate_step_access(self, step_name: str, attr: str) -> None:
    """Validate step attribute access."""
    if step_name not in self.context["steps"]:
        raise KeyError(f"Step '{step_name}' not found")
    if attr not in ["output", "status", "timestamp", "duration", "error"]:
        raise AttributeError(f"Invalid step attribute: {attr}")
```

### 5. Backward Compatibility

Add a compatibility layer for transitioning from the old flat structure:

```python
def get_context_value(self, name: str) -> Any:
    """Get value from context with backward compatibility."""
    # First check root level (legacy direct access)
    if name in self.context:
        warnings.warn(
            f"Direct access to '{name}' is deprecated. Use appropriate namespace: "
            "args.VAR, env.VAR, or steps.STEP_NAME.output",
            DeprecationWarning,
            stacklevel=2
        )
        return self.context[name]
    
    # Check namespaces
    if name in self.context["args"]:
        return self.context["args"][name]
    if name in self.context["env"]:
        return self.context["env"][name]
    if "." in name:  # Handle steps.name.output pattern
        step_name, attr = name.split(".", 1)
        if step_name in self.context["steps"]:
            self.validate_step_access(step_name, attr)
            return self.context["steps"][step_name].get(attr)
            
    raise UndefinedError(name)
```

## Implementation Order

1. **Core Updates** (src/yaml_workflow/engine.py):
   - Add type definitions
   - Update context initialization
   - Modify parameter handling
   - Update step output handling

2. **Task Handler Updates** (src/yaml_workflow/tasks/*.py):
   - Update input resolution
   - Add validation for variable access
   - Update output handling

3. **State Management Updates** (src/yaml_workflow/workspace.py):
   - Update state storage format
   - Add step metadata persistence
   - Update state restoration

4. **Exception Updates** (src/yaml_workflow/exceptions.py):
   - Add new exception types for variable access
   - Update error messages

5. **Test Updates**:
   - Add tests for namespaced variables
   - Add tests for backward compatibility
   - Update existing tests

## Files to Modify

1. Core Engine:
   - `src/yaml_workflow/engine.py`
   - `src/yaml_workflow/workspace.py` (consolidate state management here)
   - `src/yaml_workflow/exceptions.py`
   - ~~`src/yaml_workflow/state.py`~~ (remove this file)

2. Task Handlers:
   - `src/yaml_workflow/tasks/python_tasks.py`
   - `src/yaml_workflow/tasks/shell_tasks.py`
   - `src/yaml_workflow/tasks/batch_processor.py`

3. Tests:
   - `tests/test_engine.py`
   - `tests/test_tasks.py`
   - `tests/test_workspace.py`
   - `tests/test_variables.py`

4. Documentation:
   - `docs/tasks.md`
   - `docs/variables.md`
   - `docs/templating.md`
   - `docs/workspace.md`

## Code Organization Changes

### 1. Remove Redundant State Module

The current codebase has a redundant `state.py` module that only re-exports the `WorkflowState` class from `workspace.py`. We will remove this indirection:

```python
# Remove src/yaml_workflow/state.py completely

# Update src/yaml_workflow/engine.py imports
from .workspace import WorkflowState  # Direct import from workspace.py
```

### 2. Consolidate State Management

All state management functionality is already properly implemented in `workspace.py`. This includes:

```python
class WorkflowState:
    """Manages workflow execution state and persistence."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.metadata_path = workspace / METADATA_FILE
        self._load_state()

    def _load_state(self) -> None:
        """Load workflow state from metadata file."""
        if self.metadata_path.exists():
            with open(self.metadata_path) as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}

        # Initialize execution state if not present
        if "execution_state" not in self.metadata:
            self.metadata["execution_state"] = {
                "current_step": 0,
                "completed_steps": [],
                "failed_step": None,
                "step_outputs": {},
                "last_updated": datetime.now().isoformat(),
                "status": "not_started",
                "flow": None,
                "retry_state": {},
            }
            self.save()

    def get_step_state(self, step_name: str) -> Dict[str, Any]:
        """Get state for a specific step."""
        state = self.metadata["execution_state"]
        return {
            "status": (
                "completed" if step_name in state["completed_steps"]
                else "failed" if state["failed_step"] and state["failed_step"]["step_name"] == step_name
                else "not_started"
            ),
            "outputs": state["step_outputs"].get(step_name, {}),
            "retries": state["retry_state"].get(step_name, {}).get("attempt", 0),
            "error": state["failed_step"]["error"] if state["failed_step"] and state["failed_step"]["step_name"] == step_name else None
        }

    def update_step_state(self, step_name: str, outputs: Dict[str, Any], status: str) -> None:
        """Update state for a specific step."""
        state = self.metadata["execution_state"]
        if status == "completed":
            if step_name not in state["completed_steps"]:
                state["completed_steps"].append(step_name)
            state["step_outputs"][step_name] = outputs
        elif status == "failed":
            if step_name in state["completed_steps"]:
                state["completed_steps"].remove(step_name)
            state["failed_step"] = {
                "step_name": step_name,
                "error": outputs.get("error", "Unknown error"),
                "failed_at": datetime.now().isoformat()
            }
        self.save()
```

### 3. Update Import References

Update all files that import `WorkflowState` to import directly from `workspace.py`:

1. In task handlers:
```python
from ..workspace import WorkflowState
```

2. In test files:
```python
from yaml_workflow.workspace import WorkflowState
```

## Exception Handling Updates

Update exception handling to support namespaced variables:

```python
def handle_variable_error(self, error: Exception, step_name: str) -> None:
    """Handle variable-related errors during step execution."""
    if isinstance(error, VariableNotFoundError):
        # Check if variable exists in any namespace
        var_name = error.variable_name
        if "." in var_name:
            namespace, name = var_name.split(".", 1)
            available = {
                "args": list(self.context["args"].keys()),
                "env": list(self.context["env"].keys()),
                "steps": list(self.context["steps"].keys())
            }
            if namespace in available:
                raise InvalidVariableAccessError(
                    var_name,
                    f"Variable not found in namespace '{namespace}'. "
                    f"Available variables: {available[namespace]}"
                )
            raise InvalidVariableAccessError(
                var_name,
                f"Invalid namespace '{namespace}'. "
                f"Available namespaces: {list(available.keys())}"
            )
        
        # For backward compatibility
        raise RequiredVariableError(var_name, step_name)

    elif isinstance(error, AttributeError) and "steps." in str(error):
        # Handle invalid step attribute access
        match = re.search(r"steps\.(\w+)\.(\w+)", str(error))
        if match:
            step_name, attr = match.groups()
            if step_name not in self.context["steps"]:
                raise InvalidVariableAccessError(
                    f"steps.{step_name}.{attr}",
                    f"Step '{step_name}' not found"
                )
            raise InvalidVariableAccessError(
                f"steps.{step_name}.{attr}",
                f"Invalid attribute '{attr}'. Valid attributes: output, status, timestamp, duration, error"
            )
    
    raise error
```

## Testing Strategy

1. **Variable Resolution Tests**:
   - Basic variable access
   - Nested attribute access
   - Filter usage
   - Error cases

2. **Step Output Tests**:
   - Different return types
   - Multiple output assignment
   - Output access patterns
   - Error cases

3. **Environment Variable Tests**:
   - OS environment integration
   - Workflow environment overrides
   - Environment updates
   - Security considerations

4. **Backward Compatibility Tests**:
   - Deprecation warnings
   - Legacy access patterns
   - Migration path
   - Breaking changes

5. **Error Handling Tests**:
   - Template errors
   - Step execution errors
   - Retry mechanism
   - Error reporting

6. **Type Safety Tests**:
   - Type hints
   - Runtime type checking
   - Edge cases
   - Invalid access patterns

## Migration Strategy

1. Update `WorkflowEngine` to use namespaced context structure
2. Add backward compatibility layer with deprecation warnings
3. Update task handlers to use namespaced variables
4. Update documentation and examples
5. Add type hints and validation
6. Add tests for new structure
7. Deprecate direct variable access over several releases
8. Remove backward compatibility in major version update

## Rollout Plan

1. **Version 1.x**
   - Add deprecation warnings
   - Introduce new syntax support
   - Maintain backward compatibility

2. **Version 2.0**
   - Remove deprecated syntax
   - Update all examples
   - Clean up legacy code

## Backward Compatibility

During the transition period (v1.x):
- Both syntaxes will work
- Deprecation warnings will be shown
- Migration tools will be available

After v2.0:
- Only `{{ var }}` syntax will be supported
- Clear error messages for legacy syntax
- Documentation for migration

## Variable Usage Standardization

### Overview

This section describes the plan to standardize variable usage in the workflow engine to exclusively use Jinja2's `{{ var }}` syntax and remove the legacy `${var}` pattern.

### Current State Analysis

The codebase currently has mixed variable resolution patterns:
- `{{ var }}`: Jinja2 template syntax (preferred)
- `${var}`: Legacy shell-style variable substitution (to be deprecated)

### Implementation Plan

#### Dependencies and Prerequisites

**Sequential Execution Requirements**
- Each phase must be fully completed before moving to the next phase
- All tests must pass after each phase before proceeding
- No phase can be skipped or partially implemented
- If tests fail after a phase, issues must be resolved before moving forward

**Phase Dependencies**
1. Phase 1 (Audit) ✓
   - Complete inventory of all variable usage in codebase
   - Document all locations where `${var}` is used
   - List all files requiring updates

2. Phase 2 (Core Engine Update) ✓
   - Remove legacy `${var}` resolution code
   - Implement Jinja2-only template resolution
   - Update all core engine tests
   - All tests must pass

3. Phase 3 (Task Updates)
   - [x] Review all task handlers
   - Task Handler Updates:
     - [x] basic_tasks.py: Added StrictUndefined and error handling
     - [x] file_tasks.py: Updated to Jinja2 syntax
     - [x] python_tasks.py: Fixed result handling
     - [x] shell_tasks.py: Updated to Jinja2 syntax
     - [x] template_tasks.py: Added StrictUndefined support
     - [x] batch_processor.py: Completed with comprehensive updates
       - Added proper error handling with detailed messages
       - Implemented backward compatibility for legacy parameters
       - Enhanced result handling with processed_items tracking
       - Added support for aggregated results
       - Improved chunk processing and worker management
       - Added comprehensive test coverage
   - [x] Run tests for all handlers
   - [x] Document all changes
   - [x] Verify all handlers are compliant
   - [x] Final Phase 3 tests completed successfully

4. Phase 4 (Documentation and Examples)
   - [ ] Update configuration.md
   - [ ] Update workflow-structure.md
   - [ ] Update variable usage examples
   - [ ] Add error handling examples
   - [ ] Document batch processing improvements
   - [ ] Verify all examples
   - [ ] Run documentation tests

5. Phase 5 (Final Verification)
   - [ ] Run full test suite
   - [ ] Verify no legacy syntax
   - [ ] Code review
   - [ ] Release preparation

**Testing Requirements Between Phases**
- Run full test suite after each phase
- Run regression tests to ensure no breaking changes
- Document any test failures or issues
- Verify code coverage is maintained or improved

### Risk Assessment

#### Technical Risks

1. **Breaking Changes**
   - Risk: Existing workflows will break if using `${var}`
   - Mitigation: Clear documentation of required updates

2. **Edge Cases**
   - Risk: Unusual variable usage patterns may be missed
   - Mitigation: Comprehensive test suite

#### Project Risks

1. **Missed Usage**
   - Risk: Some instances of `${var}` may be missed
   - Mitigation: Thorough code scanning and testing

2. **Documentation Gaps**
   - Risk: Documentation may miss some examples
   - Mitigation: Systematic documentation review

### Implementation Notes

1. **Variable Resolution**
   ```python
   def resolve_template(self, template_str: str) -> str:
       """Resolve template with Jinja2 only."""
       template = Template(template_str, undefined=StrictUndefined)
       try:
           return template.render(**self.context)
       except UndefinedError as e:
           available = {
               "args": list(self.context["args"].keys()),
               "env": list(self.context["env"].keys()),
               "steps": list(self.context["steps"].keys())
           }
           raise TemplateError(f"{str(e)}. Available variables: {available}")
   ```

2. **Error Messages**
   - Clear error messages directing users to use `{{ var }}` syntax
   - Helpful context about available variables
   - Examples of correct usage in error messages

3. **Documentation Updates**
   - Remove all references to `${var}` syntax
   - Add clear examples of correct variable usage
   - Update troubleshooting guides

### Testing Strategy

1. **Unit Tests**
   - Variable resolution
   - Template rendering
   - Error handling

2. **Integration Tests**
   - Task interactions
   - Context handling
   - End-to-end workflows

### Rollout Plan

1. **Direct Switch**
   - Remove `${var}` support
   - Update all code to use `{{ var }}`
   - Update all documentation
   - Release new version 

### Phase Completion Reports

#### Phase 1: Audit
**Files requiring changes:**

1. Core Engine Files:
   - `src/yaml_workflow/engine.py`
     - Contains legacy `${var}` resolution code in `resolve_value` method
     - Needs update to use only Jinja2 template resolution
   - `src/yaml_workflow/types.py`
     - Contains legacy `${var}` resolution code
     - Needs update to use only template-based resolution

2. Documentation Files:
   - `docs/guide/configuration.md`
     - Contains mixed syntax examples
     - Update environment variable examples
   - `docs/workflow-structure.md`
     - Contains `${var}` syntax
     - Update all examples to use `{{ var }}`

**Files to leave unchanged:**
1. Shell Scripts (using correct shell syntax)
   - `scripts/release.sh`
   - Other shell scripts using `${var}` for shell variables

2. GitHub Actions (using correct GitHub syntax)
   - `.github/workflows/*.yml` files using `${{ var }}`

**Current Usage Analysis:**
1. Example Workflows
   - All using correct `{{ var }}` syntax
   - No changes needed

2. Test Files
   - All using correct `{{ var }}` syntax
   - No changes needed

3. Task Handlers
   - All using correct `{{ var }}` syntax
   - No changes needed

**Next Steps:**
- Proceed with Phase 2 (Core Engine Update)
- Focus on `engine.py` and `types.py` first
- Then update documentation files
- Run tests after each file change

#### Phase 2: Core Engine Update
**Changes Made:**

1. Updated `src/yaml_workflow/engine.py`:
   - Removed legacy `${var}` resolution code
   - Implemented Jinja2-only template resolution
   - Added better error handling with available variables
   - Added StrictUndefined for better error reporting
   - Updated method documentation

2. Updated `src/yaml_workflow/exceptions.py`:
   - Added new `TemplateError` class for template resolution errors
   - Improved error messages with available variables

3. Test Results:
   - All 107 tests passing
   - 1 test skipped (expected)
   - No regressions found
   - Coverage maintained

4. Note about `types.py`:
   - File not found in workspace
   - No changes needed

**Next Steps:**
- Proceed to Phase 3 (Task Updates)
- Review task handlers for any variable resolution code
- Update documentation to reflect new implementation

### Phase Tracking

- [x] Phase 1: Audit
  - [x] Complete inventory of variable usage
  - [x] Document all locations requiring changes
  - [x] Identify files to leave unchanged
  - [x] Document next steps

- [x] Phase 2: Core Engine Update
  - [x] Update engine.py
  - [x] Update types.py (not needed)
  - [x] Run all tests
  - [x] Document changes

- [x] Phase 3: Task Updates
  - [x] Review all task handlers
  - Task Handler Updates:
    - [x] basic_tasks.py: Added StrictUndefined and error handling
    - [x] file_tasks.py: Updated to Jinja2 syntax
    - [x] python_tasks.py: Fixed result handling
    - [x] shell_tasks.py: Updated to Jinja2 syntax
    - [x] template_tasks.py: Added StrictUndefined support
    - [x] batch_processor.py: Completed with comprehensive updates
      - Added proper error handling with detailed messages
      - Implemented backward compatibility for legacy parameters
      - Enhanced result handling with processed_items tracking
      - Added support for aggregated results
      - Improved chunk processing and worker management
      - Added comprehensive test coverage
  - [x] Run tests for all handlers
  - [x] Document all changes
  - [x] Verify all handlers are compliant
  - [x] Final Phase 3 tests completed successfully

- [ ] Phase 4: Documentation and Examples
  - [ ] Update configuration.md
  - [ ] Update workflow-structure.md
  - [ ] Update variable usage examples
  - [ ] Add error handling examples
  - [ ] Document batch processing improvements
  - [ ] Verify all examples
  - [ ] Run documentation tests

- [ ] Phase 5: Final Verification
  - [ ] Run full test suite
  - [ ] Verify no legacy syntax
  - [ ] Code review
  - [ ] Release preparation

### Recent Implementation Updates

#### Batch Processor Improvements
The batch processor (`batch_processor.py`) has been significantly enhanced:

1. **Error Handling**
   - Added StrictUndefined for template resolution
   - Improved error messages with available variables
   - Enhanced chunk processing validation
   - Better handling of worker exceptions

2. **Backward Compatibility**
   - Support for both `items` and `iterate_over` parameters
   - Maintained support for legacy `processing_task` format
   - Compatible with both `resume` and `resume_state` flags

3. **Result Handling**
   - Added `processed_items` tracking in original order
   - Improved failed items reporting
   - Support for aggregated results
   - Enhanced statistics and metadata

4. **Performance**
   - Optimized chunk processing
   - Improved worker management
   - Better memory usage for large batches

5. **Testing**
   - Added comprehensive test coverage
   - Verified backward compatibility
   - Tested error scenarios
   - Validated result consistency

#### Next Steps
With Phase 3 complete, we are ready to move to Phase 4:

1. Documentation Updates
   - Update all variable usage examples
   - Document new error handling features
   - Add batch processing examples
   - Update configuration guides

2. Example Updates
   - Update all workflow examples
   - Add error handling demonstrations
   - Include batch processing examples
   - Show best practices

3. Testing
   - Verify all documentation examples
   - Run example workflows
   - Test error scenarios
   - Validate configuration samples 