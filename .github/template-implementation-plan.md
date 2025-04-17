# Template Engine Centralization Plan

## Goal

The primary goal of this implementation is to centralize all template processing in the workflow engine. Currently, template resolution is scattered across different task handlers, leading to inconsistent behavior and duplicate code. We will:

1. Move all template processing to the engine level
2. Ensure consistent Jinja2 feature support across all components
3. Remove duplicate template processing code from task handlers
4. Implement comprehensive testing for template features

Key Benefits:
- Consistent template behavior across all task types
- Centralized error handling and reporting
- Easier maintenance and feature additions
- Better testing coverage
- Reduced code duplication

## Recent Progress

### Resume Functionality Improvements (2024-04-16)
- [x] Fixed resume functionality in workflow engine
  - Fixed issue where workflow state wasn't properly preserved when resuming
  - Modified WorkflowState to accept pre-loaded metadata
  - Changed order of operations in CLI to load metadata before engine initialization
  - Added proper retry state handling
  - All resume functionality tests now passing

### State Management Enhancements (2024-04-16)
- [x] Improved state management and error handling
  - Added proper retry state initialization and handling
  - Enhanced error messages for state transitions
  - Added validation for execution state format
  - Improved metadata loading and saving
  - Added type definitions for execution state
  - Added proper state initialization in both new and resume scenarios

### CLI Improvements (2024-04-16)
- [x] Enhanced CLI workflow handling
  - Added better error handling for invalid metadata
  - Improved resume logic with proper state validation
  - Added checks for workflow status before resuming
  - Enhanced parameter handling during resume
  - Added better error messages for resume failures

### Template Engine Improvements (2024-04-16)
- [x] Enhanced template resolution in engine
  - Added comprehensive test suite for template resolution
  - Improved error handling for undefined variables
  - Added support for multiple variable contexts
  - Enhanced whitespace handling
  - Added tests for special characters and numeric values
  - Improved error messages with available variables context

## Implementation Plan

### Phase 0: Task Handler Audit
- [x] List all template resolution points in each task handler:
  - python_task
  - shell_task
  - template_task
  - batch_task
  - file_task
  - custom_task
- [x] Document current template resolution approach in each:

  Current Template Resolution Approaches:
  
  1. Python Task:
     - Uses Jinja2 with StrictUndefined mode
     - Resolves templates in execute_code function
     - Handles both code and input variable templating
     - Error handling with detailed variable context
  
  2. Shell Task:
     - Uses Jinja2 with StrictUndefined mode
     - Resolves templates in process_command function
     - Single-pass command string templating
     - Provides args, env, steps context
  
  3. Template Task:
     - Uses Jinja2 with StrictUndefined mode
     - Direct template rendering with full context
     - Handles file output path resolution
     - Enhanced error reporting with available variables
  
  4. Batch Task:
     - Uses Jinja2 with StrictUndefined mode
     - Resolves templates in resolve_template function
     - Adds batch-specific context (item, batch_index, batch)
     - Used for command and output path resolution
  
  5. File Task:
     - Uses Jinja2 with StrictUndefined mode
     - Recursive template processing via process_templates
     - Handles nested data structures
     - Template resolution for paths and content
  
  6. Custom Task:
     - Uses base task handler wrapper
     - Template resolution through create_task_handler
     - Processes string inputs only
     - Inherits common error handling

  Common Patterns:
  - All use Jinja2 templating engine
  - Most use StrictUndefined mode
  - Similar error handling with TemplateError
  - Common context variables (args, env, steps)
  - Varying levels of template processing depth

