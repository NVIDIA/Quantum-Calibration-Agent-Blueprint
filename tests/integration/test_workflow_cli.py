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

"""Tests for workflow CLI commands."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add parent directory to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli import (
    count_node_states,
    list_all_workflows,
    load_workflow,
    load_workflow_history,
    validate_workflow_structure,
)

# CLI path for E2E tests
CLI_PATH = PROJECT_ROOT / "cli.py"


# =============================================================================
# Unit Tests for Helper Functions
# =============================================================================


class TestLoadWorkflow:
    """Tests for load_workflow function."""

    def test_load_existing_workflow(self, workflow_dir, sample_workflow):
        """Load an existing workflow successfully."""
        with patch("cli.get_data_dir", return_value=workflow_dir):
            result = load_workflow(sample_workflow["id"])
            assert result is not None
            assert result["id"] == sample_workflow["id"]
            assert result["name"] == sample_workflow["name"]
            assert len(result["nodes"]) == 3

    def test_load_nonexistent_workflow(self, temp_data_dir):
        """Return None for nonexistent workflow."""
        with patch("cli.get_data_dir", return_value=temp_data_dir):
            result = load_workflow("nonexistent_workflow")
            assert result is None


class TestLoadWorkflowHistory:
    """Tests for load_workflow_history function."""

    def test_load_existing_history(self, workflow_dir, sample_workflow, sample_history):
        """Load existing workflow history."""
        with patch("cli.get_data_dir", return_value=workflow_dir):
            events = load_workflow_history(sample_workflow["id"])
            assert len(events) == len(sample_history)
            assert events[0]["event"] == "workflow_started"

    def test_load_nonexistent_history(self, temp_data_dir):
        """Return empty list for nonexistent history."""
        with patch("cli.get_data_dir", return_value=temp_data_dir):
            events = load_workflow_history("nonexistent_workflow")
            assert events == []


class TestListAllWorkflows:
    """Tests for list_all_workflows function."""

    def test_list_workflows(self, workflow_dir, sample_workflow):
        """List all workflows."""
        with patch("cli.get_data_dir", return_value=workflow_dir):
            workflows = list_all_workflows()
            assert len(workflows) == 1
            assert workflows[0]["id"] == sample_workflow["id"]
            assert workflows[0]["status"] == "running"
            assert workflows[0]["node_count"] == 3

    def test_list_empty_directory(self, temp_data_dir):
        """Return empty list for empty directory."""
        with patch("cli.get_data_dir", return_value=temp_data_dir):
            workflows = list_all_workflows()
            assert workflows == []

    def test_list_multiple_workflows(
        self, temp_data_dir, sample_workflow, completed_workflow
    ):
        """List multiple workflows sorted by created date."""
        workflows_dir = temp_data_dir / "workflows"

        # Create first workflow
        wf1_dir = workflows_dir / sample_workflow["id"]
        wf1_dir.mkdir(parents=True)
        with open(wf1_dir / "workflow.json", "w") as f:
            json.dump(sample_workflow, f)

        # Create second workflow
        wf2_dir = workflows_dir / completed_workflow["id"]
        wf2_dir.mkdir(parents=True)
        with open(wf2_dir / "workflow.json", "w") as f:
            json.dump(completed_workflow, f)

        with patch("cli.get_data_dir", return_value=temp_data_dir):
            workflows = list_all_workflows()
            assert len(workflows) == 2
            # Should be sorted by created date (newest first)
            assert workflows[0]["id"] == sample_workflow["id"]  # 10:00:00
            assert workflows[1]["id"] == completed_workflow["id"]  # 09:00:00


class TestCountNodeStates:
    """Tests for count_node_states function."""

    def test_count_states(self, sample_workflow):
        """Count nodes in each state."""
        counts = count_node_states(sample_workflow)
        assert counts["success"] == 1
        assert counts["running"] == 1
        assert counts["pending"] == 1
        assert counts["failed"] == 0
        assert counts["skipped"] == 0

    def test_count_empty_workflow(self):
        """Count states for workflow with no nodes."""
        workflow = {"nodes": []}
        counts = count_node_states(workflow)
        assert counts["success"] == 0
        assert counts["running"] == 0
        assert counts["pending"] == 0


class TestValidateWorkflowStructure:
    """Tests for validate_workflow_structure function."""

    def test_valid_workflow(self, sample_workflow):
        """Valid workflow has no issues."""
        issues = validate_workflow_structure(sample_workflow)
        assert len(issues) == 0

    def test_missing_id(self):
        """Detect missing workflow ID."""
        workflow = {"nodes": []}
        issues = validate_workflow_structure(workflow)
        assert any("Missing required field: id" in issue for issue in issues)

    def test_missing_nodes(self):
        """Detect missing nodes field."""
        workflow = {"id": "test"}
        issues = validate_workflow_structure(workflow)
        assert any("Missing required field: nodes" in issue for issue in issues)

    def test_missing_node_id(self, invalid_workflow):
        """Detect missing node ID."""
        issues = validate_workflow_structure(invalid_workflow)
        assert any("Missing 'id' field" in issue for issue in issues)

    def test_missing_dependency(self, invalid_workflow):
        """Detect missing dependency."""
        issues = validate_workflow_structure(invalid_workflow)
        assert any("Dependency 'node_b' not found" in issue for issue in issues)

    def test_circular_dependency(self, circular_workflow):
        """Detect circular dependencies."""
        issues = validate_workflow_structure(circular_workflow)
        assert any("Circular dependency" in issue for issue in issues)


# =============================================================================
# E2E Tests for CLI Commands
# =============================================================================


class TestWorkflowListCommand:
    """E2E tests for 'workflow list' command."""

    def test_list_json_output(self, workflow_dir, sample_workflow):
        """Test JSON output format."""
        result = subprocess.run(
            [sys.executable, str(CLI_PATH), "workflow", "list"],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "workflows" in output
        assert len(output["workflows"]) == 1
        assert output["workflows"][0]["id"] == sample_workflow["id"]

    def test_list_human_output(self, workflow_dir):
        """Test human-readable output format."""
        result = subprocess.run(
            [sys.executable, str(CLI_PATH), "workflow", "list", "--human"],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        assert "Workflows" in result.stdout
        assert "test_workflow_001" in result.stdout

    def test_list_empty(self, temp_data_dir):
        """Test listing with no workflows."""
        result = subprocess.run(
            [sys.executable, str(CLI_PATH), "workflow", "list", "--human"],
            capture_output=True,
            text=True,
            cwd=str(temp_data_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(temp_data_dir)},
        )
        assert result.returncode == 0
        assert "No workflows found" in result.stdout


class TestWorkflowShowCommand:
    """E2E tests for 'workflow show' command."""

    def test_show_json_output(self, workflow_dir, sample_workflow):
        """Test JSON output format."""
        result = subprocess.run(
            [sys.executable, str(CLI_PATH), "workflow", "show", sample_workflow["id"]],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["id"] == sample_workflow["id"]
        assert output["name"] == sample_workflow["name"]
        assert len(output["nodes"]) == 3

    def test_show_human_output(self, workflow_dir, sample_workflow):
        """Test human-readable output format."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "show",
                sample_workflow["id"],
                "--human",
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        assert sample_workflow["name"] in result.stdout
        assert "Nodes:" in result.stdout

    def test_show_nonexistent(self, temp_data_dir):
        """Test showing nonexistent workflow."""
        result = subprocess.run(
            [sys.executable, str(CLI_PATH), "workflow", "show", "nonexistent"],
            capture_output=True,
            text=True,
            cwd=str(temp_data_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(temp_data_dir)},
        )
        assert result.returncode == 1
        assert "not found" in result.stdout


