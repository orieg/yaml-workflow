"""Tests for workflow visualization utilities."""

from yaml_workflow.visualize import (
    _get_ordered_step_names,
    _group_into_segments,
    _render_diamond,
    generate_mermaid,
    generate_text,
)


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
        # Uses unicode box-drawing characters
        assert "\u250c" in result  # top-left corner
        assert "\u2518" in result  # bottom-right corner

    def test_connectors(self):
        result = generate_text(_simple_workflow())
        assert "\u2502" in result  # vertical line
        assert "\u25bc" in result  # down arrow

    def test_summary_line(self):
        result = generate_text(_simple_workflow())
        assert "2 steps" in result
        assert "0 conditional" in result


class TestTextConditionalStep:
    def test_conditional_rendered_as_branch(self):
        result = generate_text(_conditional_workflow())
        # Conditional steps are rendered in branch groups with fan-out/fan-in
        assert "\u252c" in result or "\u2534" in result  # ┬ or ┴ (fan lines)
        assert "check_condition" in result

    def test_summary_counts(self):
        result = generate_text(_conditional_workflow())
        assert "1 conditional" in result
        assert "2 always-run" in result


class TestTextErrorHandling:
    def test_error_edge_annotation(self):
        result = generate_text(_error_handling_workflow())
        assert "error" in result
        assert "error_handler" in result

    def test_error_summary(self):
        result = generate_text(_error_handling_workflow())
        assert "1 error path(s)" in result
        assert "risky_step \u2192 error_handler" in result


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


# --- Mermaid edge case tests ---


class TestMermaidEdgeCases:
    def test_flow_with_step_not_in_step_map(self):
        """Test mermaid generation when flow references a step not in step_map (line 37)."""
        workflow = {
            "name": "Missing Step Workflow",
            "steps": [
                {"name": "real_step", "task": "shell", "inputs": {"command": "echo"}},
            ],
            "flows": {
                "definitions": [
                    {"custom": ["real_step", "ghost_step"]},
                ],
            },
        }
        result = generate_mermaid(workflow, flow="custom")
        # ghost_step should be silently skipped (continue on line 37)
        assert "real_step" in result
        assert "ghost_step" not in result

    def test_sequential_edge_skips_missing_step(self):
        """Test that sequential edges skip steps not in step_map (line 50)."""
        workflow = {
            "name": "Edge Skip Workflow",
            "steps": [
                {"name": "a", "task": "shell", "inputs": {"command": "echo"}},
                {"name": "c", "task": "echo", "inputs": {"message": "end"}},
            ],
            "flows": {
                "definitions": [
                    {"custom": ["a", "missing_b", "c"]},
                ],
            },
        }
        result = generate_mermaid(workflow, flow="custom")
        # Edge from a to missing_b and missing_b to c should not appear
        assert "a --> missing_b" not in result
        assert "missing_b --> c" not in result

    def test_error_edge_step_not_in_step_map(self):
        """Test error edge when step_name is not in step_map (line 57)."""
        workflow = {
            "name": "Error Edge Missing",
            "steps": [
                {"name": "a", "task": "shell", "inputs": {"command": "echo"}},
            ],
            "flows": {
                "definitions": [
                    {"custom": ["a", "nonexistent"]},
                ],
            },
        }
        result = generate_mermaid(workflow, flow="custom")
        # nonexistent step should be skipped in error edge processing
        assert "nonexistent" not in result

    def test_error_edge_target_not_in_step_map(self):
        """Test error edge when on_error.next references a step not in step_map (line 61)."""
        workflow = {
            "name": "Error Target Missing",
            "steps": [
                {
                    "name": "risky",
                    "task": "shell",
                    "inputs": {"command": "exit 1"},
                    "on_error": {"next": "nonexistent_handler"},
                },
            ],
        }
        result = generate_mermaid(workflow)
        # Error edge should not be generated since target is not in step_map
        assert "-.->|error|" not in result

    def test_on_error_not_dict(self):
        """Test that on_error as a non-dict value is ignored."""
        workflow = {
            "name": "Non-dict Error",
            "steps": [
                {
                    "name": "step1",
                    "task": "shell",
                    "inputs": {"command": "echo"},
                    "on_error": "skip",
                },
            ],
        }
        result = generate_mermaid(workflow)
        assert "-.->|error|" not in result


# --- Text visualization edge case tests ---


