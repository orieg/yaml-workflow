import os
import pytest
from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import WorkflowError

def test_load_workflow_file_not_found():
    """Test that attempting to load a non-existent workflow file raises a WorkflowError."""
    with pytest.raises(WorkflowError, match="Workflow file not found"):
        WorkflowEngine("nonexistent.yaml")

def test_load_workflow_invalid_yaml():
    """Test that attempting to load a file with invalid YAML content raises a WorkflowError."""
    # Create a temporary file with invalid YAML content
    with open("invalid.yaml", "w") as f:
        f.write("invalid: yaml: content:\n  - missing: colon\n  bad indentation")
    
    try:
        with pytest.raises(WorkflowError, match="Invalid YAML in workflow file"):
            WorkflowEngine("invalid.yaml")
    finally:
        # Clean up the temporary file
        os.remove("invalid.yaml")

def test_load_workflow_invalid_structure():
    """Test that attempting to load a valid YAML file that lacks required workflow structure raises a WorkflowError."""
    # Create a temporary file with valid YAML but invalid workflow structure
    with open("invalid_structure.yaml", "w") as f:
        f.write("key: value\n")  # Missing required sections
    
    try:
        with pytest.raises(WorkflowError, match="Invalid workflow file: missing both 'steps' and 'flows' sections"):
            WorkflowEngine("invalid_structure.yaml")
    finally:
        # Clean up the temporary file
        os.remove("invalid_structure.yaml") 