class TestWorkflowStatusCommand:
    """E2E tests for 'workflow status' command."""

    def test_status_json_output(self, workflow_dir, sample_workflow):
        """Test JSON output format."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "status",
                sample_workflow["id"],
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["id"] == sample_workflow["id"]
        assert output["status"] == "running"
        assert output["nodes_total"] == 3
        assert output["nodes_completed"] == 1  # 1 success

    def test_status_human_output(self, workflow_dir, sample_workflow):
        """Test human-readable output with progress bar."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "status",
                sample_workflow["id"],
                "--human",
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        assert "RUNNING" in result.stdout
        assert "Progress:" in result.stdout


class TestWorkflowValidateCommand:
    """E2E tests for 'workflow validate' command."""

    def test_validate_valid_workflow(self, workflow_dir, sample_workflow):
        """Test validating a valid workflow."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "validate",
                sample_workflow["id"],
                "--human",
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        assert "is valid" in result.stdout

    def test_validate_invalid_workflow(self, temp_data_dir, invalid_workflow):
        """Test validating an invalid workflow."""
        # Create invalid workflow
        wf_dir = temp_data_dir / "workflows" / invalid_workflow["id"]
        wf_dir.mkdir(parents=True)
        with open(wf_dir / "workflow.json", "w") as f:
            json.dump(invalid_workflow, f)

        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "validate",
                invalid_workflow["id"],
                "--human",
            ],
            capture_output=True,
            text=True,
            cwd=str(temp_data_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(temp_data_dir)},
        )
        assert result.returncode == 1
        assert "issue" in result.stdout

    def test_validate_json_output(self, workflow_dir, sample_workflow):
        """Test JSON output format."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "validate",
                sample_workflow["id"],
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["valid"] is True
        assert output["issues"] == []


