# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Workflow tool for the agent."""

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

ROOT_DIR = Path(__file__).parent.parent
WORKFLOWS_DIR = ROOT_DIR / "data" / "workflows"

# Valid status values
VALID_WORKFLOW_STATUSES = {"created", "running", "paused", "completed", "failed"}
VALID_NODE_STATES = {"pending", "running", "success", "failed", "skipped"}


def _apply_changes(data: dict, changes: dict) -> dict:
    """Apply changes to data, supporting dot notation for nested paths.

    Supports:
    - Simple keys: {"status": "running"}
    - Nested paths: {"context.resonator_freq": 5.823}
    - Node updates: {"nodes.node_1.state": "success"}

    For nodes, uses node ID to find the correct node in the array.
    """
    result = copy.deepcopy(data)

    for key, value in changes.items():
        if "." not in key:
            # Simple key - direct assignment
            result[key] = value
        else:
            # Dot notation - traverse path
            parts = key.split(".")
            target = result

            # Navigate to parent of final key
            for i, part in enumerate(parts[:-1]):
                if part == "nodes" and isinstance(target.get("nodes"), list):
                    # Next part should be node ID
                    target = target["nodes"]
                elif isinstance(target, list):
                    # Find node by ID
                    node = next((n for n in target if n.get("id") == part), None)
                    if node is None:
                        # Node not found, skip this change
                        target = None
                        break
                    target = node
                elif isinstance(target, dict):
                    if part not in target:
                        target[part] = {}
                    target = target[part]
                else:
                    target = None
                    break

            # Set the final value
            if target is not None:
                final_key = parts[-1]
                if isinstance(target, dict):
                    target[final_key] = value

    return result


