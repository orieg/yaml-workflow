"""
Core workflow engine implementation.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .exceptions import WorkflowError
from .workspace import create_workspace, get_workspace_info
from .tasks import get_task_handler

def setup_logging(workspace: Path, name: str) -> logging.Logger:
    """
    Set up logging configuration for the workflow.
    
    Args:
        workspace: Workspace directory
        name: Name of the workflow
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    logs_dir = workspace / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create log file path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"{name}_{timestamp}.log"
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Create and return workflow logger
    logger = logging.getLogger("workflow")
    logger.info(f"Logging to: {log_file}")
    return logger

class WorkflowEngine:
    """Main workflow engine class."""
    
    def __init__(
        self,
        workflow_file: str,
        workspace: Optional[str] = None,
        base_dir: str = "runs"
    ):
        """
        Initialize the workflow engine.
        
        Args:
            workflow_file: Path to the workflow YAML file
            workspace: Optional custom workspace directory
            base_dir: Base directory for workflow runs
        """
        self.workflow_file = Path(workflow_file)
        if not self.workflow_file.exists():
            raise WorkflowError(f"Workflow file not found: {workflow_file}")
        
        # Load workflow definition
        with open(workflow_file) as f:
            self.workflow = yaml.safe_load(f)
        
        # Validate workflow structure
        if not isinstance(self.workflow, dict):
            raise WorkflowError("Invalid workflow format: root must be a mapping")
        
        # Get workflow name
        self.name = self.workflow.get("name", self.workflow_file.stem)
        
        # Create workspace
        self.workspace = create_workspace(self.name, workspace, base_dir)
        self.workspace_info = get_workspace_info(self.workspace)
        
        # Set up logging
        self.logger = setup_logging(self.workspace, self.name)
        
        # Initialize context
        self.context = {
            "workflow_name": self.name,
            "workspace": str(self.workspace),
            "run_number": self.workspace_info.get("run_number"),
            "timestamp": datetime.now().isoformat(),
            "workflow_file": str(self.workflow_file.absolute())
        }
        
        self.logger.info(f"Initialized workflow: {self.name}")
        self.logger.info(f"Workspace: {self.workspace}")
        self.logger.info(f"Run number: {self.context['run_number']}")
    
    def run(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Run the workflow.
        
        Args:
            params: Optional parameters to pass to the workflow
        
        Returns:
            dict: Workflow results
        """
        # Update context with parameters
        if params:
            self.context.update(params)
        
        # Get steps
        steps = self.workflow.get("steps", [])
        if not isinstance(steps, list):
            raise WorkflowError("Invalid workflow format: steps must be a list")
        
        # Run steps
        results = {}
        for i, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                raise WorkflowError(f"Invalid step format at position {i}")
            
            # Get step info
            name = step.get("name", f"step_{i}")
            task_type = step.get("task")
            if not task_type:
                raise WorkflowError(f"No task type specified for step: {name}")
            
            # Get task handler
            handler = get_task_handler(task_type)
            if not handler:
                raise WorkflowError(f"Unknown task type: {task_type}")
            
            # Run task
            self.logger.info(f"Running step {i}: {name}")
            try:
                result = handler(step, self.context, self.workspace)
                results[name] = result
                # Update context with step result
                self.context[name] = result
            except Exception as e:
                raise WorkflowError(f"Error in step {name}: {str(e)}") from e
        
        self.logger.info("Workflow completed successfully.")
        self.logger.info("Final workflow outputs:")
        for key, value in results.items():
            self.logger.info(f"  {key}: {value}")
        
        return results
        
    def setup_workspace(self) -> Path:
        """
        Set up the workspace for this workflow run.
        
        Returns:
            Path: Path to the workspace directory
        """
        # Get workflow name from usage section or file name
        workflow_name = (
            self.workflow_def.get('usage', {}).get('name')
            or self.workflow_file.stem
        )
        
        # Create workspace
        self.workspace = create_workspace(
            workflow_name=workflow_name,
            custom_dir=self.workspace_dir,
            base_dir=self.base_dir
        )
        
        # Initialize workspace info in context
        workspace_info = get_workspace_info(self.workspace)
        self.context.update({
            'workspace': str(self.workspace),
            'run_number': int(self.workspace.name.split('_run_')[-1]),
            'timestamp': datetime.now().isoformat(),
            'workflow_name': workflow_name,
            'workflow_file': str(self.workflow_file.absolute()),
        })
        
        self.logger.info(f"Created workspace: {self.workspace}")
        return self.workspace
        
    def resolve_value(self, value: Any) -> Any:
        """
        Resolve a value, replacing any ${var} references with context values.
        
        Args:
            value: Value to resolve
            
        Returns:
            Any: Resolved value
        """
        if isinstance(value, str) and '${' in value:
            # Simple variable substitution
            for var_name, var_value in self.context.items():
                placeholder = '${' + var_name + '}'
                if placeholder in value:
                    value = value.replace(placeholder, str(var_value))
        return value
        
    def resolve_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve all inputs, replacing variables with their values from context.
        
        Args:
            inputs: Input dictionary
            
        Returns:
            Dict[str, Any]: Resolved inputs
        """
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, dict):
                resolved[key] = self.resolve_inputs(value)
            elif isinstance(value, list):
                resolved[key] = [self.resolve_value(v) for v in value]
            else:
                resolved[key] = self.resolve_value(value)
        return resolved
        
    def execute_step(self, step: Dict[str, Any]) -> None:
        """
        Execute a single workflow step.
        
        Args:
            step: Step definition from workflow
        """
        name = step.get('name', 'unnamed_step')
        self.logger.info(f"Running step: {name}")
        
        # Import module
        try:
            module = importlib.import_module(step['module'])
        except ImportError as e:
            raise ModuleNotFoundError(name, step['module']) from e
            
        # Get function
        try:
            func = getattr(module, step['function'])
        except AttributeError as e:
            raise FunctionNotFoundError(name, step['module'], step['function']) from e
            
        # Prepare inputs
        inputs = self.resolve_inputs(step.get('inputs', {}))
        
        # Add workspace to inputs if function accepts it
        sig = inspect.signature(func)
        if 'workspace' in sig.parameters and self.workspace:
            inputs['workspace'] = self.workspace
            
        self.logger.info(f"Step inputs: {inputs}")
        
        # Execute function
        try:
            result = func(**inputs)
        except Exception as e:
            raise StepExecutionError(name, e) from e
            
        # Store outputs in context
        outputs = step.get('outputs', [])
        if isinstance(outputs, list):
            if len(outputs) == 1:
                self.context[outputs[0]] = result
            elif len(outputs) > 1 and isinstance(result, (list, tuple)):
                for output, value in zip(outputs, result):
                    self.context[output] = value
        
        self.logger.info(f"Step '{name}' completed. Outputs: {self.context}")
        