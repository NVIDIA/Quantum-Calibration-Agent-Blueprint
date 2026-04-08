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

"""Unit tests for workflow tool update and log actions."""

import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.workflow_tool import _apply_changes


class TestApplyChanges:
    """Test the _apply_changes helper function."""

    def test_simple_key(self):
        data = {"status": "created"}
        result = _apply_changes(data, {"status": "running"})
        assert result["status"] == "running"

    def test_add_new_key(self):
        data = {"id": "test"}
        result = _apply_changes(data, {"name": "Test Workflow"})
        assert result["name"] == "Test Workflow"
        assert result["id"] == "test"

    def test_nested_dot_notation(self):
        data = {"context": {}}
        result = _apply_changes(data, {"context.resonator_freq": 5.823})
        assert result["context"]["resonator_freq"] == 5.823

    def test_nested_creates_intermediate(self):
        data = {"id": "test"}
        result = _apply_changes(data, {"context.value": 123})
        assert result["context"]["value"] == 123

    def test_node_dot_notation(self):
        data = {
            "nodes": [
                {"id": "node_1", "state": "pending"},
                {"id": "node_2", "state": "pending"}
            ]
        }
        result = _apply_changes(data, {"nodes.node_1.state": "running"})
        assert result["nodes"][0]["state"] == "running"
        assert result["nodes"][1]["state"] == "pending"

    def test_node_extracted(self):
        data = {
            "nodes": [{"id": "node_1", "state": "running"}]
        }
        result = _apply_changes(data, {
            "nodes.node_1.state": "success",
            "nodes.node_1.extracted": {"frequency": 5.0}
        })
        assert result["nodes"][0]["state"] == "success"
        assert result["nodes"][0]["extracted"]["frequency"] == 5.0

    def test_multiple_changes(self):
        data = {"status": "created", "context": {}}
        result = _apply_changes(data, {
            "status": "running",
            "started_at": "2024-01-01T00:00:00Z",
            "context.value": 123
        })
        assert result["status"] == "running"
        assert result["started_at"] == "2024-01-01T00:00:00Z"
        assert result["context"]["value"] == 123

    def test_nonexistent_node_ignored(self):
        data = {
            "nodes": [{"id": "node_1", "state": "pending"}]
        }
        result = _apply_changes(data, {"nodes.node_999.state": "running"})
        # Should not crash, original data unchanged
        assert result["nodes"][0]["state"] == "pending"

    def test_original_not_modified(self):
        data = {"status": "created"}
        result = _apply_changes(data, {"status": "running"})
        assert data["status"] == "created"
        assert result["status"] == "running"