- [x] Create test cases covering current template usage:

  Test Coverage Plan:

  1. Python Task Tests:
     - [x] Basic variable substitution in code
     - [x] Error handling for undefined variables
     - [x] Template resolution in function inputs
     - [ ] Complex expressions in code blocks
     - [ ] Nested variable access

  2. Shell Task Tests:
     - [ ] Basic command templating
     - [ ] Environment variable substitution
     - [ ] Error handling for invalid templates
     - [ ] Complex command construction
     - [ ] Working directory path resolution

  3. Template Task Tests:
     - [x] Basic template rendering
     - [x] Loop constructs
     - [x] Conditional logic
     - [x] Error handling for undefined variables
     - [x] File path resolution

  4. Batch Task Tests:
     - [x] Item variable substitution
     - [x] Batch index templating
     - [x] Previous batch result access
     - [x] Error handling in batch context
     - [x] Parallel processing with templates

  5. File Task Tests:
     - [ ] Path template resolution
     - [ ] Content template processing
     - [ ] Recursive template handling
     - [ ] Error handling for file operations
     - [ ] Template context in file operations

  6. Custom Task Tests:
     - [ ] Input variable templating
     - [ ] Error handling for custom handlers
     - [ ] Context variable access
     - [ ] Template resolution in outputs
     - [ ] Custom template filters

  Common Test Cases:
  - [ ] Variable namespace isolation
  - [ ] Error message clarity
  - [ ] Performance with large templates
  - [ ] Memory usage in recursive processing
  - [ ] Template syntax validation

  Note: Checked items [x] indicate existing test coverage, unchecked items [ ] need to be implemented.

### Phase 1: Basic Variable Resolution
1. Engine Updates
   - [x] Move simple variable resolution ({{ var }}) to engine level
   - [x] Add tests for basic variable resolution
   - [x] Add engine method for task handlers to use
   - [x] Add comprehensive test suite for template resolution
   - [x] Add error handling for undefined variables
   - [x] Add support for multiple variable contexts
   - [x] Add tests for special characters and numeric values
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Move template resolution to engine level

     - Add basic variable resolution to engine
     - Add engine.resolve_template method
     - Add tests for basic resolution
     EOF
     
     git commit -F commit.txt
     ```

2. Task Handler Updates (one at a time)
   Python Task:
   - [x] Remove direct template resolution
   - [x] Use engine's resolution method
   - [x] Update tests
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update python_task to use engine template resolution

     - Remove direct template processing
     - Use engine.resolve_template
     - Add tests verifying resolution
     EOF
     
     git commit -F commit.txt
     ```
   
   Shell Task:
   - [ ] Remove direct template resolution
   - [ ] Use engine's resolution method
   - [ ] Update tests
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update shell_task to use engine template resolution

     - Remove direct template processing
     - Use engine.resolve_template
     - Add tests verifying resolution
     - Verify existing shell_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   Template Task:
   - [x] Remove direct template resolution
   - [x] Use engine's resolution method
   - [x] Update tests
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update template_task to use engine template resolution

     - Remove direct template processing
     - Use engine.resolve_template
     - Add tests verifying resolution
     - Verify existing template_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   Batch Task:
   - [-] Remove direct template resolution (partially complete)
   - [-] Use engine's resolution method (partially complete)
   - [x] Update tests
   - [ ] TODO: Remove batch_processor.resolve_template and use engine.resolve_template
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update batch_task to use engine template resolution

     - Remove direct template processing
     - Use engine.resolve_template
     - Add tests verifying resolution
     - Verify existing batch_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   File Task:
   - [ ] Remove direct template resolution
   - [ ] Use engine's resolution method
   - [ ] Update tests
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update file_task to use engine template resolution

     - Remove direct template processing
     - Use engine.resolve_template
     - Add tests verifying resolution
     - Verify existing file_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   Custom Task:
   - [ ] Remove direct template resolution
   - [ ] Use engine's resolution method
   - [ ] Update tests
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update custom_task to use engine template resolution

     - Remove direct template processing
     - Use engine.resolve_template
     - Add tests verifying resolution
     - Verify existing custom_task workflows
     EOF
     
     git commit -F commit.txt
     ```

### Phase 2: Basic Control Structures
1. Engine Updates
   - [ ] Add support for if statements in engine
   - [ ] Add tests for if statement resolution
   - [ ] Add engine method for condition evaluation
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Add if statement support to engine

     - Add condition evaluation to engine
     - Add engine.evaluate_condition method
     - Add tests for if statements
     - Support full Jinja2 if syntax
     EOF
     
     git commit -F commit.txt
     ```

