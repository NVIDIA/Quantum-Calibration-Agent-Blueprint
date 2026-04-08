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

"""Lab tool for deep agent - experiment management API."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

# Import core modules
ROOT_DIR = Path(__file__).parent.parent
from core import discovery, runner, storage
from core.models import ExperimentResult

# Paths
SCRIPTS_DIR = ROOT_DIR / "scripts"
DATA_DIR = ROOT_DIR / "data" / "experiments"


@tool
def lab(
    action: str,
    experiment_name: str = None,
    experiment_id: str = None,
    array_name: str = None,
    slice_start: int = None,
    slice_end: int = None,
    last_n: int = None,
    filter_type: str = None,
) -> dict[str, Any]:
    """Quantum calibration query tool. Get experiment info, history, and data.

    Actions:
    - info: Get full documentation including all experiments and their parameters (START HERE)
    - schema: Get detailed schema for a specific experiment (needs experiment_name)
    - history_list: List past experiments (optional: last_n)
    - history_show: Get experiment details (needs experiment_id)
    - list_arrays: List available arrays in an experiment (needs experiment_id)
    - get_array: Get array data (needs experiment_id, array_name)
    - get_stats: Get array statistics (needs experiment_id, array_name)

    To run experiments, use the run_experiment tool instead.
    """
    try:
        if action == "info":
            return _get_info()
        elif action == "list_experiments":
            return _list_experiments()
        elif action == "schema":
            return _get_schema(experiment_name)
        elif action == "history_list":
            return _history_list(last_n, filter_type)
        elif action == "history_show":
            return _history_show(experiment_id)
        elif action == "list_arrays":
            return _list_arrays(experiment_id)
        elif action == "get_array":
            return _get_array(experiment_id, array_name, slice_start, slice_end)
        elif action == "get_stats":
            return _get_stats(experiment_id, array_name)
        elif action == "run":
            return {"error": "Use the run_experiment tool to execute experiments"}
        else:
            return {
                "error": f"Unknown action: {action}",
                "valid_actions": [
                    "info",
                    "schema",
                    "history_list",
                    "history_show",
                    "list_arrays",
                    "get_array",
                    "get_stats",
                ],
            }
    except Exception as e:
        return {"error": str(e)}


@tool
def run_experiment(
    experiment_name: str,
    params: dict = None,
    notes: str = "",
    python_path: str = None,
) -> dict[str, Any]:
    """Execute a quantum calibration experiment. Requires approval before running.

    Args:
        experiment_name: Name of the experiment to run (use lab action='info' to see available)
        params: Dictionary of experiment parameters
        notes: Optional notes to attach to the experiment run
        python_path: Path to Python interpreter to use (e.g., '/path/to/venv/bin/python').
                     If not specified, uses system 'python'. Check skills/memory for the
                     correct Python environment for your experiments.

    Returns experiment results including ID, status, and any generated data arrays.
    """
    return _run_experiment(experiment_name, params, notes, python_path)


def _get_info() -> dict:
    """Get comprehensive info: all experiments with full parameter schemas."""
    experiments = discovery.discover_experiments(SCRIPTS_DIR)

    experiment_docs = []
    for exp in experiments:
        params = []
        for p in exp.parameters:
            param_doc = {
                "name": p.name,
                "type": p.type,
                "default": p.default,
            }
            if p.range:
                param_doc["range"] = f"{p.range[0]} to {p.range[1]}"
            if p.required:
                param_doc["required"] = True
            params.append(param_doc)

        experiment_docs.append(
            {
                "name": exp.name,
                "description": exp.description,
                "parameters": params,
            }
        )

    return {
        "experiments": experiment_docs,
        "usage": {
            "run_experiment": "run_experiment(experiment_name='NAME', params={...})",
            "view_history": "lab(action='history_list', last_n=10)",
            "get_results": "lab(action='history_show', experiment_id='ID')",
            "get_data": "lab(action='get_array', experiment_id='ID', array_name='NAME')",
        },
    }


def _list_experiments() -> dict:
    """List all available experiments."""
    experiments = discovery.discover_experiments(SCRIPTS_DIR)
    return {
        "experiments": [
            {
                "name": exp.name,
                "description": exp.description,
                "parameter_count": len(exp.parameters),
            }
            for exp in experiments
        ]
    }


def _get_schema(experiment_name: str) -> dict:
    """Get schema for a specific experiment."""
    if not experiment_name:
        return {"error": "experiment_name is required for schema action"}

    schema = discovery.get_experiment_schema(experiment_name, SCRIPTS_DIR)
    if not schema:
        # List available experiments in error message
        available = discovery.discover_experiments(SCRIPTS_DIR)
        return {
            "error": f"Experiment '{experiment_name}' not found",
            "available_experiments": [e.name for e in available],
        }

    return {
        "name": schema.name,
        "description": schema.description,
        "module_path": schema.module_path,
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "required": p.required,
                "default": p.default,
                "range": list(p.range) if p.range else None,
            }
            for p in schema.parameters
        ],
    }


def _run_experiment(
    experiment_name: str, params: dict, notes: str = "", python_path: str = None
) -> dict:
    """Run an experiment and store results."""
    if not experiment_name:
        return {"error": "experiment_name is required for run action"}
    if params is None:
        params = {}

    # Validate experiment exists
    schema = discovery.get_experiment_schema(experiment_name, SCRIPTS_DIR)
    if not schema:
        available = discovery.discover_experiments(SCRIPTS_DIR)
        return {
            "error": f"Experiment '{experiment_name}' not found",
            "available_experiments": [e.name for e in available],
        }

    # Generate experiment ID and timestamp BEFORE running
    # This allows real-time log file access during execution
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat().replace("+00:00", "Z")
    exp_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{experiment_name}"

    # Create experiment directory and log file path
    exp_dir = DATA_DIR / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    log_file = exp_dir / "output.log"

    # Run experiment with real-time logging
    try:
        result_dict = runner.run_experiment(
            experiment_name,
            params,
            SCRIPTS_DIR,
            python_path=python_path,
            log_file=log_file,
        )
    except ValueError as e:
        # Parameter validation error - provide helpful info
        return {
            "error": str(e),
            "hint": f"Call lab(action='schema', experiment_name='{experiment_name}') to see valid parameters",
        }
    except TimeoutError as e:
        return {"error": f"Experiment timed out: {e}", "id": exp_id}
    except RuntimeError as e:
        return {"error": f"Experiment failed: {e}", "id": exp_id}

    # Extract target from params
    target = params.get("target")

    # Create ExperimentResult
    # Scripts return "data" but we store it as "results"
    results_data = result_dict.get("results") or result_dict.get("data", {})
    experiment_result = ExperimentResult(
        id=exp_id,
        type=experiment_name,
        timestamp=timestamp,
        status=result_dict["status"],
        target=target,
        params=params,
        results=results_data,
        arrays=result_dict.get("arrays", {}),
        plots=result_dict.get("plots", []),
        notes=notes,
    )

    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Store results
    storage.save_experiment(experiment_result, DATA_DIR)

    # Return summary
    return {
        "id": exp_id,
        "status": result_dict["status"],
        "timestamp": timestamp,
        "results": results_data,
        "arrays": list(result_dict.get("arrays", {}).keys()),
        "plots": [p["name"] for p in result_dict.get("plots", [])],
        "error": (
            result_dict.get("error") if result_dict["status"] == "failed" else None
        ),
    }


def _history_list(last_n: int = None, filter_type: str = None) -> dict:
    """List past experiments."""
    experiments = storage.search_experiments(DATA_DIR, type=filter_type, last=last_n)
    return {
        "count": len(experiments),
        "experiments": [
            {
                "id": exp["id"],
                "type": exp["type"],
                "target": exp.get("target"),
                "timestamp": exp["timestamp"],
                "status": exp["status"],
            }
            for exp in experiments
        ],
    }


def _history_show(experiment_id: str) -> dict:
    """Get full details of an experiment."""
    if not experiment_id:
        return {"error": "experiment_id is required for history_show action"}

    experiment = storage.load_experiment(experiment_id, DATA_DIR)
    if not experiment:
        return {"error": f"Experiment '{experiment_id}' not found"}

    return experiment.to_dict()


def _list_arrays(experiment_id: str) -> dict:
    """List arrays in an experiment."""
    if not experiment_id:
        return {"error": "experiment_id is required for list_arrays action"}

    arrays = storage.list_arrays(experiment_id, DATA_DIR)
    if arrays is None:
        return {"error": f"Experiment '{experiment_id}' not found"}

    return {"arrays": arrays}


def _get_array(
    experiment_id: str, array_name: str, slice_start: int = None, slice_end: int = None
) -> dict:
    """Get array data with optional slicing."""
    if not experiment_id:
        return {"error": "experiment_id is required for get_array action"}
    if not array_name:
        return {"error": "array_name is required for get_array action"}

    data = storage.get_array(
        experiment_id, array_name, DATA_DIR, start=slice_start, end=slice_end
    )
    if data is None:
        # Check if experiment exists
        arrays = storage.list_arrays(experiment_id, DATA_DIR)
        if arrays is None:
            return {"error": f"Experiment '{experiment_id}' not found"}
        return {
            "error": f"Array '{array_name}' not found in experiment",
            "available_arrays": [a["name"] for a in arrays],
        }

    return {
        "array": array_name,
        "data": data,
        "length": len(data),
        "slice": (
            f"{slice_start or 0}:{slice_end or len(data)}"
            if slice_start or slice_end
            else "full"
        ),
    }


def _get_stats(experiment_id: str, array_name: str) -> dict:
    """Get statistics for an array."""
    if not experiment_id:
        return {"error": "experiment_id is required for get_stats action"}
    if not array_name:
        return {"error": "array_name is required for get_stats action"}

    stats = storage.get_array_stats(experiment_id, array_name, DATA_DIR)
    if stats is None:
        arrays = storage.list_arrays(experiment_id, DATA_DIR)
        if arrays is None:
            return {"error": f"Experiment '{experiment_id}' not found"}
        return {
            "error": f"Array '{array_name}' not found in experiment",
            "available_arrays": [a["name"] for a in arrays],
        }

    return {"array": array_name, "stats": stats}