def _validate_workflow_comprehensive(workflow_id: str) -> dict:
    """Validate a workflow with comprehensive checks.

    Returns detailed validation results following the validate_script pattern.
    """
    result = {
        "valid": False,
        "checks": [],
        "workflow_info": None,
        "errors": [],
        "warnings": [],
    }

    wf_dir = WORKFLOWS_DIR / workflow_id
    wf_file = wf_dir / "workflow.json"
    plan_file = wf_dir / "plan.md"

    # Check 1: Directory exists
    if not wf_dir.exists():
        result["checks"].append(
            {
                "check": "directory_exists",
                "passed": False,
                "message": f"Workflow directory not found: {wf_dir}",
            }
        )
        result["errors"].append(f"Workflow directory not found: {workflow_id}")
        return result
    result["checks"].append(
        {
            "check": "directory_exists",
            "passed": True,
            "message": "Workflow directory exists",
        }
    )

    # Check 2: workflow.json exists
    if not wf_file.exists():
        result["checks"].append(
            {
                "check": "file_exists",
                "passed": False,
                "message": "workflow.json not found",
            }
        )
        result["errors"].append(f"workflow.json not found in {wf_dir}")
        return result
    result["checks"].append(
        {"check": "file_exists", "passed": True, "message": "workflow.json exists"}
    )

    # Check 3: Valid JSON syntax
    try:
        data = json.loads(wf_file.read_text())
    except json.JSONDecodeError as e:
        result["checks"].append(
            {
                "check": "json_syntax",
                "passed": False,
                "message": f"Invalid JSON at line {e.lineno}: {e.msg}",
            }
        )
        result["errors"].append(f"Invalid JSON syntax: {e}")
        return result
    result["checks"].append(
        {"check": "json_syntax", "passed": True, "message": "Valid JSON syntax"}
    )

    # Check 4: Required fields (id, name, nodes)
    required_fields = ["id", "name", "nodes"]
    missing_fields = [f for f in required_fields if f not in data]
    if missing_fields:
        result["checks"].append(
            {
                "check": "required_fields",
                "passed": False,
                "message": f"Missing required fields: {missing_fields}",
            }
        )
        result["errors"].append(f"Missing required fields: {missing_fields}")
        return result
    result["checks"].append(
        {
            "check": "required_fields",
            "passed": True,
            "message": "All required fields present (id, name, nodes)",
        }
    )

    # Check 5: nodes is a list
    if not isinstance(data["nodes"], list):
        result["checks"].append(
            {
                "check": "nodes_is_list",
                "passed": False,
                "message": f"'nodes' must be a list, got {type(data['nodes']).__name__}",
            }
        )
        result["errors"].append("'nodes' field must be a list")
        return result
    result["checks"].append(
        {"check": "nodes_is_list", "passed": True, "message": "'nodes' is a list"}
    )

    nodes = data["nodes"]

    # Check 6: Has at least one node
    if not nodes:
        result["checks"].append(
            {"check": "has_nodes", "passed": False, "message": "Workflow has no nodes"}
        )
        result["errors"].append("Workflow must have at least one node")
        return result
    result["checks"].append(
        {
            "check": "has_nodes",
            "passed": True,
            "message": f"Workflow has {len(nodes)} node(s)",
        }
    )

    # Check 7: Node IDs are unique
    node_ids = []
    duplicate_ids = []
    for node in nodes:
        if "id" not in node:
            result["checks"].append(
                {
                    "check": "node_ids_present",
                    "passed": False,
                    "message": f"Node missing 'id' field: {node}",
                }
            )
            result["errors"].append(
                f"Node missing 'id' field: {node.get('name', 'unknown')}"
            )
            return result
        if node["id"] in node_ids:
            duplicate_ids.append(node["id"])
        node_ids.append(node["id"])

    if duplicate_ids:
        result["checks"].append(
            {
                "check": "node_ids_unique",
                "passed": False,
                "message": f"Duplicate node IDs: {duplicate_ids}",
            }
        )
        result["errors"].append(f"Duplicate node IDs found: {duplicate_ids}")
        return result
    result["checks"].append(
        {
            "check": "node_ids_unique",
            "passed": True,
            "message": "All node IDs are unique",
        }
    )

    # Check 8: All nodes have required fields (id, name)
    for node in nodes:
        if "name" not in node:
            result["checks"].append(
                {
                    "check": "node_names_present",
                    "passed": False,
                    "message": f"Node '{node['id']}' missing 'name' field",
                }
            )
            result["errors"].append(f"Node '{node['id']}' missing 'name' field")
            return result
    result["checks"].append(
        {
            "check": "node_names_present",
            "passed": True,
            "message": "All nodes have 'name' field",
        }
    )

    # Check 9: Edge references (dependencies reference existing nodes)
    node_id_set = set(node_ids)
    invalid_deps = []
    for node in nodes:
        deps = node.get("dependencies", [])
        if not isinstance(deps, list):
            result["checks"].append(
                {
                    "check": "dependencies_valid",
                    "passed": False,
                    "message": f"Node '{node['id']}' dependencies must be a list",
                }
            )
            result["errors"].append(
                f"Node '{node['id']}' dependencies must be a list, got {type(deps).__name__}"
            )
            return result
        for dep in deps:
            if dep not in node_id_set:
                invalid_deps.append({"node": node["id"], "invalid_dep": dep})

    if invalid_deps:
        result["checks"].append(
            {
                "check": "edge_references",
                "passed": False,
                "message": f"Invalid dependency references: {invalid_deps}",
            }
        )
        result["errors"].append(f"Invalid dependency references: {invalid_deps}")
        return result
    result["checks"].append(
        {
            "check": "edge_references",
            "passed": True,
            "message": "All dependency references are valid",
        }
    )

    # Check 10: No cycles (DAG validation)
    is_dag, cycle_error = _validate_dag(nodes)
    if not is_dag:
        result["checks"].append(
            {"check": "no_cycles", "passed": False, "message": cycle_error}
        )
        result["errors"].append(cycle_error)
        return result
    result["checks"].append(
        {
            "check": "no_cycles",
            "passed": True,
            "message": "No circular dependencies (valid DAG)",
        }
    )

    # Check 11: Workflow status value (warning)
    wf_status = data.get("status", "created")
    if wf_status not in VALID_WORKFLOW_STATUSES:
        result["checks"].append(
            {
                "check": "workflow_status_valid",
                "passed": False,
                "message": f"Invalid workflow status: '{wf_status}'",
            }
        )
        result["warnings"].append(
            f"Invalid workflow status '{wf_status}'. Valid: {VALID_WORKFLOW_STATUSES}"
        )
    else:
        result["checks"].append(
            {
                "check": "workflow_status_valid",
                "passed": True,
                "message": f"Workflow status is valid: '{wf_status}'",
            }
        )

    # Check 12: Node state values (warning)
    invalid_states = []
    for node in nodes:
        state = node.get("state", "pending")
        if state not in VALID_NODE_STATES:
            invalid_states.append({"node": node["id"], "state": state})

    if invalid_states:
        result["checks"].append(
            {
                "check": "node_states_valid",
                "passed": False,
                "message": f"Invalid node states: {invalid_states}",
            }
        )
        result["warnings"].append(
            f"Invalid node states: {invalid_states}. Valid: {VALID_NODE_STATES}"
        )
    else:
        result["checks"].append(
            {
                "check": "node_states_valid",
                "passed": True,
                "message": "All node states are valid",
            }
        )

    # Check 13: plan.md exists (warning)
    if not plan_file.exists():
        result["checks"].append(
            {"check": "plan_exists", "passed": False, "message": "plan.md not found"}
        )
        result["warnings"].append(
            "plan.md not found - consider creating a planning document"
        )
    else:
        result["checks"].append(
            {"check": "plan_exists", "passed": True, "message": "plan.md exists"}
        )

    # Check 14: Orphan nodes (warning) - nodes with no dependencies and not depended on
    depended_on = set()
    for node in nodes:
        for dep in node.get("dependencies", []):
            depended_on.add(dep)

    has_deps = set()
    for node in nodes:
        if node.get("dependencies"):
            has_deps.add(node["id"])

    # Root nodes (no dependencies) are OK
    # Leaf nodes (not depended on) are OK
    # But totally isolated nodes (no deps AND not depended on AND not the only node) are suspicious
    if len(nodes) > 1:
        isolated = []
        for node in nodes:
            node_id = node["id"]
            if not node.get("dependencies") and node_id not in depended_on:
                isolated.append(node_id)

        if (
            len(isolated) > 1
        ):  # More than one root node might be intentional for parallel starts
            result["checks"].append(
                {
                    "check": "no_isolated_nodes",
                    "passed": True,
                    "message": f"Multiple root nodes: {isolated} (parallel start points)",
                }
            )
        elif isolated:
            result["checks"].append(
                {
                    "check": "no_isolated_nodes",
                    "passed": True,
                    "message": f"Root node: {isolated[0]}",
                }
            )
        else:
            result["checks"].append(
                {
                    "check": "no_isolated_nodes",
                    "passed": True,
                    "message": "All nodes are connected",
                }
            )

    # Build workflow info (similar to schema in validate_script)
    completed = sum(1 for n in nodes if n.get("state") == "success")
    failed = sum(1 for n in nodes if n.get("state") == "failed")

    result["workflow_info"] = {
        "id": data.get("id"),
        "name": data.get("name"),
        "status": wf_status,
        "node_count": len(nodes),
        "edge_count": sum(len(n.get("dependencies", [])) for n in nodes),
        "progress": f"{completed}/{len(nodes)} completed"
        + (f", {failed} failed" if failed else ""),
        "path": str(wf_dir),
    }

    result["valid"] = len(result["errors"]) == 0
    return result