2. Task Handler Updates (one at a time)
   Python Task:
   - [ ] Remove condition evaluation code
   - [ ] Use engine's condition evaluation
   - [ ] Update tests with if statements
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update python_task to use engine condition evaluation

     - Remove task-specific condition handling
     - Use engine.evaluate_condition
     - Add tests for if statements
     - Verify conditional python_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   Shell Task:
   - [ ] Remove condition evaluation code
   - [ ] Use engine's condition evaluation
   - [ ] Update tests with if statements
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update shell_task to use engine condition evaluation

     - Remove task-specific condition handling
     - Use engine.evaluate_condition
     - Add tests for if statements
     - Verify conditional shell_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   Template Task:
   - [ ] Remove condition evaluation code
   - [ ] Use engine's condition evaluation
   - [ ] Update tests with if statements
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update template_task to use engine condition evaluation

     - Remove task-specific condition handling
     - Use engine.evaluate_condition
     - Add tests for if statements
     - Verify conditional template_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   Batch Task:
   - [ ] Remove condition evaluation code
   - [ ] Use engine's condition evaluation
   - [ ] Update tests with if statements
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update batch_task to use engine condition evaluation

     - Remove task-specific condition handling
     - Use engine.evaluate_condition
     - Add tests for if statements
     - Verify conditional batch_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   File Task:
   - [ ] Remove condition evaluation code
   - [ ] Use engine's condition evaluation
   - [ ] Update tests with if statements
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update file_task to use engine condition evaluation

     - Remove task-specific condition handling
     - Use engine.evaluate_condition
     - Add tests for if statements
     - Verify conditional file_task workflows
     EOF
     
     git commit -F commit.txt
     ```
   
   Custom Task:
   - [ ] Remove condition evaluation code
   - [ ] Use engine's condition evaluation
   - [ ] Update tests with if statements
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update custom_task to use engine condition evaluation

     - Remove task-specific condition handling
     - Use engine.evaluate_condition
     - Add tests for if statements
     - Verify conditional custom_task workflows
     EOF
     
     git commit -F commit.txt
     ```

### Phase 3: Loop Support
1. Engine Updates
   - [ ] Add for loop support in engine
   - [ ] Add tests for loop resolution
   - [ ] Add engine method for loop handling

2. Task Handler Updates (one at a time)
   Python Task:
   - [ ] Remove loop handling code
   - [ ] Use engine's loop handling
   - [ ] Update tests with loops
   
   Shell Task:
   - [ ] Remove loop handling code
   - [ ] Use engine's loop handling
   - [ ] Update tests with loops
   
   Template Task:
   - [ ] Remove loop handling code
   - [ ] Use engine's loop handling
   - [ ] Update tests with loops
   
   Batch Task:
   - [ ] Remove loop handling code
   - [ ] Use engine's loop handling
   - [ ] Update tests with loops
   
   File Task:
   - [ ] Remove loop handling code
   - [ ] Use engine's loop handling
   - [ ] Update tests with loops
   
   Custom Task:
   - [ ] Remove loop handling code
   - [ ] Use engine's loop handling
   - [ ] Update tests with loops

### Phase 4: Variable Assignment
1. Engine Updates
   - [ ] Add support for set statements
   - [ ] Add tests for variable assignment
   - [ ] Add engine method for variable assignment

2. Task Handler Updates (one at a time)
   Python Task:
   - [ ] Remove variable assignment code
   - [ ] Use engine's variable assignment
   - [ ] Update tests with set statements
   
   Shell Task:
   - [ ] Remove variable assignment code
   - [ ] Use engine's variable assignment
   - [ ] Update tests with set statements
   
   Template Task:
   - [ ] Remove variable assignment code
   - [ ] Use engine's variable assignment
   - [ ] Update tests with set statements
   
   Batch Task:
   - [ ] Remove variable assignment code
   - [ ] Use engine's variable assignment
   - [ ] Update tests with set statements
   
   File Task:
   - [ ] Remove variable assignment code
   - [ ] Use engine's variable assignment
   - [ ] Update tests with set statements
   
   Custom Task:
   - [ ] Remove variable assignment code
   - [ ] Use engine's variable assignment
   - [ ] Update tests with set statements

### Phase 5: Filters and Expressions
1. Engine Updates
   - [ ] Add support for basic filters (upper, lower, etc)
   - [ ] Add tests for filter resolution
   - [ ] Add support for basic expressions (math, concatenation)
   - [ ] Add tests for expression resolution

