"""
Workflow validator — deep static analysis of workflow YAML files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# ---------------------------------------------------------------------------
# Known built-in task types
# ---------------------------------------------------------------------------
BUILTIN_TASKS = {
    "shell",
    "python_code",
    "python_function",
    "python_script",
    "python_module",
    "template",
    "http.request",
    "file.write",
    "file.read",
    "file.append",
    "file.copy",
    "file.move",
    "file.delete",
    "file.read_json",
    "file.write_json",
    "file.read_yaml",
    "file.write_yaml",
    "batch",
    "noop",
    "notify",
    # Legacy / alias names registered in tasks/__init__.py
    "write_file",
    "read_file",
    "append_file",
    "write_json",
    "read_json",
    "write_yaml",
    "read_yaml",
    "http_request",
    "render_template",
    "print_vars",
    "list_files",
    "hello_world",
    "echo",
    "add_numbers",
    "join_strings",
    "create_greeting",
    "fail",
}

ALLOWED_TOP_LEVEL_KEYS = {
    "name",
    "description",
    "params",
    "steps",
    "flows",
    "settings",
    "imports",
}

# Pattern that indicates a likely double-result bug:  steps.X.result.result.Y
_DOUBLE_RESULT_RE = re.compile(r"steps\.[^.]+\.result\.result")

# Pattern to find  args.something  references inside Jinja2 templates
_ARGS_REF_RE = re.compile(r"\bargs\.(\w+)\b")

# Pattern to find  steps.something  references inside Jinja2 templates
_STEPS_REF_RE = re.compile(r"\bsteps\.(\w+)\b")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    level: str  # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    step: Optional[str] = None
    hint: Optional[str] = None


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [
                {
                    "level": i.level,
                    "message": i.message,
                    "line": i.line,
                    "step": i.step,
                    "hint": i.hint,
                }
                for i in self.issues
            ],
        }


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class WorkflowValidator:
    """Static validator for yaml-workflow YAML files."""

    def __init__(self, workflow_path: str | Path):
        self.workflow_path = Path(workflow_path)
        self._raw_text: str = ""
        self._workflow: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def validate(self) -> ValidationResult:
        """Run all checks and return a ValidationResult."""
        result = ValidationResult()

        syntax_issues = self._check_yaml_syntax()
        result.issues.extend(syntax_issues)

        # If YAML cannot be parsed, structural checks are meaningless.
        if any(i.level == "error" for i in syntax_issues):
            return result

        result.issues.extend(self._check_structure())
        result.issues.extend(self._check_step_names_unique())
        result.issues.extend(self._check_task_types())
        result.issues.extend(self._check_flow_references())
        result.issues.extend(self._check_param_references())
        result.issues.extend(self._check_step_result_access())

        return result

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_yaml_syntax(self) -> List[ValidationIssue]:
        """Verify the file exists and is valid YAML."""
        issues: List[ValidationIssue] = []

        if not self.workflow_path.exists():
            issues.append(
                ValidationIssue(
                    level="error",
                    message=f"File not found: {self.workflow_path}",
                )
            )
            return issues

        try:
            self._raw_text = self.workflow_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(
                ValidationIssue(
                    level="error",
                    message=f"Cannot read file: {exc}",
                )
            )
            return issues

        try:
            self._workflow = yaml.safe_load(self._raw_text)
        except yaml.YAMLError as exc:
            line = None
            if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
                line = exc.problem_mark.line + 1
            issues.append(
                ValidationIssue(
                    level="error",
                    message=f"YAML syntax error: {exc}",
                    line=line,
                    hint="Fix the YAML syntax error above before re-validating.",
                )
            )

        return issues

    def _check_structure(self) -> List[ValidationIssue]:
        """Check high-level structure: root type, required sections, allowed keys."""
        issues: List[ValidationIssue] = []
        wf = self._workflow

        if not isinstance(wf, dict):
            issues.append(
                ValidationIssue(
                    level="error",
                    message="Workflow root must be a YAML mapping (dict), not a list or scalar.",
                    hint="Ensure the top-level of your workflow file is a YAML object.",
                )
            )
            return issues

        # At least one of steps / flows must be present
        if "steps" not in wf and "flows" not in wf:
            issues.append(
                ValidationIssue(
                    level="error",
                    message="Workflow must contain at least a 'steps' or 'flows' section.",
                    hint="Add a 'steps:' list with at least one step definition.",
                )
            )

        # Unknown top-level keys
        for key in wf:
            if key not in ALLOWED_TOP_LEVEL_KEYS:
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Unknown top-level key '{key}'.",
                        hint=(
                            f"Allowed top-level keys are: {', '.join(sorted(ALLOWED_TOP_LEVEL_KEYS))}. "
                            "Use the 'params' section for workflow inputs."
                        ),
                    )
                )

        # Steps must be a list (if present)
        if "steps" in wf and not isinstance(wf["steps"], (list, dict)):
            issues.append(
                ValidationIssue(
                    level="error",
                    message="'steps' must be a list or mapping.",
                )
            )

        # Each step must have 'name' and 'task'
        steps = self._get_steps_list()
        for idx, step in enumerate(steps):
            if not isinstance(step, dict):
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Step at index {idx} is not a mapping.",
                    )
                )
                continue
            step_label = step.get("name") or f"<step {idx}>"
            if "name" not in step:
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Step at index {idx} is missing required field 'name'.",
                        hint="Every step must have a 'name' field.",
                    )
                )
            if "task" not in step:
                line = self._find_step_line(step_label)
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Step '{step_label}': missing required field 'task'.",
                        line=line,
                        step=step_label,
                        hint="Every step must have a 'task' field specifying the task type.",
                    )
                )

        return issues

    def _check_step_names_unique(self) -> List[ValidationIssue]:
        """Ensure step names are unique within the workflow."""
        issues: List[ValidationIssue] = []
        seen: Dict[str, int] = {}
        for idx, step in enumerate(self._get_steps_list()):
            if not isinstance(step, dict):
                continue
            name = step.get("name")
            if name is None:
                continue
            if name in seen:
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=(
                            f"Duplicate step name '{name}' (first at index {seen[name]}, "
                            f"repeated at index {idx})."
                        ),
                        step=name,
                        hint="Step names must be unique across the workflow.",
                    )
                )
            else:
                seen[name] = idx
        return issues

    def _check_task_types(self) -> List[ValidationIssue]:
        """Warn on unknown task types (may be plugins, so never an error)."""
        issues: List[ValidationIssue] = []
        for step in self._get_steps_list():
            if not isinstance(step, dict):
                continue
            task = step.get("task")
            step_name = step.get("name", "<unnamed>")
            if task and task not in BUILTIN_TASKS:
                issues.append(
                    ValidationIssue(
                        level="warning",
                        message=(
                            f"Step '{step_name}': unknown task type '{task}' "
                            "(may be a plugin)."
                        ),
                        step=step_name,
                        hint=(
                            "If this is a plugin task, make sure it is installed. "
                            "Built-in tasks are: "
                            + ", ".join(sorted(BUILTIN_TASKS))
                            + "."
                        ),
                    )
                )
        return issues

    def _check_flow_references(self) -> List[ValidationIssue]:
        """Ensure every step name referenced in flows actually exists in steps."""
        issues: List[ValidationIssue] = []
        wf = self._workflow
        if not isinstance(wf, dict):
            return issues

        flows = wf.get("flows")
        if not flows or not isinstance(flows, dict):
            return issues

        defined_step_names = {
            s.get("name")
            for s in self._get_steps_list()
            if isinstance(s, dict) and s.get("name")
        }

        for flow_name, flow_def in flows.items():
            if not isinstance(flow_def, dict):
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Flow '{flow_name}' definition must be a mapping.",
                    )
                )
                continue
            flow_steps = flow_def.get("steps")
            if not isinstance(flow_steps, list):
                issues.append(
                    ValidationIssue(
                        level="error",
                        message=f"Flow '{flow_name}' must have a 'steps' list.",
                        hint="Example: flows:\n  my_flow:\n    steps: [step1, step2]",
                    )
                )
                continue
            for ref in flow_steps:
                if not isinstance(ref, str):
                    issues.append(
                        ValidationIssue(
                            level="error",
                            message=(
                                f"Flow '{flow_name}': step reference must be a string, "
                                f"got {type(ref).__name__}."
                            ),
                        )
                    )
                elif ref not in defined_step_names:
                    issues.append(
                        ValidationIssue(
                            level="error",
                            message=(
                                f"Flow '{flow_name}' references step '{ref}' which does not exist."
                            ),
                            hint=(
                                "Check the step name spelling. "
                                f"Defined steps: {', '.join(sorted(s for s in defined_step_names if s)) or '(none)'}."
                            ),
                        )
                    )
        return issues

    def _check_param_references(self) -> List[ValidationIssue]:
        """Warn when args.X is used in a template but X is not declared in params."""
        issues: List[ValidationIssue] = []
        wf = self._workflow
        if not isinstance(wf, dict):
            return issues

        declared_params = set(wf.get("params", {}).keys())

        for step in self._get_steps_list():
            if not isinstance(step, dict):
                continue
            step_name = step.get("name", "<unnamed>")
            inputs = step.get("inputs") or {}
            if not isinstance(inputs, dict):
                continue
            for input_key, value in inputs.items():
                for match in _ARGS_REF_RE.finditer(str(value)):
                    param_name = match.group(1)
                    if param_name not in declared_params:
                        issues.append(
                            ValidationIssue(
                                level="warning",
                                message=(
                                    f"Step '{step_name}', input '{input_key}': "
                                    f"references 'args.{param_name}' which is not declared in params."
                                ),
                                step=step_name,
                                hint=(
                                    f"Add '{param_name}' to the 'params' section, "
                                    "or check the spelling of the parameter name."
                                ),
                            )
                        )
        return issues

    def _check_step_result_access(self) -> List[ValidationIssue]:
        """Detect the common double-result bug: steps.X.result.result.Y."""
        issues: List[ValidationIssue] = []
        for step in self._get_steps_list():
            if not isinstance(step, dict):
                continue
            step_name = step.get("name", "<unnamed>")
            inputs = step.get("inputs") or {}
            if not isinstance(inputs, dict):
                continue
            for input_key, value in inputs.items():
                if _DOUBLE_RESULT_RE.search(str(value)):
                    issues.append(
                        ValidationIssue(
                            level="warning",
                            message=(
                                f"Step '{step_name}': double result access pattern detected "
                                f"in input '{input_key}'."
                            ),
                            step=step_name,
                            hint=(
                                "Use steps.STEP_NAME.result.KEY, "
                                "not steps.STEP_NAME.result.result.KEY."
                            ),
                        )
                    )
        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_steps_list(self) -> List[Any]:
        """Return steps as a flat list regardless of dict/list format."""
        wf = self._workflow
        if not isinstance(wf, dict):
            return []
        steps = wf.get("steps", [])
        if isinstance(steps, dict):
            result = []
            for step_name, step_cfg in steps.items():
                if isinstance(step_cfg, dict):
                    if "name" not in step_cfg:
                        step_cfg = dict(step_cfg)
                        step_cfg["name"] = step_name
                    result.append(step_cfg)
                else:
                    result.append(step_cfg)
            return result
        if isinstance(steps, list):
            return steps
        return []

    def _find_step_line(self, step_name: str) -> Optional[int]:
        """Attempt to locate the line number for a step by searching the raw text."""
        if not self._raw_text or not step_name:
            return None
        for idx, line in enumerate(self._raw_text.splitlines(), start=1):
            if f"name: {step_name}" in line or f"name: '{step_name}'" in line:
                return idx
        return None