class TestTextEdgeCases:
    def test_single_conditional_step(self):
        """Test text rendering of a single conditional step (rendered as branch, line 177)."""
        workflow = {
            "name": "Single Cond",
            "steps": [
                {"name": "setup", "task": "shell", "inputs": {"command": "echo"}},
                {
                    "name": "check",
                    "task": "python",
                    "inputs": {"code": "pass"},
                    "condition": "true",
                },
                {"name": "end", "task": "echo", "inputs": {"message": "done"}},
            ],
        }
        result = generate_text(workflow)
        assert "check" in result
        assert "1 conditional" in result

    def test_flow_with_step_not_in_step_map_text(self):
        """Test text generation when flow references a step not in step_map (line 93, 121)."""
        workflow = {
            "name": "Missing Step Text",
            "steps": [
                {"name": "real", "task": "shell", "inputs": {"command": "echo"}},
            ],
            "flows": {
                "definitions": [
                    {"custom": ["real", "ghost"]},
                ],
            },
        }
        result = generate_text(workflow, flow="custom")
        assert "real" in result
        # ghost should not cause an error

    def test_text_with_flow_display(self):
        """Test text rendering shows flow name when specified."""
        result = generate_text(_flow_workflow(), flow="main_flow")
        assert "Flow: main_flow" in result

    def test_text_multiple_conditional_steps(self):
        """Test text rendering with multiple adjacent conditional steps (branch group)."""
        workflow = {
            "name": "Multi Branch",
            "steps": [
                {"name": "init", "task": "shell", "inputs": {"command": "echo"}},
                {
                    "name": "cond_a",
                    "task": "python",
                    "inputs": {"code": "pass"},
                    "condition": "true",
                },
                {
                    "name": "cond_b",
                    "task": "python",
                    "inputs": {"code": "pass"},
                    "condition": "true",
                },
                {
                    "name": "cond_c",
                    "task": "python",
                    "inputs": {"code": "pass"},
                    "condition": "true",
                },
                {"name": "finish", "task": "echo", "inputs": {"message": "done"}},
            ],
        }
        result = generate_text(workflow)
        assert "cond_a" in result
        assert "cond_b" in result
        assert "cond_c" in result
        assert "3 conditional" in result
        # Branch rendering uses fan-out/fan-in
        assert "\u252c" in result  # fan-out
        assert "\u2534" in result  # fan-in

    def test_text_error_on_non_conditional_step(self):
        """Test text rendering shows error annotations on box steps."""
        workflow = {
            "name": "Error Box",
            "steps": [
                {
                    "name": "risky",
                    "task": "shell",
                    "inputs": {"command": "exit 1"},
                    "on_error": {"next": "handler"},
                },
                {"name": "handler", "task": "echo", "inputs": {"message": "fixed"}},
            ],
        }
        result = generate_text(workflow)
        assert "error" in result
        assert "handler" in result


# --- _render_diamond tests ---


class TestRenderDiamond:
    def test_basic_diamond_rendering(self):
        """Test _render_diamond produces expected diamond shape (lines 306-321)."""
        lines = []
        _render_diamond(lines, "my_step", "python", 12, [])
        output = "\n".join(lines)
        assert "my_step" in output
        assert "python" in output
        assert "\u25c7" in output  # diamond marker
        assert "\u2571" in output  # forward slash
        assert "\u2572" in output  # backslash
        assert "\u25c1" in output  # left arrow
        assert "\u25b7" in output  # right arrow

    def test_diamond_with_error_targets(self):
        """Test _render_diamond with error targets annotation."""
        lines = []
        _render_diamond(lines, "check", "shell", 10, ["fallback"])
        output = "\n".join(lines)
        assert "check" in output
        assert "error" in output
        assert "fallback" in output

    def test_diamond_no_error_targets(self):
        """Test _render_diamond without error targets."""
        lines = []
        _render_diamond(lines, "test_step", "echo", 14, [])
        output = "\n".join(lines)
        assert "test_step" in output
        assert "error" not in output


# --- _get_ordered_step_names tests ---


