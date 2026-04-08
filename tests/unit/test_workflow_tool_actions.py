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

"""Unit tests for workflow tool list, validate, status, history actions and helpers."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.workflow_tool import (
    WORKFLOWS_DIR,
    _format_status,
    _load_history,
    _load_workflow,
    _validate_dag,
    workflow,
)


# ---------------------------------------------------------------------------
# list action
# ---------------------------------------------------------------------------
class TestListAction:
    """Tests for the 'list' action."""

    @pytest.fixture(autouse=True)
    def _patch_dir(self, tmp_path, monkeypatch):
        self.workflows_dir = tmp_path / "workflows"
        self.workflows_dir.mkdir()
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", self.workflows_dir)

    def test_empty_workflows_dir(self):
        result = workflow.func(action="list")
        assert result["workflows"] == []
        assert "No workflows found" in result["message"]

    def test_one_valid_workflow(self, sample_workflow):
        wf_dir = self.workflows_dir / sample_workflow["id"]
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(json.dumps(sample_workflow))

        result = workflow.func(action="list")
        assert len(result["workflows"]) == 1
        wf = result["workflows"][0]
        assert wf["workflow_id"] == sample_workflow["id"]
        assert wf["name"] == sample_workflow["name"]
        assert wf["status"] == sample_workflow["status"]
        # node_1 is success => 1/3
        assert wf["progress"] == "1/3"

    def test_invalid_json_workflow(self):
        wf_dir = self.workflows_dir / "bad_wf"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text("{not valid json")

        result = workflow.func(action="list")
        assert len(result["workflows"]) == 1
        assert result["workflows"][0]["workflow_id"] == "bad_wf"
        assert result["workflows"][0]["error"] == "Invalid JSON"


# ---------------------------------------------------------------------------
# validate action
# ---------------------------------------------------------------------------
class TestValidateAction:
    """Tests for the 'validate' action."""

    @pytest.fixture(autouse=True)
    def _patch_dir(self, tmp_path, monkeypatch):
        self.workflows_dir = tmp_path / "workflows"
        self.workflows_dir.mkdir()
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", self.workflows_dir)

    def test_missing_workflow_id(self):
        result = workflow.func(action="validate")
        assert result["valid"] is False
        assert "workflow_id required" in result["errors"]

    def test_valid_workflow(self, sample_workflow):
        wf_dir = self.workflows_dir / sample_workflow["id"]
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(json.dumps(sample_workflow))
        # Create plan.md to avoid warning
        (wf_dir / "plan.md").write_text("# Plan")

        result = workflow.func(action="validate", workflow_id=sample_workflow["id"])
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["workflow_info"] is not None
        assert result["workflow_info"]["node_count"] == 3

    def test_missing_directory(self):
        result = workflow.func(action="validate", workflow_id="nonexistent")
        assert result["valid"] is False
        assert any("not found" in e for e in result["errors"])

    def test_missing_workflow_json(self):
        wf_dir = self.workflows_dir / "empty_dir"
        wf_dir.mkdir()

        result = workflow.func(action="validate", workflow_id="empty_dir")
        assert result["valid"] is False
        assert any("workflow.json" in e for e in result["errors"])

    def test_invalid_json(self):
        wf_dir = self.workflows_dir / "bad_json"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text("{bad")

        result = workflow.func(action="validate", workflow_id="bad_json")
        assert result["valid"] is False
        assert any("Invalid JSON" in e for e in result["errors"])

    def test_missing_required_fields(self):
        wf_dir = self.workflows_dir / "missing_fields"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(json.dumps({"id": "missing_fields"}))

        result = workflow.func(action="validate", workflow_id="missing_fields")
        assert result["valid"] is False
        assert any("Missing required fields" in e for e in result["errors"])

    def test_nodes_not_a_list(self):
        wf_dir = self.workflows_dir / "bad_nodes"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(
            json.dumps({"id": "bad_nodes", "name": "Bad", "nodes": "not a list"})
        )

        result = workflow.func(action="validate", workflow_id="bad_nodes")
        assert result["valid"] is False
        assert any("list" in e for e in result["errors"])

    def test_empty_nodes(self):
        wf_dir = self.workflows_dir / "empty_nodes"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(
            json.dumps({"id": "empty_nodes", "name": "Empty", "nodes": []})
        )

        result = workflow.func(action="validate", workflow_id="empty_nodes")
        assert result["valid"] is False
        assert any("at least one node" in e for e in result["errors"])

    def test_duplicate_node_ids(self):
        wf_dir = self.workflows_dir / "dup_ids"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "id": "dup_ids",
                    "name": "Dup",
                    "nodes": [
                        {"id": "n1", "name": "A", "dependencies": []},
                        {"id": "n1", "name": "B", "dependencies": []},
                    ],
                }
            )
        )

        result = workflow.func(action="validate", workflow_id="dup_ids")
        assert result["valid"] is False
        assert any("Duplicate" in e for e in result["errors"])

    def test_missing_node_names(self):
        wf_dir = self.workflows_dir / "no_name"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "id": "no_name",
                    "name": "No Name",
                    "nodes": [{"id": "n1", "dependencies": []}],
                }
            )
        )

        result = workflow.func(action="validate", workflow_id="no_name")
        assert result["valid"] is False
        assert any("name" in e.lower() for e in result["errors"])

    def test_invalid_dependency_references(self):
        wf_dir = self.workflows_dir / "bad_deps"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "id": "bad_deps",
                    "name": "Bad Deps",
                    "nodes": [
                        {
                            "id": "n1",
                            "name": "N1",
                            "dependencies": ["nonexistent"],
                        }
                    ],
                }
            )
        )

        result = workflow.func(action="validate", workflow_id="bad_deps")
        assert result["valid"] is False
        assert any("Invalid dependency" in e for e in result["errors"])

    def test_circular_dependencies(self, circular_workflow):
        wf_dir = self.workflows_dir / circular_workflow["id"]
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(json.dumps(circular_workflow))

        result = workflow.func(
            action="validate", workflow_id=circular_workflow["id"]
        )
        assert result["valid"] is False
        assert any("cycle" in e.lower() for e in result["errors"])

    def test_invalid_workflow_status_warning(self):
        wf_dir = self.workflows_dir / "bad_status"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "id": "bad_status",
                    "name": "Bad Status",
                    "status": "banana",
                    "nodes": [
                        {"id": "n1", "name": "N1", "dependencies": []},
                    ],
                }
            )
        )
        (wf_dir / "plan.md").write_text("# Plan")

        result = workflow.func(action="validate", workflow_id="bad_status")
        # Invalid status is a warning, not an error
        assert result["valid"] is True
        assert any("banana" in w for w in result["warnings"])

    def test_invalid_node_states_warning(self):
        wf_dir = self.workflows_dir / "bad_state"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(
            json.dumps(
                {
                    "id": "bad_state",
                    "name": "Bad State",
                    "status": "running",
                    "nodes": [
                        {
                            "id": "n1",
                            "name": "N1",
                            "state": "exploded",
                            "dependencies": [],
                        },
                    ],
                }
            )
        )
        (wf_dir / "plan.md").write_text("# Plan")

        result = workflow.func(action="validate", workflow_id="bad_state")
        assert result["valid"] is True
        assert any("exploded" in w for w in result["warnings"])

    def test_missing_plan_md_warning(self, sample_workflow):
        wf_dir = self.workflows_dir / sample_workflow["id"]
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(json.dumps(sample_workflow))
        # No plan.md created

        result = workflow.func(action="validate", workflow_id=sample_workflow["id"])
        assert result["valid"] is True
        assert any("plan.md" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# status action
# ---------------------------------------------------------------------------
class TestStatusAction:
    """Tests for the 'status' action."""

    @pytest.fixture(autouse=True)
    def _patch_dir(self, tmp_path, monkeypatch):
        self.workflows_dir = tmp_path / "workflows"
        self.workflows_dir.mkdir()
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", self.workflows_dir)

    def _write_workflow(self, data):
        wf_dir = self.workflows_dir / data["id"]
        wf_dir.mkdir(parents=True, exist_ok=True)
        (wf_dir / "workflow.json").write_text(json.dumps(data))

    def test_missing_workflow_id(self):
        result = workflow.func(action="status")
        assert "error" in result
        assert "workflow_id" in result["error"]

    def test_workflow_not_found(self):
        result = workflow.func(action="status", workflow_id="nope")
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_running_workflow(self, sample_workflow):
        self._write_workflow(sample_workflow)
        result = workflow.func(
            action="status", workflow_id=sample_workflow["id"]
        )

        assert result["status"] == "running"
        assert result["progress"]["completed"] == 1
        assert result["progress"]["running"] == 1
        assert result["progress"]["pending"] == 1
        assert result["progress"]["total"] == 3

    def test_paused_workflow_includes_suggestions(self, paused_workflow):
        self._write_workflow(paused_workflow)
        result = workflow.func(
            action="status", workflow_id=paused_workflow["id"]
        )

        assert result["status"] == "paused"
        assert result["paused_reason"] == "Node failed after max retries"
        assert len(result["suggestions"]) == 2

    def test_completed_workflow(self, completed_workflow):
        self._write_workflow(completed_workflow)
        result = workflow.func(
            action="status", workflow_id=completed_workflow["id"]
        )

        assert result["status"] == "completed"
        assert result["progress"]["completed"] == 1
        assert result["progress"]["total"] == 1


# ---------------------------------------------------------------------------
# history action
# ---------------------------------------------------------------------------
class TestHistoryAction:
    """Tests for the 'history' action."""

    @pytest.fixture(autouse=True)
    def _patch_dir(self, tmp_path, monkeypatch):
        self.workflows_dir = tmp_path / "workflows"
        self.workflows_dir.mkdir()
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", self.workflows_dir)

    def test_missing_workflow_id(self):
        result = workflow.func(action="history")
        assert "error" in result
        assert "workflow_id" in result["error"]

    def test_no_history_file(self):
        wf_dir = self.workflows_dir / "wf1"
        wf_dir.mkdir()

        result = workflow.func(action="history", workflow_id="wf1")
        assert result["events"] == []
        assert "No history found" in result["message"]

    def test_valid_history(self, sample_history):
        wf_dir = self.workflows_dir / "wf1"
        wf_dir.mkdir()
        with open(wf_dir / "history.jsonl", "w") as f:
            for event in sample_history:
                f.write(json.dumps(event) + "\n")

        result = workflow.func(action="history", workflow_id="wf1")
        assert result["workflow_id"] == "wf1"
        assert result["count"] == len(sample_history)
        assert result["events"][0]["event"] == "workflow_started"


# ---------------------------------------------------------------------------
# _validate_dag helper
# ---------------------------------------------------------------------------
class TestValidateDag:
    """Tests for the _validate_dag helper."""

    def test_empty_nodes(self):
        valid, msg = _validate_dag([])
        assert valid is False
        assert "no nodes" in msg.lower()

    def test_valid_linear_dag(self):
        nodes = [
            {"id": "a", "name": "A", "dependencies": []},
            {"id": "b", "name": "B", "dependencies": ["a"]},
        ]
        valid, msg = _validate_dag(nodes)
        assert valid is True

    def test_missing_id(self):
        valid, msg = _validate_dag([{"name": "A"}])
        assert valid is False
        assert "id" in msg.lower()

    def test_missing_name(self):
        valid, msg = _validate_dag([{"id": "a"}])
        assert valid is False
        assert "name" in msg.lower()

    def test_duplicate_ids(self):
        nodes = [
            {"id": "a", "name": "A", "dependencies": []},
            {"id": "a", "name": "B", "dependencies": []},
        ]
        valid, msg = _validate_dag(nodes)
        assert valid is False
        assert "Duplicate" in msg

    def test_invalid_dep_reference(self):
        nodes = [{"id": "a", "name": "A", "dependencies": ["z"]}]
        valid, msg = _validate_dag(nodes)
        assert valid is False
        assert "invalid dependency" in msg.lower()

    def test_cycle_detected(self):
        nodes = [
            {"id": "a", "name": "A", "dependencies": ["b"]},
            {"id": "b", "name": "B", "dependencies": ["a"]},
        ]
        valid, msg = _validate_dag(nodes)
        assert valid is False
        assert "cycle" in msg.lower()


# ---------------------------------------------------------------------------
# _load_workflow helper
# ---------------------------------------------------------------------------
class TestLoadWorkflow:
    """Tests for the _load_workflow helper."""

    @pytest.fixture(autouse=True)
    def _patch_dir(self, tmp_path, monkeypatch):
        self.workflows_dir = tmp_path / "workflows"
        self.workflows_dir.mkdir()
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", self.workflows_dir)

    def test_not_found(self):
        data, err = _load_workflow("nonexistent")
        assert data is None
        assert "not found" in err.lower()

    def test_invalid_json(self):
        wf_dir = self.workflows_dir / "bad"
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text("{bad")

        data, err = _load_workflow("bad")
        assert data is None
        assert "Invalid JSON" in err

    def test_valid_load(self, sample_workflow):
        wf_dir = self.workflows_dir / sample_workflow["id"]
        wf_dir.mkdir()
        (wf_dir / "workflow.json").write_text(json.dumps(sample_workflow))

        data, err = _load_workflow(sample_workflow["id"])
        assert err is None
        assert data["id"] == sample_workflow["id"]


# ---------------------------------------------------------------------------
# _load_history helper
# ---------------------------------------------------------------------------
class TestLoadHistory:
    """Tests for the _load_history helper."""

    @pytest.fixture(autouse=True)
    def _patch_dir(self, tmp_path, monkeypatch):
        self.workflows_dir = tmp_path / "workflows"
        self.workflows_dir.mkdir()
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", self.workflows_dir)

    def test_no_history_file(self):
        wf_dir = self.workflows_dir / "wf"
        wf_dir.mkdir()
        events = _load_history("wf")
        assert events == []

    def test_loads_events(self, sample_history):
        wf_dir = self.workflows_dir / "wf"
        wf_dir.mkdir()
        with open(wf_dir / "history.jsonl", "w") as f:
            for event in sample_history:
                f.write(json.dumps(event) + "\n")

        events = _load_history("wf")
        assert len(events) == len(sample_history)

    def test_last_n_limits(self, sample_history):
        wf_dir = self.workflows_dir / "wf"
        wf_dir.mkdir()
        with open(wf_dir / "history.jsonl", "w") as f:
            for event in sample_history:
                f.write(json.dumps(event) + "\n")

        events = _load_history("wf", last_n=2)
        assert len(events) == 2
        # Should return the last 2 events
        assert events[0]["event"] == sample_history[-2]["event"]
        assert events[1]["event"] == sample_history[-1]["event"]


# ---------------------------------------------------------------------------
# _format_status helper
# ---------------------------------------------------------------------------
class TestFormatStatus:
    """Tests for the _format_status helper."""

    def test_mixed_node_states(self):
        data = {
            "id": "wf1",
            "name": "Mixed",
            "status": "running",
            "nodes": [
                {"id": "n1", "name": "N1", "state": "pending", "dependencies": []},
                {"id": "n2", "name": "N2", "state": "running", "dependencies": [], "run_count": 1},
                {"id": "n3", "name": "N3", "state": "success", "dependencies": [], "run_count": 1},
                {"id": "n4", "name": "N4", "state": "failed", "dependencies": [], "run_count": 2},
                {"id": "n5", "name": "N5", "state": "skipped", "dependencies": []},
            ],
        }
        result = _format_status(data, [])

        assert result["progress"]["pending"] == 1
        assert result["progress"]["running"] == 1
        assert result["progress"]["completed"] == 1
        assert result["progress"]["failed"] == 1
        assert result["progress"]["skipped"] == 1
        assert result["progress"]["total"] == 5

    def test_current_node_set(self):
        data = {
            "id": "wf1",
            "name": "W",
            "status": "running",
            "current_node": "n1",
            "nodes": [
                {"id": "n1", "name": "Node 1", "state": "running", "dependencies": [], "run_count": 2},
            ],
        }
        result = _format_status(data, [])

        assert result["current_node"] is not None
        assert result["current_node"]["id"] == "n1"
        assert result["current_node"]["name"] == "Node 1"
        assert result["current_node"]["state"] == "running"
        assert result["current_node"]["run_count"] == 2

    def test_current_node_none(self):
        data = {
            "id": "wf1",
            "name": "W",
            "status": "created",
            "nodes": [{"id": "n1", "name": "N1", "state": "pending", "dependencies": []}],
        }
        result = _format_status(data, [])
        assert result["current_node"] is None

    def test_paused_with_suggestions(self, paused_workflow):
        result = _format_status(paused_workflow, [])

        assert result["status"] == "paused"
        assert result["paused_reason"] == "Node failed after max retries"
        assert result["paused_at"] == "2026-03-22T08:30:00Z"
        assert len(result["suggestions"]) == 2

    def test_with_history(self, sample_workflow, sample_history):
        result = _format_status(sample_workflow, sample_history)

        assert "recent_history" in result
        assert len(result["recent_history"]) == len(sample_history)

    def test_no_history(self, sample_workflow):
        result = _format_status(sample_workflow, [])
        assert "recent_history" not in result

    def test_history_limited_to_10(self):
        data = {
            "id": "wf1",
            "name": "W",
            "status": "running",
            "nodes": [{"id": "n1", "name": "N1", "state": "running", "dependencies": []}],
        }
        history = [{"ts": f"2026-01-01T00:00:{i:02d}Z", "event": f"evt_{i}"} for i in range(15)]
        result = _format_status(data, history)

        assert len(result["recent_history"]) == 10

    def test_nodes_include_extracted(self, sample_workflow):
        result = _format_status(sample_workflow, [])
        # node_1 has extracted data
        node1 = next(n for n in result["nodes"] if n["id"] == "node_1")
        assert node1["extracted"] == {"peak_frequency": 5012.5}
        # node_3 has no extracted
        node3 = next(n for n in result["nodes"] if n["id"] == "node_3")
        assert node3["extracted"] is None

    def test_nodes_include_experiment_id(self):
        data = {
            "id": "wf1",
            "name": "W",
            "status": "completed",
            "nodes": [
                {
                    "id": "n1",
                    "name": "N1",
                    "state": "success",
                    "dependencies": [],
                    "experiment_id": "20260404_120000_qubit_spectroscopy",
                },
                {
                    "id": "n2",
                    "name": "N2",
                    "state": "success",
                    "dependencies": ["n1"],
                },
            ],
        }
        result = _format_status(data, [])
        node1 = next(n for n in result["nodes"] if n["id"] == "n1")
        assert node1["experiment_id"] == "20260404_120000_qubit_spectroscopy"
        node2 = next(n for n in result["nodes"] if n["id"] == "n2")
        assert node2["experiment_id"] is None
