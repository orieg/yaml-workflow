"""Tests for workflow visualization utilities."""

from yaml_workflow.visualize import generate_mermaid, generate_text


def _simple_workflow():
    """Two sequential steps, no conditions or error handling."""
    return {
        "name": "Simple Workflow",
        "steps": [
            {"name": "step_one", "task": "shell", "inputs": {"command": "echo hi"}},
            {"name": "step_two", "task": "echo", "inputs": {"message": "done"}},
        ],
    }


def _conditional_workflow():
    """Workflow with a conditional step that should render as a diamond."""
    return {
        "name": "Conditional Workflow",
        "steps": [
            {"name": "setup", "task": "shell", "inputs": {"command": "echo setup"}},
            {
                "name": "check_condition",
                "task": "python",
                "inputs": {"code": "pass"},
                "condition": "steps.setup.status == 'completed'",
            },
            {"name": "finalize", "task": "echo", "inputs": {"message": "done"}},
        ],
    }


def _error_handling_workflow():
    """Workflow with on_error.next referencing another step."""
    return {
        "name": "Error Handling Workflow",
        "steps": [
            {
                "name": "risky_step",
                "task": "shell",
                "inputs": {"command": "exit 1"},
                "on_error": {"action": "retry", "retry": 3, "next": "error_handler"},
            },
            {"name": "normal_step", "task": "echo", "inputs": {"message": "ok"}},
            {
                "name": "error_handler",
                "task": "echo",
                "inputs": {"message": "handling error"},
            },
        ],
    }


def _flow_workflow():
    """Workflow with flows section that reorders steps."""
    return {
        "name": "Flow Workflow",
        "steps": [
            {"name": "alpha", "task": "shell", "inputs": {"command": "echo a"}},
            {"name": "beta", "task": "echo", "inputs": {"message": "b"}},
            {"name": "gamma", "task": "template", "inputs": {"template": "c"}},
        ],
        "flows": {
            "default": "reverse_flow",
            "definitions": [
                {"main_flow": ["alpha", "beta", "gamma"]},
                {"reverse_flow": ["gamma", "alpha"]},
            ],
        },
    }


class TestSimpleWorkflow:
    def test_contains_graph_td(self):
        result = generate_mermaid(_simple_workflow())
        assert "graph TD" in result

    def test_each_step_name_appears(self):
        result = generate_mermaid(_simple_workflow())
        assert "step_one" in result
        assert "step_two" in result

    def test_sequential_edge(self):
        result = generate_mermaid(_simple_workflow())
        assert "step_one --> step_two" in result

    def test_node_labels_include_task(self):
        result = generate_mermaid(_simple_workflow())
        assert "shell" in result
        assert "echo" in result

    def test_title_comment(self):
        result = generate_mermaid(_simple_workflow())
        assert "%% Simple Workflow" in result


class TestConditionalStep:
    def test_diamond_shape_for_condition(self):
        result = generate_mermaid(_conditional_workflow())
        # Diamond nodes use curly braces: name{"label"}
        assert 'check_condition{"check_condition<br/><small>python</small>"}' in result

    def test_non_conditional_uses_square_brackets(self):
        result = generate_mermaid(_conditional_workflow())
        assert 'setup["setup<br/><small>shell</small>"]' in result
        assert 'finalize["finalize<br/><small>echo</small>"]' in result

    def test_sequential_edges_present(self):
        result = generate_mermaid(_conditional_workflow())
        assert "setup --> check_condition" in result
        assert "check_condition --> finalize" in result


class TestOnErrorNext:
    def test_dashed_error_edge(self):
        result = generate_mermaid(_error_handling_workflow())
        assert "risky_step -.->|error| error_handler" in result

    def test_sequential_edges_still_present(self):
        result = generate_mermaid(_error_handling_workflow())
        assert "risky_step --> normal_step" in result
        assert "normal_step --> error_handler" in result


