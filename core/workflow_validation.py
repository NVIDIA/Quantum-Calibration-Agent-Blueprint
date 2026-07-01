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
