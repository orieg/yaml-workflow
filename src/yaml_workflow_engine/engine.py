"""
Core workflow engine implementation
"""

import yaml
import importlib
import logging
import inspect
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    WorkflowDefinitionError,
    WorkflowValidationError,
    ModuleImportError,
    FunctionNotFoundError,
    TaskExecutionError,
    InputResolutionError,
    OutputHandlingError,
    RequiredVariableError,
    WorkflowValidationSchema
)

def _validate_workflow_definition(workflow_def: Dict[str, Any]) -> None:
    """
    Validate the workflow definition structure.
    
    Args:
        workflow_def: Workflow definition dictionary
    
    Raises:
        WorkflowValidationError: If validation fails
    """
    if not isinstance(workflow_def, dict):
        raise WorkflowValidationError("Workflow definition must be a dictionary")
    
    if 'workflow' not in workflow_def:
        raise WorkflowValidationError("Missing 'workflow' key in definition")
    
    if 'steps' not in workflow_def['workflow']:
        raise WorkflowValidationError("Missing 'steps' in workflow definition")
    
    steps = workflow_def['workflow']['steps']
    if not isinstance(steps, list):
        raise WorkflowValidationError("Workflow steps must be a list")
    
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise WorkflowValidationError(f"Step {i} must be a dictionary")
        
        # Check required fields
        for field in WorkflowValidationSchema.REQUIRED_STEP_FIELDS:
            if field not in step:
                raise WorkflowValidationError(f"Missing required field '{field}' in step {i}")

def _load_workflow(yaml_path: str) -> Dict[str, Any]:
    """
    Load and parse the workflow YAML file.
    
    Args:
        yaml_path: Path to the workflow YAML file
    
    Returns:
        Dict containing the workflow definition
    
    Raises:
        WorkflowDefinitionError: If workflow file cannot be loaded or parsed
    """
    try:
        with open(yaml_path, 'r') as f:
            workflow_def = yaml.safe_load(f)
            _validate_workflow_definition(workflow_def)
            return workflow_def
    except FileNotFoundError:
        raise WorkflowDefinitionError(f"Workflow file not found: {yaml_path}")
    except yaml.YAMLError as e:
        raise WorkflowDefinitionError(f"Invalid YAML in workflow file: {e}")
    except WorkflowValidationError as e:
        raise WorkflowDefinitionError(f"Invalid workflow structure: {e}")

def _has_default_value(func: callable, param_name: str) -> bool:
    """
    Check if a function parameter has a default value.
    
    Args:
        func: Function to inspect
        param_name: Name of the parameter to check
    
    Returns:
        bool: True if parameter has a default value, False otherwise
    """
    try:
        signature = inspect.signature(func)
        param = signature.parameters.get(param_name)
        if param is None:
            return False  # Parameter doesn't exist
        return param.default is not inspect.Parameter.empty
    except ValueError:
        return False  # Can't inspect the function

def _resolve_inputs(step_name: str, inputs: Dict[str, Any], context: Dict[str, Any], func: callable) -> Dict[str, Any]:
    """
    Resolve input values from the context or use literal values.
    
    Args:
        step_name: Name of the current step
        inputs: Dictionary of input definitions
        context: Current workflow context
        func: Function to execute (used to check parameter defaults)
    
    Returns:
        Dictionary of resolved input values
    
    Raises:
        InputResolutionError: If required inputs cannot be resolved
    """
    resolved_inputs = {}
    for k, v in inputs.items():
        try:
            if isinstance(v, str) and v.startswith('${'):
                var_name = v[2:-1]  # Remove ${}
                if var_name not in context and not _has_default_value(func, k):
                    # Only raise error if parameter has no default value
                    raise RequiredVariableError(var_name, step_name)
                context_value = context.get(var_name)
                if context_value is not None:
                    resolved_inputs[k] = context_value
                # If context_value is None and parameter has default, don't add to resolved_inputs
            else:
                resolved_inputs[k] = v
        except Exception as e:
            raise InputResolutionError(step_name, k, str(e))
    return resolved_inputs

def _load_function(module_name: str, function_name: str) -> callable:
    """
    Load a function from a module dynamically.
    
    Args:
        module_name: Name of the module to import
        function_name: Name of the function to load
    
    Returns:
        Function object
    
    Raises:
        ModuleImportError: If module cannot be imported
        FunctionNotFoundError: If function doesn't exist in module
    """
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ModuleImportError(f"Failed to import module '{module_name}': {e}")
    
    try:
        return getattr(module, function_name)
    except AttributeError:
        raise FunctionNotFoundError(f"Function '{function_name}' not found in module '{module_name}'")

def _handle_outputs(step_name: str, outputs: List[str], result: Any, context: Dict[str, Any]) -> None:
    """
    Store function outputs in the workflow context.
    
    Args:
        step_name: Name of the current step
        outputs: List of output variable names
        result: Function execution result
        context: Current workflow context to update
    
    Raises:
        OutputHandlingError: If outputs cannot be properly handled
    """
    try:
        if len(outputs) == 1:
            context[outputs[0]] = result
        elif len(outputs) > 1:
            if not isinstance(result, (list, tuple)):
                raise OutputHandlingError(step_name, "Multiple outputs defined but function return is not a list or tuple")
            if len(result) != len(outputs):
                raise OutputHandlingError(step_name, f"Expected {len(outputs)} outputs but got {len(result)}")
            for i, output_name in enumerate(outputs):
                context[output_name] = result[i]
    except Exception as e:
        raise OutputHandlingError(step_name, str(e))

def _execute_step(step: Dict[str, Any], context: Dict[str, Any]) -> None:
    """
    Execute a single workflow step.
    
    Args:
        step: Step definition from workflow
        context: Current workflow context
    
    Raises:
        TaskExecutionError: If step execution fails
    """
    step_name = step['name']
    try:
        # Load the function
        function_to_call = _load_function(step['module'], step['function'])
        
        # Resolve inputs
        inputs = step.get('inputs', {})
        resolved_inputs = _resolve_inputs(step_name, inputs, context, function_to_call)
        
        # Execute the function
        logging.info(f"Running step: {step_name} with inputs: {resolved_inputs}")
        result = function_to_call(**resolved_inputs)
        
        # Handle outputs
        outputs = step.get('outputs', [])
        _handle_outputs(step_name, outputs, result, context)
        
        logging.info(f"Step '{step_name}' completed. Outputs: {context}")
    except Exception as e:
        raise TaskExecutionError(step_name, e)

def run_workflow(yaml_path: str, runtime_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a workflow defined in a YAML file.
    
    Args:
        yaml_path: Path to the workflow YAML file
        runtime_inputs: Dictionary of runtime input values
    
    Returns:
        Final workflow context containing all outputs
    
    Raises:
        WorkflowError: If workflow execution fails
    """
    try:
        # Load and validate workflow definition
        workflow_def = _load_workflow(yaml_path)
        
        # Initialize context with runtime inputs
        context = {}
        context.update(runtime_inputs)
        
        # Execute each step
        for step in workflow_def['workflow']['steps']:
            try:
                _execute_step(step, context)
            except TaskExecutionError as e:
                # Handle step-specific error handling configuration
                error_handling = step.get('error_handling', {})
                if error_handling.get('on_failure') == 'skip':
                    logging.warning(f"Step '{step['name']}' failed but continuing due to error handling config: {e}")
                    continue
                raise
        
        logging.info("Workflow completed successfully.")
        return context
        
    except Exception as e:
        logging.error(f"Workflow failed: {e}")
        raise 