def _validate_dag(nodes: list) -> tuple[bool, str]:
    """Validate workflow DAG structure.

    Returns (is_valid, error_message).
    """
    if not nodes:
        return False, "Workflow has no nodes"

    # Check all nodes have required fields
    node_ids = set()
    for node in nodes:
        if "id" not in node:
            return False, f"Node missing 'id' field: {node}"
        if "name" not in node:
            return False, f"Node '{node['id']}' missing 'name' field"
        if node["id"] in node_ids:
            return False, f"Duplicate node ID: {node['id']}"
        node_ids.add(node["id"])

    # Check all dependencies reference valid nodes
    for node in nodes:
        deps = node.get("dependencies", [])
        for dep in deps:
            if dep not in node_ids:
                return False, f"Node '{node['id']}' has invalid dependency '{dep}'"

    # Check for cycles using DFS
    visited = set()
    rec_stack = set()

    def has_cycle(node_id: str) -> bool:
        visited.add(node_id)
        rec_stack.add(node_id)

        node = next(n for n in nodes if n["id"] == node_id)
        for dep in node.get("dependencies", []):
            if dep not in visited:
                if has_cycle(dep):
                    return True
            elif dep in rec_stack:
                return True

        rec_stack.remove(node_id)
        return False

    for node in nodes:
        if node["id"] not in visited:
            if has_cycle(node["id"]):
                return False, "Workflow contains a cycle"

    return True, ""


