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

"""Subprocess experiment execution."""

import json
import subprocess
from pathlib import Path
from typing import Optional

from .discovery import get_experiment_schema
from .models import ExperimentSchema, ParameterSpec


def validate_params(params: dict, schema: ExperimentSchema) -> list[str]:
    """Validate parameters against experiment schema.

    Args:
        params: Parameter dictionary to validate
        schema: Experiment schema with parameter specifications

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Build lookup for parameter specs
    param_specs = {p.name: p for p in schema.parameters}

    # Check for required parameters
    for param_spec in schema.parameters:
        if param_spec.required and param_spec.name not in params:
            errors.append(f"Missing required parameter: {param_spec.name}")

    # Validate provided parameters
    for param_name, param_value in params.items():
        # Check if parameter exists in schema
        if param_name not in param_specs:
            errors.append(f"Unknown parameter: {param_name}")
            continue

        spec = param_specs[param_name]

        # Check type (strict, no coercion)
        if not _check_type(param_value, spec.type):
            errors.append(
                f"Parameter {param_name} has wrong type. "
                f"Expected {spec.type}, got {type(param_value).__name__}"
            )
            continue

        # Check range for numeric types
        if spec.range and spec.type in ("int", "float"):
            min_val, max_val = spec.range
            if not (min_val <= param_value <= max_val):
                errors.append(
                    f"Parameter {param_name} out of range. "
                    f"Expected [{min_val}, {max_val}], got {param_value}"
                )

    return errors


def run_experiment(
    name: str,
    params: dict,
    scripts_dir: Path,
    timeout: int = 300,
    python_path: str = None,
    log_file: Path = None,
) -> dict:
    """Run an experiment in a subprocess.

    Args:
        name: Experiment name (function name)
        params: Parameters to pass to experiment
        scripts_dir: Directory containing experiment scripts
        timeout: Timeout in seconds (default 300)
        python_path: Path to Python interpreter (default: 'python')
        log_file: Optional path to write progress output (stderr) in real-time

    Returns:
        Result dictionary with status, results, arrays, plots, metadata

    Raises:
        ValueError: If experiment not found or validation fails
        RuntimeError: If subprocess execution fails
        TimeoutError: If experiment exceeds timeout
    """
    # Get experiment schema
    schema = get_experiment_schema(name, scripts_dir)
    if schema is None:
        raise ValueError(f"Experiment not found: {name}")

    # Validate parameters
    validation_errors = validate_params(params, schema)
    if validation_errors:
        raise ValueError(f"Parameter validation failed: {'; '.join(validation_errors)}")

    # Get module name from script path
    module_path = Path(schema.module_path)
    module_name = module_path.stem

    # Build subprocess command
    # Use Python code passed to -c that imports the function and calls it
    # Insert the parent of scripts_dir so relative imports within the package work
    scripts_parent = str(Path(scripts_dir).parent)
    package_name = Path(scripts_dir).name
    python_code = f"""
import sys, json
sys.path.insert(0, '{scripts_parent}')
from {package_name}.{module_name} import {name}
params = json.loads(sys.stdin.read())
result = {name}(**params)
print(json.dumps(result))
"""

    # Determine Python executable
    python_executable = python_path or "python"

    # Use Popen for real-time stderr streaming if log_file is provided
    if log_file is not None:
        return _run_with_logging(
            python_executable, python_code, params, timeout, log_file
        )

    # Fallback to subprocess.run for simple case (no logging)
    try:
        process = subprocess.run(
            [python_executable, "-c", python_code],
            input=json.dumps(params),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if process.returncode != 0:
            error_msg = process.stderr.strip() if process.stderr else "Unknown error"
            raise RuntimeError(f"Experiment subprocess failed: {error_msg}")

        return _parse_and_validate_result(process.stdout)

    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Experiment timed out after {timeout} seconds")
    except FileNotFoundError:
        raise RuntimeError(f"Python interpreter not found: {python_executable}")


def _run_with_logging(
    python_executable: str,
    python_code: str,
    params: dict,
    timeout: int,
    log_file: Path,
) -> dict:
    """Run experiment with real-time stderr logging to file.

    Uses Popen to stream stderr to log file as it's generated,
    enabling real-time progress monitoring.
    """
    import os
    import select
    import time

    # Ensure log directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Use unbuffered Python output so prints flush immediately
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        with open(log_file, "w", encoding="utf-8") as log_fh:
            process = subprocess.Popen(
                [python_executable, "-c", python_code],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )

            # Send params via stdin and close
            process.stdin.write(json.dumps(params))
            process.stdin.close()

            # Stream stderr to log file in real-time
            stdout_data = []
            start_time = time.time()

            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    process.kill()
                    raise TimeoutError(f"Experiment timed out after {timeout} seconds")

                # Check if process has finished
                if process.poll() is not None:
                    break

                # Read available stderr and write to log immediately
                try:
                    # Use select for non-blocking read (Unix)
                    readable, _, _ = select.select([process.stderr], [], [], 0.1)
                    if readable:
                        line = process.stderr.readline()
                        if line:
                            log_fh.write(line)
                            log_fh.flush()
                except (AttributeError, ValueError):
                    # Fallback for Windows or if select fails
                    time.sleep(0.1)

            # Read any remaining stderr
            remaining_stderr = process.stderr.read()
            if remaining_stderr:
                log_fh.write(remaining_stderr)
                log_fh.flush()

            # Read stdout (JSON result)
            stdout_content = process.stdout.read()

            if process.returncode != 0:
                # Read log file for error context
                log_fh.flush()
                error_context = log_file.read_text(encoding="utf-8")[-500:]
                raise RuntimeError(
                    f"Experiment subprocess failed (exit {process.returncode}): {error_context}"
                )

            return _parse_and_validate_result(stdout_content)

    except FileNotFoundError:
        raise RuntimeError(f"Python interpreter not found: {python_executable}")


def _parse_and_validate_result(stdout: str) -> dict:
    """Parse JSON output and validate result structure."""
    try:
        result = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse experiment output as JSON: {e}")

    if not isinstance(result, dict):
        raise RuntimeError("Experiment must return a dictionary")

    if "status" not in result:
        raise RuntimeError("Experiment result missing 'status' field")

    if result["status"] not in ("success", "failed"):
        raise RuntimeError(
            f"Invalid status value: {result['status']}. Must be 'success' or 'failed'"
        )

    if result["status"] == "failed" and "error" not in result:
        raise RuntimeError("Failed experiment must include 'error' field")

    return result


def _check_type(value: any, type_name: str) -> bool:
    """Check if value matches the expected type (no coercion).

    Args:
        value: Value to check
        type_name: Expected type name (int, float, str, bool, list)

    Returns:
        True if type matches, False otherwise
    """
    type_map = {
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
    }

    expected_type = type_map.get(type_name)
    if expected_type is None:
        return False

    # Strict type checking (no coercion)
    # Note: bool is a subclass of int in Python, so check bool before int
    if type_name == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    else:
        return isinstance(value, expected_type)
