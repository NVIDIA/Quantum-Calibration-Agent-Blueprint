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
from copy import deepcopy
from pathlib import Path

import numpy as np

from .discovery import get_experiment_schema
from .models import ExperimentSchema, ParameterSpec


def resolve_params(params: dict, schema: ExperimentSchema) -> dict:
    """Merge parameter overrides with defaults discovery safely resolved.

    A default is only carried over when validation would accept it. Discovery
    records an annotation name verbatim when it is not one of the few it maps,
    so a signature like `Dict[str, int]` yields the type name "Dict", which
    _check_type does not recognise. Injecting such a default would fail
    validation and abort a run that previously worked, because the parameter
    used to be omitted and Python applied the declared default itself. Leaving
    it out preserves that behaviour.
    """
    effective_params = {
        param.name: deepcopy(param.default)
        for param in schema.parameters
        if not param.required
        and param.default_resolved
        and not _check_value(param, param.default)
    }
    effective_params.update(params)
    return effective_params


def _check_value(spec: ParameterSpec, value: any) -> list[str]:
    """Return the validation errors for one parameter value.

    Shared by validate_params and resolve_params so that the rules deciding
    whether a value is acceptable live in exactly one place.
    """
    errors = []

    if (
        value is None
        and not spec.required
        and spec.default_resolved
        and spec.default is None
    ):
        return errors

    # Check type (strict, no coercion)
    if not _check_type(value, spec.type):
        errors.append(
            f"Parameter {spec.name} has wrong type. "
            f"Expected {spec.type}, got {type(value).__name__}"
        )
        return errors

    # Check range for numeric types
    if spec.range and spec.type in ("int", "float"):
        min_val, max_val = spec.range
        # An open bound is recorded as None, because the infinity that would
        # otherwise express it is not portable JSON.
        #
        # Each side is negated rather than compared directly so that NaN,
        # which returns false for every comparison, still fails the check
        # instead of silently satisfying both sides.
        below = min_val is not None and not (value >= min_val)
        above = max_val is not None and not (value <= max_val)
        if below or above:
            errors.append(
                f"Parameter {spec.name} out of range. "
                f"Expected [{min_val}, {max_val}], got {value}"
            )

    return errors


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

        errors.extend(_check_value(param_specs[param_name], param_value))

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

    # Resolve only defaults that discovery can safely carry over JSON. Dynamic
    # defaults remain omitted so Python applies their real declared values.
    params = resolve_params(params, schema)

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

    _normalise_result_containers(result)
    result["arrays"] = _collect_arrays(result)

    return result


def _normalise_result_containers(result: dict) -> None:
    """Collapse `results` and `data` into one canonical container.

    The documented script return format has no `results` key: a script reports
    its scalars and tagged arrays under `data`. `results` is the name of the
    stored field, and the persistence paths tolerate a script that uses it by
    reading `results` or falling back to `data` — so only one of the two is
    ever consumed downstream.

    That made it possible for the stored scalars and the stored arrays to
    describe different subsets of one run: arrays were gathered from both
    containers while everything else came from whichever container was picked.
    Merging them here means every consumer sees the same single container.
    `results` wins a name collision, matching the precedence the persistence
    paths already apply.
    """
    from_results = result.get("results")
    from_data = result.get("data")
    if not isinstance(from_results, dict) and not isinstance(from_data, dict):
        return

    canonical = {}
    if isinstance(from_data, dict):
        canonical.update(from_data)
    if isinstance(from_results, dict):
        canonical.update(from_results)
    result["results"] = canonical


def _collect_arrays(result: dict) -> dict:
    """Gather every persistable array from a result into one mapping.

    Scripts return arrays nested under `results`/`data` tagged `type:"array"`,
    and may also supply a top-level `arrays` mapping of raw values. Nothing
    else extracts the tagged form, so without this the queryable HDF5 `arrays`
    group would stay empty for those scripts.

    Precedence is the top-level `arrays` mapping, then `results`, then `data`,
    and the first writer of a name wins. Anything already present is therefore
    preserved rather than replaced, while names it does not define are still
    added. Entries that storage could not write are skipped rather than
    raising, since a malformed array should not fail an otherwise good run.
    """
    collected: dict = {}

    # Raw values, already in the shape storage expects.
    existing = result.get("arrays")
    if isinstance(existing, dict):
        for key, value in existing.items():
            if _is_persistable_name(key) and _is_persistable_array(value):
                collected[key] = value

    # Tagged values, which need unwrapping.
    for container_name in ("results", "data"):
        container = result.get(container_name)
        if not isinstance(container, dict):
            continue
        for key, value in container.items():
            if key in collected or not _is_persistable_name(key):
                continue
            if isinstance(value, dict) and value.get("type") == "array":
                candidate = value.get("value")
                if _is_persistable_array(candidate):
                    collected[key] = candidate

    return collected


def _is_persistable_name(name: any) -> bool:
    """Report whether storage could use this name as an HDF5 dataset name.

    Names become dataset names directly. An empty name is not a valid one,
    "." and ".." address the current and parent group rather than a new
    dataset, and a name containing "/" creates intermediate groups, which
    load_experiment then tries to slice as if it were a dataset.
    """
    if not isinstance(name, str) or not name:
        return False
    if "/" in name or "\x00" in name:
        return False
    if name in (".", ".."):
        return False
    # h5py encodes the name as UTF-8. A lone surrogate survives JSON transport
    # but cannot be encoded, so it would raise only at save time.
    try:
        name.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _is_persistable_array(value: any) -> bool:
    """Report whether storage could write this value and read it back.

    Being a list is not sufficient. core/storage.py builds the dataset with
    np.array() and reads it back by slicing with [:], so a ragged list raises
    from numpy and a list of strings, mappings or None raises from h5py for
    want of a native dtype. Mirroring the real write here keeps a malformed
    array from turning an otherwise successful run into a save failure.
    """
    if not isinstance(value, list):
        return False

    try:
        array = np.asarray(value)
    except (ValueError, TypeError):
        # Ragged nesting cannot become a rectangular array.
        return False

    if not (
        np.issubdtype(array.dtype, np.number)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        return False

    # The dtype alone does not prove the conversion kept the value. Mixing an
    # integer too large for a float mantissa with a float yields a float64
    # array that silently rounds it, so what is read back from storage would
    # differ from what the experiment reported.
    return array.tolist() == value


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
        "dict": dict,
    }

    expected_type = type_map.get(type_name)
    if expected_type is None:
        return False

    # Strict type checking (no coercion)
    # Note: bool is a subclass of int in Python, so check bool before int
    if type_name == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    elif type_name == "float":
        # JSON does not distinguish int from float — accept both
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    else:
        return isinstance(value, expected_type)
