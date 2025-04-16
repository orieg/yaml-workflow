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

## Implementation Plan

### Phase 0: Task Handler Audit
- [ ] List all template resolution points in each task handler:
  - python_task
  - shell_task
  - template_task
  - batch_task
  - file_task
  - custom_task
- [ ] Document current template resolution approach in each
- [ ] Create test cases covering current template usage

### Phase 1: Basic Variable Resolution
1. Engine Updates
   - [ ] Move simple variable resolution ({{ var }}) to engine level
   - [ ] Add tests for basic variable resolution
   - [ ] Add engine method for task handlers to use
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
   - [ ] Remove direct template resolution
   - [ ] Use engine's resolution method
   - [ ] Update tests
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
   - [ ] Remove direct template resolution
   - [ ] Use engine's resolution method
   - [ ] Update tests
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
   - [ ] Remove direct template resolution
   - [ ] Use engine's resolution method
   - [ ] Update tests
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