2. Task Handler Updates (one at a time)
   Python Task:
   - [ ] Remove filter/expression handling code
   - [ ] Use engine's filter/expression handling
   - [ ] Update tests with filters and expressions
   
   Shell Task:
   - [ ] Remove filter/expression handling code
   - [ ] Use engine's filter/expression handling
   - [ ] Update tests with filters and expressions
   
   Template Task:
   - [ ] Remove filter/expression handling code
   - [ ] Use engine's filter/expression handling
   - [ ] Update tests with filters and expressions
   
   Batch Task:
   - [ ] Remove filter/expression handling code
   - [ ] Use engine's filter/expression handling
   - [ ] Update tests with filters and expressions
   
   File Task:
   - [ ] Remove filter/expression handling code
   - [ ] Use engine's filter/expression handling
   - [ ] Update tests with filters and expressions
   
   Custom Task:
   - [ ] Remove filter/expression handling code
   - [ ] Use engine's filter/expression handling
   - [ ] Update tests with filters and expressions

### Phase 6: Error Handling
1. Engine Updates
   - [ ] Improve error messages for undefined variables
   - [ ] Add tests for error scenarios
   - [ ] Add error handling for nested variable access

2. Task Handler Updates (one at a time)
   Python Task:
   - [ ] Remove task-specific error handling
   - [ ] Use engine's error handling
   - [ ] Update tests with error scenarios
   
   Shell Task:
   - [ ] Remove task-specific error handling
   - [ ] Use engine's error handling
   - [ ] Update tests with error scenarios
   
   Template Task:
   - [ ] Remove task-specific error handling
   - [ ] Use engine's error handling
   - [ ] Update tests with error scenarios
   
   Batch Task:
   - [ ] Remove task-specific error handling
   - [ ] Use engine's error handling
   - [ ] Update tests with error scenarios
   
   File Task:
   - [ ] Remove task-specific error handling
   - [ ] Use engine's error handling
   - [ ] Update tests with error scenarios
   
   Custom Task:
   - [ ] Remove task-specific error handling
   - [ ] Use engine's error handling
   - [ ] Update tests with error scenarios

### Phase 7: Advanced Features
1. Engine Updates
   - [ ] Add support for macros
   - [ ] Add support for includes
   - [ ] Add support for custom filters
   - [ ] Add comprehensive tests for advanced features