class TestFlowOrdering:
    def test_explicit_flow_ordering(self):
        result = generate_mermaid(_flow_workflow(), flow="main_flow")
        lines = result.split("\n")
        edge_lines = [
            line.strip() for line in lines if "-->" in line and "-.->|" not in line
        ]
        assert "alpha --> beta" in edge_lines
        assert "beta --> gamma" in edge_lines

    def test_default_flow_used_when_no_flow_specified(self):
        """When no flow is specified, the default flow from flows section is used."""
        result = generate_mermaid(_flow_workflow())
        lines = result.split("\n")
        edge_lines = [
            line.strip() for line in lines if "-->" in line and "-.->|" not in line
        ]
        # default flow is "reverse_flow": ["gamma", "alpha"]
        assert "gamma --> alpha" in edge_lines
        # Should NOT have beta in edges since it's not in reverse_flow
        assert not any("beta" in line for line in edge_lines)

    def test_explicit_flow_changes_order(self):
        """reverse_flow should produce gamma -> alpha ordering only."""
        result = generate_mermaid(_flow_workflow(), flow="reverse_flow")
        lines = result.split("\n")
        edge_lines = [
            line.strip() for line in lines if "-->" in line and "-.->|" not in line
        ]
        assert "gamma --> alpha" in edge_lines
        assert len(edge_lines) == 1

    def test_flow_nodes_only_include_flow_steps(self):
        """Only steps in the specified flow should have node definitions."""
        result = generate_mermaid(_flow_workflow(), flow="reverse_flow")
        # beta should not have a node definition since it's not in reverse_flow
        assert "beta" not in result


class TestNestedWorkflowFormat:
    def test_workflow_key_wrapper(self):
        """Handle workflows wrapped in a top-level 'workflow' key."""
        wrapped = {"workflow": _simple_workflow()}
        result = generate_mermaid(wrapped)
        assert "graph TD" in result
        assert "step_one" in result
        assert "step_two" in result


class TestTextSimpleWorkflow:
    def test_contains_workflow_name(self):
        result = generate_text(_simple_workflow())
        assert "Simple Workflow" in result

    def test_each_step_name_appears(self):
        result = generate_text(_simple_workflow())
        assert "step_one" in result
        assert "step_two" in result

    def test_task_types_appear(self):
        result = generate_text(_simple_workflow())
        assert "shell" in result
        assert "echo" in result

    def test_box_borders(self):
        result = generate_text(_simple_workflow())
        assert "+" in result
        assert "-" in result

    def test_connectors(self):
        result = generate_text(_simple_workflow())
        assert "|" in result
        assert "v" in result

    def test_summary_line(self):
        result = generate_text(_simple_workflow())
        assert "2 steps" in result
        assert "0 conditional" in result


class TestTextConditionalStep:
    def test_conditional_marker(self):
        result = generate_text(_conditional_workflow())
        # Conditional steps have a ? marker
        assert "?" in result

    def test_summary_counts(self):
        result = generate_text(_conditional_workflow())
        assert "1 conditional" in result
        assert "2 always-run" in result


class TestTextErrorHandling:
    def test_error_edge_annotation(self):
        result = generate_text(_error_handling_workflow())
        assert "--error-->" in result
        assert "error_handler" in result

    def test_error_summary(self):
        result = generate_text(_error_handling_workflow())
        assert "1 error path(s)" in result
        assert "risky_step -> error_handler" in result


class TestTextFlowOrdering:
    def test_explicit_flow(self):
        result = generate_text(_flow_workflow(), flow="reverse_flow")
        lines = result.split("\n")
        # gamma should appear before alpha
        gamma_line = next(i for i, l in enumerate(lines) if "gamma" in l)
        alpha_line = next(i for i, l in enumerate(lines) if "alpha" in l)
        assert gamma_line < alpha_line

    def test_nested_workflow_format(self):
        wrapped = {"workflow": _simple_workflow()}
        result = generate_text(wrapped)
        assert "step_one" in result
        assert "step_two" in result
