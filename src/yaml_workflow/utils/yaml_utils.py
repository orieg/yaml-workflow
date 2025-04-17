"""YAML utilities for the workflow engine."""

from typing import Any

import yaml


def raw_constructor(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> str:
    """Constructor for !raw tag that preserves raw string content."""
    return loader.construct_scalar(node)


def get_safe_loader() -> type[yaml.SafeLoader]:
    """Get a SafeLoader with custom constructors registered."""
    loader = yaml.SafeLoader
    loader.add_constructor("!raw", raw_constructor)
    return loader