def _load_workflow(workflow_id: str) -> tuple[dict | None, str | None]:
    """Load workflow.json. Returns (data, error)."""
    wf_dir = WORKFLOWS_DIR / workflow_id
    wf_file = wf_dir / "workflow.json"

    if not wf_file.exists():
        return None, f"Workflow not found: {workflow_id}"

    try:
        data = json.loads(wf_file.read_text())
        return data, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"


def _load_history(workflow_id: str, last_n: int = 20) -> list[dict]:
    """Load recent history events."""
    history_file = WORKFLOWS_DIR / workflow_id / "history.jsonl"

    if not history_file.exists():
        return []

    events = []
    try:
        lines = history_file.read_text().strip().split("\n")
        for line in lines[-last_n:]:
            if line:
                events.append(json.loads(line))
    except (json.JSONDecodeError, IOError):
        pass

    return events


def _format_status(data: dict, history: list[dict]) -> dict:
    """Format workflow status for display."""
    nodes = data.get("nodes", [])
    total = len(nodes)
    completed = sum(1 for n in nodes if n.get("state") == "success")
    failed = sum(1 for n in nodes if n.get("state") == "failed")
    skipped = sum(1 for n in nodes if n.get("state") == "skipped")
    running = sum(1 for n in nodes if n.get("state") == "running")

    # Find current node
    current_node = data.get("current_node")
    current_node_info = None
    if current_node:
        for n in nodes:
            if n["id"] == current_node:
                current_node_info = {
                    "id": n["id"],
                    "name": n["name"],
                    "state": n.get("state", "pending"),
                    "run_count": n.get("run_count", 0),
                }
                break

    result = {
        "id": data.get("id"),
        "name": data.get("name"),
        "objective": data.get("objective"),
        "status": data.get("status", "created"),
        "context": data.get("context", {}),
        "progress": {
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "running": running,
            "pending": total - completed - failed - skipped - running,
            "total": total,
        },
        "current_node": current_node_info,
        "nodes": [
            {
                "id": n["id"],
                "name": n["name"],
                "dependencies": n.get("dependencies", []),
                "state": n.get("state", "pending"),
                "run_count": n.get("run_count", 0),
                "extracted": n.get("extracted"),
                "experiment_id": n.get("experiment_id"),
            }
            for n in nodes
        ],
    }

    # Add pause info if paused
    if data.get("status") == "paused":
        result["paused_reason"] = data.get("paused_reason")
        result["paused_at"] = data.get("paused_at")
        result["suggestions"] = data.get("suggestions", [])

    # Add recent history
    if history:
        result["recent_history"] = history[-10:]

    return result


