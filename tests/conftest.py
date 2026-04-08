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

"""Pytest fixtures for QCA CLI tests."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.models import ExperimentResult
from core.storage import save_experiment


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory with workflow structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        workflows_dir = data_dir / "workflows"
        workflows_dir.mkdir(parents=True)
        yield data_dir


@pytest.fixture
def sample_workflow():
    """Return a sample workflow definition."""
    return {
        "id": "test_workflow_001",
        "name": "Test Workflow",
        "description": "A test workflow for unit tests",
        "status": "running",
        "created": "2026-03-22T10:00:00Z",
        "nodes": [
            {
                "id": "node_1",
                "name": "First Node",
                "experiment": "qubit_spectroscopy",
                "state": "success",
                "dependencies": [],
                "run_count": 1,
                "extracted": {"peak_frequency": 5012.5},
            },
            {
                "id": "node_2",
                "name": "Second Node",
                "experiment": "qubit_spectroscopy",
                "state": "running",
                "dependencies": ["node_1"],
                "run_count": 1,
            },
            {
                "id": "node_3",
                "name": "Third Node",
                "experiment": "qubit_spectroscopy",
                "state": "pending",
                "dependencies": ["node_2"],
            },
        ],
        "global_params": {"max_retries": 3, "timeout": 300},
        "completion_criteria": {"primary": "node_3.success"},
    }


@pytest.fixture
def sample_history():
    """Return sample workflow history events."""
    return [
        {"ts": "2026-03-22T10:00:00Z", "event": "workflow_started"},
        {
            "ts": "2026-03-22T10:00:01Z",
            "event": "node_started",
            "node": "node_1",
            "run": 1,
        },
        {
            "ts": "2026-03-22T10:01:00Z",
            "event": "node_completed",
            "node": "node_1",
            "state": "success",
        },
        {
            "ts": "2026-03-22T10:01:05Z",
            "event": "node_started",
            "node": "node_2",
            "run": 1,
        },
    ]


@pytest.fixture
def workflow_dir(temp_data_dir, sample_workflow, sample_history):
    """Create a workflow directory with workflow.json and history.jsonl."""
    workflow_id = sample_workflow["id"]
    wf_dir = temp_data_dir / "workflows" / workflow_id
    wf_dir.mkdir(parents=True)

    # Write workflow.json
    with open(wf_dir / "workflow.json", "w") as f:
        json.dump(sample_workflow, f)

    # Write history.jsonl
    with open(wf_dir / "history.jsonl", "w") as f:
        for event in sample_history:
            f.write(json.dumps(event) + "\n")

    return temp_data_dir


@pytest.fixture
def invalid_workflow():
    """Return an invalid workflow with issues."""
    return {
        "id": "invalid_workflow",
        "name": "Invalid Workflow",
        "nodes": [
            {
                "id": "node_a",
                "name": "Node A",
                "dependencies": ["node_b"],  # node_b doesn't exist
            },
            {
                # Missing 'id' field
                "name": "Node without ID"
            },
        ],
    }


@pytest.fixture
def circular_workflow():
    """Return a workflow with circular dependencies."""
    return {
        "id": "circular_workflow",
        "name": "Circular Workflow",
        "nodes": [
            {"id": "node_a", "name": "Node A", "dependencies": ["node_c"]},
            {"id": "node_b", "name": "Node B", "dependencies": ["node_a"]},
            {"id": "node_c", "name": "Node C", "dependencies": ["node_b"]},
        ],
    }


@pytest.fixture
def completed_workflow():
    """Return a completed workflow."""
    return {
        "id": "completed_workflow",
        "name": "Completed Workflow",
        "status": "completed",
        "created": "2026-03-22T09:00:00Z",
        "nodes": [
            {
                "id": "node_1",
                "name": "Only Node",
                "state": "success",
                "dependencies": [],
                "extracted": {"result": 42},
            }
        ],
    }


@pytest.fixture
def paused_workflow():
    """Return a paused workflow with suggestions."""
    return {
        "id": "paused_workflow",
        "name": "Paused Workflow",
        "status": "paused",
        "created": "2026-03-22T08:00:00Z",
        "paused_at": "2026-03-22T08:30:00Z",
        "paused_reason": "Node failed after max retries",
        "suggestions": [
            {"action": "retry", "reason": "Try with different parameters"},
            {"action": "skip", "reason": "Skip this node and continue"},
        ],
        "nodes": [
            {
                "id": "node_1",
                "name": "Failed Node",
                "state": "failed",
                "dependencies": [],
                "run_count": 3,
            }
        ],
    }


# =============================================================================
# Experiment Fixtures (Task 1.3)
# =============================================================================


@pytest.fixture
def sample_experiment_result():
    """Sample ExperimentResult for testing."""
    return ExperimentResult(
        id="20260322_100000_qubit_spectroscopy",
        type="qubit_spectroscopy",
        timestamp="2026-03-22T10:00:00Z",
        status="success",
        target="qubit_0",
        params={"center_freq": 4.8, "span": 0.2, "num_points": 101},
        results={"qubit_freq": {"value": 4.85, "unit": "GHz"}},
        arrays={"frequencies": [4.7, 4.75, 4.8, 4.85, 4.9]},
        plots=[
            {
                "name": "spectrum",
                "format": "plotly",
                "data": {
                    "data": [
                        {
                            "x": [4.7, 4.75, 4.8, 4.85, 4.9],
                            "y": [0.1, 0.2, 0.8, 0.3, 0.1],
                        }
                    ],
                    "layout": {"title": "Qubit Spectroscopy"},
                },
            }
        ],
    )


@pytest.fixture
def temp_scripts_dir(tmp_path):
    """Create temp directory with mock experiment scripts."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    # Create minimal valid script
    (scripts_dir / "test_experiment.py").write_text(
        '''
from typing import Annotated

def test_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Test experiment."""
    return {"status": "success", "data": {"result": param1 * 2}}
'''
    )
    return scripts_dir


@pytest.fixture
def temp_data_dir_with_experiments(temp_data_dir, sample_experiment_result):
    """Create data dir with saved experiments."""
    # Ensure experiments directory exists
    experiments_dir = temp_data_dir / "experiments"
    experiments_dir.mkdir(parents=True, exist_ok=True)
    save_experiment(sample_experiment_result, temp_data_dir)
    return temp_data_dir
