import os

import pytest
import yaml

from yaml_workflow.engine import WorkflowEngine
from yaml_workflow.exceptions import ConfigurationError, WorkflowError


def test_load_workflow_file_not_found():
    """Test that attempting to load a non-existent workflow file raises a WorkflowError."""
    with pytest.raises(WorkflowError, match="Workflow file not found"):
        WorkflowEngine("nonexistent.yaml")


def test_load_workflow_invalid_yaml():
    """Test that attempting to load an invalid YAML file raises a WorkflowError (wrapping yaml.YAMLError)."""
    # Create a temporary file with invalid YAML content
    with open("invalid_yaml.yaml", "w") as f:
        f.write("invalid: yaml: content\n")

    try:
        # Expect WorkflowError, and check the message contains the original YAML error details
        with pytest.raises(
            WorkflowError,
            match=r"Invalid YAML in workflow file:.*mapping values are not allowed here",
        ) as e:
            WorkflowEngine("invalid_yaml.yaml")
    finally:
        # Clean up the temporary file
        os.remove("invalid_yaml.yaml")


def test_load_workflow_invalid_structure():
    """Test that attempting to load a YAML file with invalid top-level keys raises ConfigurationError."""
    # Create a temporary file with valid YAML but invalid workflow structure (unexpected top-level key)
    with open("invalid_structure.yaml", "w") as f:
        f.write("key: value\n")  # 'key' is not an allowed top-level key

    try:
        with pytest.raises(
            ConfigurationError,  # Expect ConfigurationError
            # Match the specific error message about the unexpected key
            match=r"Unexpected top-level key 'key' found.*Allowed keys are:.*",
        ):
            WorkflowEngine("invalid_structure.yaml")
    finally:
        # Clean up the temporary file
        os.remove("invalid_structure.yaml")


def test_load_workflow_missing_steps():
    """Test that attempting to load a workflow file missing both 'steps' and 'flows' raises a WorkflowError."""
    # Create a temporary file with valid YAML but missing 'steps' and 'flows' sections
    with open("missing_steps_and_flows.yaml", "w") as f:
        f.write("name: test_missing_sections\\n")  # Missing 'steps' and 'flows'

    try:
        with pytest.raises(
            WorkflowError,
            match="Invalid workflow file: missing both 'steps' and 'flows' sections",
        ) as e:
            WorkflowEngine("missing_steps_and_flows.yaml")
    finally:
        # Clean up the temporary file
        os.remove("missing_steps_and_flows.yaml")