class TestWorkflowUpdate:
    """Test the workflow update action."""

    @pytest.fixture
    def temp_workflows_dir(self, tmp_path, monkeypatch):
        """Create temporary workflows directory."""
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", workflows_dir)
        return workflows_dir

    def test_create_new_workflow(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        result = workflow.func(
            action="update",
            workflow_id="test_workflow",
            data={
                "name": "Test Workflow",
                "status": "created",
                "nodes": [
                    {"id": "node_1", "name": "First Node", "dependencies": []}
                ]
            }
        )

        assert result.get("success") is True
        assert result.get("created") is True

        wf_file = temp_workflows_dir / "test_workflow" / "workflow.json"
        assert wf_file.exists()

        data = json.loads(wf_file.read_text())
        assert data["name"] == "Test Workflow"
        assert data["status"] == "created"
        assert len(data["nodes"]) == 1

    def test_update_existing_workflow(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        # Create initial workflow
        wf_dir = temp_workflows_dir / "test_workflow"
        wf_dir.mkdir()
        wf_file = wf_dir / "workflow.json"
        wf_file.write_text(json.dumps({
            "id": "test_workflow",
            "name": "Test",
            "status": "created",
            "nodes": [{"id": "node_1", "name": "Node 1", "state": "pending", "dependencies": []}]
        }))

        # Update it
        result = workflow.func(
            action="update",
            workflow_id="test_workflow",
            data={"status": "running", "nodes.node_1.state": "running"}
        )

        assert result.get("success") is True
        assert result.get("created") is False

        data = json.loads(wf_file.read_text())
        assert data["status"] == "running"
        assert data["nodes"][0]["state"] == "running"

    def test_validation_failure_reverts(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        # Create valid workflow
        wf_dir = temp_workflows_dir / "test_workflow"
        wf_dir.mkdir()
        wf_file = wf_dir / "workflow.json"
        original = {
            "id": "test_workflow",
            "name": "Test",
            "status": "created",
            "nodes": [{"id": "node_1", "name": "Node 1", "dependencies": []}]
        }
        wf_file.write_text(json.dumps(original))

        # Try invalid update (empty nodes)
        result = workflow.func(
            action="update",
            workflow_id="test_workflow",
            data={"nodes": []}
        )

        assert "error" in result

        # Original should be preserved
        data = json.loads(wf_file.read_text())
        assert len(data["nodes"]) == 1

    def test_invalid_node_reference_fails(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        result = workflow.func(
            action="update",
            workflow_id="test_workflow",
            data={
                "name": "Test",
                "nodes": [
                    {"id": "node_1", "name": "Node 1", "dependencies": ["nonexistent"]}
                ]
            }
        )

        assert "error" in result

    def test_missing_workflow_id(self):
        from tools.workflow_tool import workflow

        result = workflow.func(action="update", data={"name": "Test"})
        assert "error" in result
        assert "workflow_id" in result["error"]

    def test_missing_data(self):
        from tools.workflow_tool import workflow

        result = workflow.func(action="update", workflow_id="test")
        assert "error" in result
        assert "data" in result["error"]

    def test_update_with_context(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        # Create workflow
        workflow.func(
            action="update",
            workflow_id="test_workflow",
            data={
                "name": "Test",
                "status": "created",
                "context": {},
                "nodes": [{"id": "node_1", "name": "Node 1", "dependencies": []}]
            }
        )

        # Update context
        result = workflow.func(
            action="update",
            workflow_id="test_workflow",
            data={
                "context.resonator_freq": 5.823,
                "context.qubit_freq": 4.5
            }
        )

        assert result.get("success") is True

        wf_file = temp_workflows_dir / "test_workflow" / "workflow.json"
        data = json.loads(wf_file.read_text())
        assert data["context"]["resonator_freq"] == 5.823
        assert data["context"]["qubit_freq"] == 4.5


class TestWorkflowLog:
    """Test the workflow log action."""

    @pytest.fixture
    def temp_workflows_dir(self, tmp_path, monkeypatch):
        """Create temporary workflows directory with a workflow."""
        workflows_dir = tmp_path / "workflows"
        wf_dir = workflows_dir / "test_workflow"
        wf_dir.mkdir(parents=True)
        (wf_dir / "workflow.json").write_text(json.dumps({
            "id": "test_workflow",
            "name": "Test",
            "nodes": [{"id": "node_1", "name": "Node 1", "dependencies": []}]
        }))
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", workflows_dir)
        return workflows_dir

    def test_log_event(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        result = workflow.func(
            action="log",
            workflow_id="test_workflow",
            event="node_started",
            node="node_1",
            run=1
        )

        assert result.get("success") is True
        assert result["logged"]["event"] == "node_started"
        assert "ts" in result["logged"]

        history_file = temp_workflows_dir / "test_workflow" / "history.jsonl"
        assert history_file.exists()

        lines = history_file.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["event"] == "node_started"
        assert entry["node"] == "node_1"
        assert entry["run"] == 1

    def test_log_multiple_events(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        workflow.func(action="log", workflow_id="test_workflow", event="workflow_started")
        workflow.func(action="log", workflow_id="test_workflow", event="node_started", node="node_1")
        workflow.func(action="log", workflow_id="test_workflow", event="node_completed", node="node_1", state="success")

        history_file = temp_workflows_dir / "test_workflow" / "history.jsonl"
        lines = history_file.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_log_nonexistent_workflow(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        result = workflow.func(
            action="log",
            workflow_id="nonexistent",
            event="test"
        )
        assert "error" in result

    def test_log_missing_event(self, temp_workflows_dir):
        from tools.workflow_tool import workflow

        result = workflow.func(action="log", workflow_id="test_workflow")
        assert "error" in result
        assert "event" in result["error"]


class TestWorkflowIntegration:
    """Integration tests for workflow execution flow."""

    @pytest.fixture
    def temp_workflows_dir(self, tmp_path, monkeypatch):
        workflows_dir = tmp_path / "workflows"
        workflows_dir.mkdir()
        monkeypatch.setattr("tools.workflow_tool.WORKFLOWS_DIR", workflows_dir)
        return workflows_dir

    def test_full_workflow_execution(self, temp_workflows_dir):
        """Test a complete workflow execution cycle."""
        from tools.workflow_tool import workflow

        # 1. Create workflow
        result = workflow.func(
            action="update",
            workflow_id="calibration",
            data={
                "name": "Qubit Calibration",
                "status": "created",
                "context": {},
                "nodes": [
                    {"id": "node_1", "name": "Resonator", "state": "pending", "dependencies": []},
                    {"id": "node_2", "name": "Qubit", "state": "pending", "dependencies": ["node_1"]}
                ]
            }
        )
        assert result.get("success") is True

        # 2. Start workflow
        workflow.func(action="update", workflow_id="calibration", data={
            "status": "running",
            "started_at": "2024-01-01T00:00:00Z"
        })
        workflow.func(action="log", workflow_id="calibration", event="workflow_started")

        # 3. Start node_1
        workflow.func(action="update", workflow_id="calibration", data={
            "current_node": "node_1",
            "nodes.node_1.state": "running",
            "nodes.node_1.run_count": 1
        })
        workflow.func(action="log", workflow_id="calibration", event="node_started", node="node_1")

        # 4. Complete node_1 successfully
        workflow.func(action="update", workflow_id="calibration", data={
            "nodes.node_1.state": "success",
            "nodes.node_1.extracted": {"resonator_freq": 5.823},
            "context.resonator_freq": 5.823
        })
        workflow.func(action="log", workflow_id="calibration", event="node_completed", node="node_1", state="success")

        # 5. Start node_2
        workflow.func(action="update", workflow_id="calibration", data={
            "current_node": "node_2",
            "nodes.node_2.state": "running",
            "nodes.node_2.run_count": 1
        })

        # 6. Complete node_2
        workflow.func(action="update", workflow_id="calibration", data={
            "nodes.node_2.state": "success",
            "nodes.node_2.extracted": {"qubit_freq": 4.5}
        })

        # 7. Complete workflow
        workflow.func(action="update", workflow_id="calibration", data={
            "status": "completed",
            "current_node": None
        })

        # Verify final state
        wf_file = temp_workflows_dir / "calibration" / "workflow.json"
        data = json.loads(wf_file.read_text())

        assert data["status"] == "completed"
        assert data["nodes"][0]["state"] == "success"
        assert data["nodes"][1]["state"] == "success"
        assert data["context"]["resonator_freq"] == 5.823

        # Verify history
        history_file = temp_workflows_dir / "calibration" / "history.jsonl"
        lines = history_file.read_text().strip().split("\n")
        assert len(lines) >= 3

    def test_workflow_pause_and_resume(self, temp_workflows_dir):
        """Test pausing and resuming a workflow."""
        from tools.workflow_tool import workflow

        # Create and start workflow
        workflow.func(
            action="update",
            workflow_id="test",
            data={
                "name": "Test",
                "status": "running",
                "nodes": [{"id": "node_1", "name": "Node 1", "state": "failed", "dependencies": []}]
            }
        )

        # Pause
        workflow.func(action="update", workflow_id="test", data={
            "status": "paused",
            "paused_reason": "Node failed, need human decision",
            "suggestions": [{"action": "retry"}, {"action": "skip"}]
        })

        wf_file = temp_workflows_dir / "test" / "workflow.json"
        data = json.loads(wf_file.read_text())
        assert data["status"] == "paused"
        assert data["paused_reason"] == "Node failed, need human decision"

        # Resume
        workflow.func(action="update", workflow_id="test", data={
            "status": "running",
            "paused_reason": None,
            "suggestions": None,
            "nodes.node_1.state": "pending"
        })

        data = json.loads(wf_file.read_text())
        assert data["status"] == "running"
        assert data["nodes"][0]["state"] == "pending"