2. Task Handler Updates (one at a time)
   Python Task:
   - [ ] Remove any custom template features
   - [ ] Use engine's advanced features
   - [ ] Update tests with macros and includes
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update python_task to use engine advanced features

     - Remove custom template features
     - Use engine's advanced features
     - Add tests for macros and includes
     EOF
     
     git commit -F commit.txt
     ```

   Shell Task:
   - [ ] Remove any custom template features
   - [ ] Use engine's advanced features
   - [ ] Update tests with macros and includes
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update shell_task to use engine advanced features

     - Remove custom template features
     - Use engine's advanced features
     - Add tests for macros and includes
     EOF
     
     git commit -F commit.txt
     ```

   Template Task:
   - [ ] Remove any custom template features
   - [ ] Use engine's advanced features
   - [ ] Update tests with macros and includes
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update template_task to use engine advanced features

     - Remove custom template features
     - Use engine's advanced features
     - Add tests for macros and includes
     EOF
     
     git commit -F commit.txt
     ```

   Batch Task:
   - [ ] Remove any custom template features
   - [ ] Use engine's advanced features
   - [ ] Update tests with macros and includes
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update batch_task to use engine advanced features

     - Remove custom template features
     - Use engine's advanced features
     - Add tests for macros and includes
     EOF
     
     git commit -F commit.txt
     ```

   File Task:
   - [ ] Remove any custom template features
   - [ ] Use engine's advanced features
   - [ ] Update tests with macros and includes
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update file_task to use engine advanced features

     - Remove custom template features
     - Use engine's advanced features
     - Add tests for macros and includes
     EOF
     
     git commit -F commit.txt
     ```

   Custom Task:
   - [ ] Remove any custom template features
   - [ ] Use engine's advanced features
   - [ ] Update tests with macros and includes
   - [ ] After tests pass:
     ```bash
     cat > commit.txt << 'EOF'
     Update custom_task to use engine advanced features

     - Remove custom template features
     - Use engine's advanced features
     - Add tests for macros and includes
     EOF
     
     git commit -F commit.txt
     ```

### Phase 2: Enhanced Batch Processing
See detailed implementation in `.github/intermediate-implementation-plan.md`

1. Batch Task Improvements
   - [x] Standardize task interface with template engine integration
   - [x] Implement consistent error handling for template resolution
   - [x] Simplify state management with template context preservation
   - [ ] After implementation:
     ```bash
     cat > commit.txt << 'EOF'
     Enhance batch processing with template integration

     - Standardize task interface with template engine
     - Add consistent error handling for templates
     - Simplify state management
     - Add comprehensive test coverage
     EOF
     
     git commit -F commit.txt
     ```

2. Template Resolution Integration
   - [ ] Update batch context to include template engine
   - [ ] Implement template-specific error handling
   - [ ] Add template state tracking
   - [ ] After implementation:
     ```bash
     cat > commit.txt << 'EOF'
     Integrate template resolution in batch processing

     - Add template engine to batch context
     - Implement template error handling
     - Add template state tracking
     - Update tests for template scenarios
     EOF
     
     git commit -F commit.txt
     ```

3. Testing Updates
   - [ ] Add template resolution test cases:
     - Variable substitution in batch items
     - Error handling for undefined variables
     - State preservation during resume
     - Complex template expressions
     - Nested variable access
   - [ ] After implementation:
     ```bash
     cat > commit.txt << 'EOF'
     Add comprehensive template tests for batch processing

     - Add variable substitution tests
     - Add error handling tests
     - Add state preservation tests
     - Add complex expression tests
     EOF
     
     git commit -F commit.txt
     ```

4. Documentation
   - [ ] Update batch processing documentation with template examples
   - [ ] Add troubleshooting guide for template issues
   - [ ] Provide migration guide for template changes
   - [ ] After completion:
     ```bash
     cat > commit.txt << 'EOF'
     Update documentation for batch template processing

     - Add template usage examples
     - Add troubleshooting guide
     - Add migration guide
     - Update API documentation
     EOF
     
     git commit -F commit.txt
     ```

### Phase 3: Namespace-Aware Template Resolution

1. Enhanced Template Engine
   ```python
   class TemplateEngine:
       """Process Jinja2 templates with namespace support."""
       
       def __init__(self, cache_size: int = 128):
           self.env = Environment(undefined=StrictUndefined)
           self._compile_template = lru_cache(maxsize=cache_size)(self._compile_template_uncached)
           
       def process_template(self, template_str: str, context: Dict[str, Any]) -> str:
           """Process template with namespace support."""
           try:
               template = self._compile_template(template_str)
               return template.render(**self._prepare_context(context))
           except UndefinedError as e:
               namespace = self._get_undefined_namespace(str(e))
               available = self._get_namespace_variables(context, namespace)
               raise TemplateError(f"Variable not found in namespace '{namespace}'. Available: {available}")
               
       def _prepare_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
           """Prepare context with namespace support."""
           return {
               "args": context.get("args", {}),
               "env": context.get("env", {}),
               "steps": context.get("steps", {}),
               **{k: v for k, v in context.items() if k not in ["args", "env", "steps"]}
           }
   ```

2. Task Handler Updates
   - [ ] Update all task handlers to use namespace-aware template resolution
   - [ ] Add namespace validation in task handlers
   - [ ] Update error messages with namespace context
   - [ ] After implementation:
     ```bash
     cat > commit.txt << 'EOF'
     Update task handlers with namespace support

     - Add namespace-aware template resolution
     - Add namespace validation
     - Update error messages
     - Add namespace tests
     EOF
     
     git commit -F commit.txt
     ```

3. Testing Updates
   - [ ] Add namespace-specific test cases:
     - Variable isolation between namespaces
     - Cross-namespace access patterns
     - Namespace error handling
     - Template resolution in each namespace
   - [ ] After implementation:
     ```bash
     cat > commit.txt << 'EOF'
     Add namespace-aware template tests

     - Add namespace isolation tests
     - Add cross-namespace access tests
     - Add namespace error tests
     - Update template resolution tests
     EOF
     
     git commit -F commit.txt
     ```

4. Documentation
   - [ ] Document namespace best practices
   - [ ] Update template resolution guide
   - [ ] Add namespace troubleshooting guide
   - [ ] After completion:
     ```bash
     cat > commit.txt << 'EOF'
     Update documentation with namespace guidelines

     - Add namespace best practices
     - Update template guide
     - Add troubleshooting section
     - Add migration guide
     EOF
     
     git commit -F commit.txt
     ```