@tool
def workflow(
    action: str,
    workflow_id: str = "",
    data: dict = None,
    event: str = "",
    last_n: int = 20,
    **kwargs: Any,
) -> dict:
    """Manage and inspect workflows.

    Args:
        action: One of: list, validate, status, history, update, log
        workflow_id: Required for most actions
        data: For update action - dict of changes to apply
        event: For log action - event name to log
        last_n: Number of history events to show (default 20)
        **kwargs: For log action - additional event fields

    Actions:
        list: List all workflows with their status
        validate: Check workflow.json structure and DAG
        status: Show detailed progress, nodes, suggestions if paused
        history: Show recent events from history.jsonl
        update: Create or update workflow (validates before writing)
        log: Append event to history.jsonl

    Returns:
        Dict with result
    """
    # Ensure workflows directory exists
    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

    if action == "list":
        workflows = []
        if WORKFLOWS_DIR.exists():
            for wf_dir in WORKFLOWS_DIR.iterdir():
                if wf_dir.is_dir():
                    wf_file = wf_dir / "workflow.json"
                    if wf_file.exists():
                        try:
                            data = json.loads(wf_file.read_text())
                            nodes = data.get("nodes", [])
                            completed = sum(
                                1 for n in nodes if n.get("state") == "success"
                            )
                            workflows.append(
                                {
                                    "workflow_id": wf_dir.name,
                                    "name": data.get("name", ""),
                                    "status": data.get("status", "created"),
                                    "progress": f"{completed}/{len(nodes)}",
                                    "current_node": data.get("current_node"),
                                }
                            )
                        except json.JSONDecodeError:
                            workflows.append(
                                {
                                    "workflow_id": wf_dir.name,
                                    "error": "Invalid JSON",
                                }
                            )

        if not workflows:
            return {"workflows": [], "message": "No workflows found"}
        return {"workflows": workflows}

    if action == "validate":
        if not workflow_id:
            return {
                "valid": False,
                "errors": ["workflow_id required"],
                "checks": [],
                "warnings": [],
            }

        # Use comprehensive validation
        return _validate_workflow_comprehensive(workflow_id)

    if action == "status":
        if not workflow_id:
            return {"error": "workflow_id required"}

        data, error = _load_workflow(workflow_id)
        if error:
            return {"error": error}

        history = _load_history(workflow_id, last_n=10)
        status = _format_status(data, history)

        return status

    if action == "history":
        if not workflow_id:
            return {"error": "workflow_id required"}

        history_file = WORKFLOWS_DIR / workflow_id / "history.jsonl"

        if not history_file.exists():
            return {"events": [], "message": "No history found"}

        events = _load_history(workflow_id, last_n=last_n)

        return {
            "workflow_id": workflow_id,
            "events": events,
            "count": len(events),
        }

    if action == "update":
        if not workflow_id:
            return {"error": "workflow_id required"}
        if not data:
            return {"error": "data required"}

        wf_dir = WORKFLOWS_DIR / workflow_id
        wf_file = wf_dir / "workflow.json"

        # Load existing or start fresh
        if wf_file.exists():
            try:
                existing = json.loads(wf_file.read_text())
            except json.JSONDecodeError as e:
                return {"error": f"Existing workflow.json is invalid: {e}"}
            is_new = False
        else:
            existing = {"id": workflow_id}
            is_new = True

        # Apply changes
        merged = _apply_changes(existing, data)

        # Ensure directory exists
        wf_dir.mkdir(parents=True, exist_ok=True)

        # Write tentatively
        wf_file.write_text(json.dumps(merged, indent=2))

        # Validate
        validation = _validate_workflow_comprehensive(workflow_id)

        if not validation["valid"]:
            # Rollback: restore original or delete if new
            if is_new:
                wf_file.unlink(missing_ok=True)
                if wf_dir.exists() and not any(wf_dir.iterdir()):
                    wf_dir.rmdir()
            else:
                wf_file.write_text(json.dumps(existing, indent=2))

            return {
                "error": "Validation failed",
                "details": validation["errors"],
                "warnings": validation["warnings"],
            }

        return {
            "success": True,
            "workflow_id": workflow_id,
            "created": is_new,
            "validation": {
                "valid": validation["valid"],
                "warnings": validation["warnings"],
            },
        }

    if action == "log":
        if not workflow_id:
            return {"error": "workflow_id required"}
        if not event:
            return {"error": "event required"}

        wf_dir = WORKFLOWS_DIR / workflow_id

        if not wf_dir.exists():
            return {"error": f"Workflow not found: {workflow_id}"}

        history_file = wf_dir / "history.jsonl"

        # Build event entry with auto-timestamp
        entry = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": event,
            **kwargs,
        }

        # Append to history
        with open(history_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return {"success": True, "logged": entry}

    return {"error": f"Unknown action: {action}. Use: list, validate, status, history, update, log"}
