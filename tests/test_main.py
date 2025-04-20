import runpy
from unittest.mock import MagicMock, patch

import pytest


# We need to patch the target *where it's looked up*.
# Since __main__ imports main from .cli, the lookup happens in the __main__ module's namespace.
# However, runpy executes it *as* __main__, so patching its original location might be correct.
# Let's try patching the original location first.
@patch("yaml_workflow.cli.main")
def test_main_script_calls_cli_main(mock_cli_main):
    """Test that running the main script executes cli.main."""
    # Prevent main() from actually exiting the test suite
    mock_cli_main.side_effect = lambda: None

    try:
        # Execute the __main__ module as if run via 'python -m yaml_workflow'
        runpy.run_module("yaml_workflow", run_name="__main__")
    except SystemExit:
        # Catch SystemExit if cli.main still causes one despite the mock
        pass

    # Assert that the mocked cli.main() function was called once
    mock_cli_main.assert_called_once()


# Alternative test: Check if invoking via subprocess works (more integration-like)
# import subprocess
# import sys
#
# def test_main_subprocess():
#     result = subprocess.run([sys.executable, '-m', 'yaml_workflow', '--version'], capture_output=True, text=True)
#     assert result.returncode == 0
#     assert 'yaml-workflow' in result.stdout # Check if version is printed