class TestWorkflowHistoryCommand:
    """E2E tests for 'workflow history' command."""

    def test_history_json_output(self, workflow_dir, sample_workflow, sample_history):
        """Test JSON output format."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "history",
                sample_workflow["id"],
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "events" in output
        assert len(output["events"]) == len(sample_history)

    def test_history_last_n(self, workflow_dir, sample_workflow):
        """Test --last option."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "history",
                sample_workflow["id"],
                "--last",
                "2",
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert len(output["events"]) == 2

    def test_history_human_output(self, workflow_dir, sample_workflow):
        """Test human-readable output format."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "history",
                sample_workflow["id"],
                "--human",
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        assert "History" in result.stdout
        assert "workflow_started" in result.stdout


class TestWorkflowNodesCommand:
    """E2E tests for 'workflow nodes' command."""

    def test_nodes_json_output(self, workflow_dir, sample_workflow):
        """Test JSON output format."""
        result = subprocess.run(
            [sys.executable, str(CLI_PATH), "workflow", "nodes", sample_workflow["id"]],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert "nodes" in output
        assert len(output["nodes"]) == 3

    def test_nodes_human_output(self, workflow_dir, sample_workflow):
        """Test human-readable output format."""
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "nodes",
                sample_workflow["id"],
                "--human",
            ],
            capture_output=True,
            text=True,
            cwd=str(workflow_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(workflow_dir)},
        )
        assert result.returncode == 0
        assert "Nodes" in result.stdout
        assert "node_1" in result.stdout
        assert "success" in result.stdout
        assert "Extracted Values" in result.stdout


class TestWorkflowPausedStatus:
    """Tests for paused workflow status display."""

    def test_paused_status_shows_suggestions(self, temp_data_dir, paused_workflow):
        """Test that paused workflow shows suggestions."""
        # Create paused workflow
        wf_dir = temp_data_dir / "workflows" / paused_workflow["id"]
        wf_dir.mkdir(parents=True)
        with open(wf_dir / "workflow.json", "w") as f:
            json.dump(paused_workflow, f)

        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "status",
                paused_workflow["id"],
                "--human",
            ],
            capture_output=True,
            text=True,
            cwd=str(temp_data_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(temp_data_dir)},
        )
        assert result.returncode == 0
        assert "PAUSED" in result.stdout
        assert "Paused Reason" in result.stdout
        assert "Suggestions" in result.stdout


class TestWorkflowCompletedStatus:
    """Tests for completed workflow status display."""

    def test_completed_status(self, temp_data_dir, completed_workflow):
        """Test completed workflow status."""
        # Create completed workflow
        wf_dir = temp_data_dir / "workflows" / completed_workflow["id"]
        wf_dir.mkdir(parents=True)
        with open(wf_dir / "workflow.json", "w") as f:
            json.dump(completed_workflow, f)

        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "workflow",
                "status",
                completed_workflow["id"],
            ],
            capture_output=True,
            text=True,
            cwd=str(temp_data_dir.parent),
            env={**subprocess.os.environ, "QCAL_DATA_DIR": str(temp_data_dir)},
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "completed"
        assert output["progress"] == 100.0
        assert output["nodes_completed"] == 1