class TestGetOrderedStepNames:
    def test_flow_not_found_falls_back_to_step_order(self):
        """Test that specifying a non-existent flow falls back to step order (line 339->352)."""
        workflow = {
            "name": "Fallback",
            "steps": [
                {"name": "a", "task": "shell"},
                {"name": "b", "task": "echo"},
            ],
            "flows": {
                "definitions": [
                    {"existing_flow": ["b", "a"]},
                ],
            },
        }
        steps = workflow["steps"]
        result = _get_ordered_step_names(workflow, steps, flow="nonexistent_flow")
        # Should fall back to step definition order
        assert result == ["a", "b"]

    def test_default_flow_not_found_falls_back(self):
        """Test that a default flow name not matching any definition falls back (line 345->352, 347->352)."""
        workflow = {
            "name": "Bad Default",
            "steps": [
                {"name": "x", "task": "shell"},
                {"name": "y", "task": "echo"},
            ],
            "flows": {
                "default": "missing_default",
                "definitions": [
                    {"other_flow": ["y", "x"]},
                ],
            },
        }
        steps = workflow["steps"]
        result = _get_ordered_step_names(workflow, steps, flow=None)
        # default flow "missing_default" not found, should fall back to step order
        assert result == ["x", "y"]

    def test_no_flows_section(self):
        """Test step ordering when no flows section exists."""
        workflow = {
            "name": "No Flows",
            "steps": [
                {"name": "first", "task": "shell"},
                {"name": "second", "task": "echo"},
            ],
        }
        steps = workflow["steps"]
        result = _get_ordered_step_names(workflow, steps, flow=None)
        assert result == ["first", "second"]

    def test_flow_specified_but_no_flows_section(self):
        """Test specifying a flow when no flows section exists (line 339->352)."""
        workflow = {
            "name": "No Flows Section",
            "steps": [
                {"name": "a", "task": "shell"},
                {"name": "b", "task": "echo"},
            ],
        }
        steps = workflow["steps"]
        result = _get_ordered_step_names(workflow, steps, flow="some_flow")
        # No flows section at all, should fall back
        assert result == ["a", "b"]

    def test_empty_definitions_list(self):
        """Test with empty definitions list."""
        workflow = {
            "name": "Empty Defs",
            "steps": [
                {"name": "a", "task": "shell"},
            ],
            "flows": {
                "definitions": [],
            },
        }
        steps = workflow["steps"]
        result = _get_ordered_step_names(workflow, steps, flow="any")
        assert result == ["a"]

    def test_definitions_with_non_dict_entries(self):
        """Test definitions containing non-dict entries are skipped."""
        workflow = {
            "name": "Mixed Defs",
            "steps": [
                {"name": "a", "task": "shell"},
                {"name": "b", "task": "echo"},
            ],
            "flows": {
                "definitions": [
                    "not_a_dict",
                    {"real_flow": ["b", "a"]},
                ],
            },
        }
        steps = workflow["steps"]
        result = _get_ordered_step_names(workflow, steps, flow="real_flow")
        assert result == ["b", "a"]


# --- _group_into_segments tests ---


class TestGroupIntoSegments:
    def test_all_regular_steps(self):
        """Test grouping when all steps are regular (no conditions)."""
        step_map = {
            "a": {"name": "a", "task": "shell"},
            "b": {"name": "b", "task": "echo"},
        }
        result = _group_into_segments(["a", "b"], step_map)
        assert len(result) == 2
        assert result[0] == {"type": "step", "name": "a"}
        assert result[1] == {"type": "step", "name": "b"}

    def test_single_conditional(self):
        """Test grouping with a single conditional step (line 177)."""
        step_map = {
            "a": {"name": "a", "task": "shell"},
            "cond": {"name": "cond", "task": "python", "condition": "true"},
            "b": {"name": "b", "task": "echo"},
        }
        result = _group_into_segments(["a", "cond", "b"], step_map)
        assert len(result) == 3
        assert result[0] == {"type": "step", "name": "a"}
        assert result[1] == {"type": "branch", "steps": ["cond"]}
        assert result[2] == {"type": "step", "name": "b"}

    def test_multiple_adjacent_conditionals(self):
        """Test grouping adjacent conditionals into a single branch segment."""
        step_map = {
            "a": {"name": "a", "task": "shell"},
            "c1": {"name": "c1", "task": "python", "condition": "true"},
            "c2": {"name": "c2", "task": "python", "condition": "true"},
            "b": {"name": "b", "task": "echo"},
        }
        result = _group_into_segments(["a", "c1", "c2", "b"], step_map)
        assert len(result) == 3
        assert result[0] == {"type": "step", "name": "a"}
        assert result[1] == {"type": "branch", "steps": ["c1", "c2"]}
        assert result[2] == {"type": "step", "name": "b"}

    def test_step_not_in_step_map(self):
        """Test grouping when a step is not in step_map."""
        step_map = {"a": {"name": "a", "task": "shell"}}
        result = _group_into_segments(["a", "missing"], step_map)
        assert len(result) == 2
        assert result[0] == {"type": "step", "name": "a"}
        # missing has no "condition" in step_map.get("missing", {}), so it's a step
        assert result[1] == {"type": "step", "name": "missing"}
