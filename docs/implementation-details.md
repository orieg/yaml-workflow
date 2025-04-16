# Implementation Details: Namespaced Variables

## Overview

This document describes the implementation of namespaced variables in the workflow engine:
- `args.VAR`: Access to workflow parameters
- `env.VAR`: Access to environment variables
- `steps.STEP_NAME.output`: Access to step outputs (singular, supports multiple return types)

## Current Implementation

The workflow engine uses a namespaced context structure for all variable access:

```python
self.context = {
    # Built-in variables
    "workflow_name": self.name,
    "workspace": str(self.workspace),
    "run_number": self.workspace_info.get("run_number"),
    "timestamp": datetime.now().isoformat(),
    "workflow_file": str(self.workflow_file.absolute() if self.workflow_file else ""),
    
    # Namespaced variables
    "args": {},    # Workflow parameters
    "env": dict(os.environ),  # Environment variables
    "steps": {},   # Step outputs and metadata
}
```

### Variable Resolution

Template resolution is handled using Jinja2 with StrictUndefined for better error detection:

```python
def resolve_template(self, template_str: str) -> str:
    """Resolve template with both direct and namespaced variables."""
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
```

## Batch Processing Implementation

### Overview

The batch processing functionality allows parallel execution of tasks over a collection of items with the following features:
- Parallel execution with configurable worker limits
- Chunked processing for large datasets
- State persistence and resume capability
- Progress tracking and error handling
- Result aggregation
- Backward compatibility with legacy configurations

### Current Status

✅ Completed Features:
- Parallel execution with proper worker limits
- Result handling and ordering
- Error handling and state management
- Progress tracking and callbacks
- Support for both `items` and `iterate_over` parameters
- Support for both direct settings and `parallel_settings`
- Compatibility with legacy `processing_task` format
- Result aggregation
- State persistence and resume capability
- Enhanced error reporting with detailed messages
- Basic performance optimizations

🔄 Ongoing Optimizations:
- Advanced performance optimizations for large datasets
- Dynamic chunk size adjustment based on workload
- Resource usage monitoring and throttling
- Enhanced state recovery mechanisms

### Implementation Details

The batch processor is implemented in two main components:

1. BatchProcessor Class:
```python
class BatchProcessor:
    def __init__(self, workspace: Union[str, Path], name: str):
        self.workspace = Path(workspace)
        self.name = name
        self.state_dir = self.workspace / ".batch_state"
        self.state_file = self.state_dir / f"{name}_state.json"

    def process_batch(
        self,
        items: List[Any],
        task_config: Dict[str, Any],
        context: Dict[str, Any],
        chunk_size: int = 10,
        max_workers: Optional[int] = None,
        resume_state: bool = False,
        progress_callback: Optional[Callable] = None,
        error_handler: Optional[Callable] = None,
        aggregator: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        # Implementation handles:
        # - Parallel processing with worker limits
        # - Chunked processing
        # - State management
        # - Result aggregation
        # - Progress tracking
        # Returns processed results and statistics
```

2. Task Registration:
```python
@register_task("batch_processor")
def process_batch(step: Dict[str, Any], context: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    # Configuration handling:
    # - Support both items and iterate_over
    # - Handle parallel_settings
    # - Support legacy processing_task format
    # Returns:
    {
        "processed": List[str],        # Successfully processed item IDs
        "failed": List[str],           # Failed item IDs
        "results": List[Any],          # Raw results
        "stats": Dict[str, Any],       # Processing statistics
        "processed_items": List[Any],   # Ordered results
        "failed_items": List[Any],      # Failed items
        "aggregated_result": Any        # Optional aggregated result
    }
```

### Configuration Example

```yaml
steps:
  - name: process_data
    task: batch_processor
    items:                    # or iterate_over for backward compatibility
      - item1
      - item2
      - item3
    parallel_settings:
      max_workers: 4
      chunk_size: 10
    resume_state: true
    processing_task:
      task: python
      inputs:
        operation: multiply
        factor: 2
```

## Completed Changes

The following major changes have been implemented:

### 1. Type Definitions
- Added comprehensive type definitions for workflow context
- Implemented TypedDict for step metadata
- Added proper type hints throughout the codebase
- Implemented literal types for status values

### 2. Context Structure
- Implemented namespaced variable structure
- Added proper initialization of all namespaces
- Maintained backward compatibility
- Added proper error handling for undefined variables

### 3. Step Output Handling
- Implemented proper step metadata tracking
- Added support for multiple output types
- Added proper error state handling
- Implemented retry mechanism

### 4. Error Handling
- Implemented StrictUndefined for template resolution
- Added detailed error messages with available variables
- Added proper exception hierarchy
- Added comprehensive error recovery options

### 5. Template Resolution
- Standardized on Jinja2 template engine
- Removed legacy ${var} syntax
- Added proper error handling
- Added support for filters and expressions

## Migration Status

✅ Completed:
- Updated WorkflowEngine to use namespaced context
- Added backward compatibility layer
- Updated task handlers
- Added type hints and validation
- Added comprehensive test suite
- Updated core documentation

🔄 In Progress:
- Updating remaining example workflows
- Adding more test coverage
- Enhancing error reporting
- Improving performance monitoring

## Future Enhancements

1. Performance Monitoring
   - Add detailed performance metrics
   - Implement adaptive chunk sizing
   - Add resource usage monitoring
   - Optimize large dataset handling

2. Error Handling
   - Add more detailed error messages
   - Implement smart retry mechanisms
   - Add error aggregation
   - Improve recovery options

3. State Management
   - Enhance state persistence
   - Add distributed state support
   - Improve resume capabilities
   - Add state cleanup utilities 