# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Shared structural validation helpers for persisted workflows."""

from typing import Any


def get_workflow_nodes(data: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Return workflow nodes or a user-facing structural validation error."""
    if not isinstance(data, dict):
        return None, f"workflow must be an object, got {type(data).__name__}"

    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        return None, f"'nodes' must be a list, got {type(nodes).__name__}"

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            return (
                None,
                f"nodes[{index}] must be an object, got {type(node).__name__}",
            )

    return nodes, None


def get_node_dependencies(node: Any) -> tuple[list[str] | None, str | None]:
    """Return a node's dependency IDs or a user-facing structural error.

    Every element is checked before any caller compares it against the set of
    known node IDs. An unhashable element such as a list or dict would
    otherwise raise TypeError from that membership test rather than producing
    a validation result.
    """
    node_id = node.get("id", "unknown") if isinstance(node, dict) else "unknown"
    deps = node.get("dependencies", []) if isinstance(node, dict) else None

    if not isinstance(deps, list):
        return (
            None,
            f"Node '{node_id}' dependencies must be a list, "
            f"got {type(deps).__name__}",
        )

    for index, dep in enumerate(deps):
        if not isinstance(dep, str) or not dep:
            return (
                None,
                f"Node '{node_id}' dependencies[{index}] must be a non-empty "
                f"string, got {type(dep).__name__}",
            )

    return deps, None


def is_hashable(value: Any) -> bool:
    """Report whether a value can be compared against a set of valid values.

    Persisted workflows can carry a list or dict where a status string is
    expected, and membership tests against the valid-value sets raise on those.
    """
    try:
        hash(value)
    except TypeError:
        return False
    return True
