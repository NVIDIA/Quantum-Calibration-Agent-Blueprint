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

"""Unit tests for core/runner.py."""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
from core.runner import run_experiment, validate_params, _check_type
from core.models import ExperimentSchema, ParameterSpec


class TestValidateParams:
    """Tests for validate_params function."""

    @pytest.fixture
    def sample_schema(self):
        """Sample experiment schema."""
        return ExperimentSchema(
            name="test_exp",
            description="Test",
            parameters=[
                ParameterSpec(
                    name="freq", type="float", required=True, range=(1.0, 10.0)
                ),
                ParameterSpec(
                    name="count",
                    type="int",
                    required=False,
                    default=100,
                    range=(1, 1000),
                ),
                ParameterSpec(name="name", type="str", required=False, default="test"),
            ],
            module_path="/test.py",
        )

    def test_valid_params(self, sample_schema):
        """Valid parameters pass validation."""
        errors = validate_params({"freq": 5.0, "count": 50}, sample_schema)
        assert errors == []

    def test_missing_required_param(self, sample_schema):
        """Missing required parameter fails."""
        errors = validate_params({"count": 50}, sample_schema)
        assert any("Missing required" in e for e in errors)

    def test_unknown_param(self, sample_schema):
        """Unknown parameter fails."""
        errors = validate_params({"freq": 5.0, "unknown": 123}, sample_schema)
        assert any("Unknown parameter" in e for e in errors)

    def test_wrong_type(self, sample_schema):
        """Wrong type fails."""
        errors = validate_params({"freq": "not a float"}, sample_schema)
        assert any("wrong type" in e for e in errors)

    def test_out_of_range(self, sample_schema):
        """Out of range value fails."""
        errors = validate_params({"freq": 100.0}, sample_schema)  # Max is 10.0
        assert any("out of range" in e for e in errors)

    def test_valid_params_with_all_fields(self, sample_schema):
        """Valid parameters with all fields pass."""
        errors = validate_params(
            {"freq": 5.0, "count": 500, "name": "custom"}, sample_schema
        )
        assert errors == []

    def test_range_boundary_values(self, sample_schema):
        """Test boundary values for range validation."""
        # Min boundary
        errors = validate_params({"freq": 1.0}, sample_schema)
        assert errors == []

        # Max boundary
        errors = validate_params({"freq": 10.0}, sample_schema)
        assert errors == []

        # Below min
        errors = validate_params({"freq": 0.5}, sample_schema)
        assert any("out of range" in e for e in errors)

        # Above max
        errors = validate_params({"freq": 10.5}, sample_schema)
        assert any("out of range" in e for e in errors)


class TestCheckType:
    """Tests for _check_type function."""

    def test_int_type(self):
        """Integer type checking."""
        assert _check_type(5, "int") is True
        assert _check_type(5.0, "int") is False
        assert (
            _check_type(True, "int") is False
        )  # bool is subclass of int but should be rejected

    def test_float_type(self):
        """Float type checking."""
        assert _check_type(5.0, "float") is True
        assert _check_type(5, "float") is False

    def test_str_type(self):
        """String type checking."""
        assert _check_type("hello", "str") is True
        assert _check_type(123, "str") is False

    def test_bool_type(self):
        """Boolean type checking."""
        assert _check_type(True, "bool") is True
        assert _check_type(False, "bool") is True
        assert _check_type(1, "bool") is False

    def test_list_type(self):
        """List type checking."""
        assert _check_type([1, 2, 3], "list") is True
        assert _check_type((1, 2, 3), "list") is False
        assert _check_type([], "list") is True

    def test_unknown_type(self):
        """Unknown type returns False."""
        assert _check_type("value", "unknown_type") is False


class TestRunExperiment:
    """Tests for run_experiment function."""

    def test_experiment_not_found(self, tmp_path):
        """Nonexistent experiment raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            run_experiment("nonexistent", {}, tmp_path)

    def test_validation_error(self, temp_scripts_dir):
        """Invalid params raise ValueError."""
        with pytest.raises(ValueError, match="validation failed"):
            run_experiment(
                "test_experiment", {"param1": 100.0}, temp_scripts_dir
            )  # Out of range

    def test_successful_run(self, temp_scripts_dir):
        """Successful experiment run."""
        result = run_experiment("test_experiment", {"param1": 5.0}, temp_scripts_dir)
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["result"] == 10.0  # param1 * 2

    def test_subprocess_timeout(self, temp_scripts_dir):
        """Test subprocess timeout handling."""
        # Create a script that sleeps longer than timeout
        sleep_script = temp_scripts_dir / "slow_experiment.py"
        sleep_script.write_text(
            '''
from typing import Annotated
import time

def slow_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Slow experiment."""
    time.sleep(10)  # Sleep for 10 seconds
    return {"status": "success", "data": {"result": param1}}
'''
        )

        with pytest.raises(TimeoutError, match="timed out"):
            run_experiment(
                "slow_experiment", {"param1": 5.0}, temp_scripts_dir, timeout=1
            )

    def test_subprocess_non_zero_exit(self, temp_scripts_dir):
        """Test handling of subprocess that exits with error."""
        # Create a script that raises an exception
        error_script = temp_scripts_dir / "error_experiment.py"
        error_script.write_text(
            '''
from typing import Annotated

def error_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Error experiment."""
    raise ValueError("Intentional error")
'''
        )

        with pytest.raises(RuntimeError, match="subprocess failed"):
            run_experiment("error_experiment", {"param1": 5.0}, temp_scripts_dir)

    def test_invalid_json_output(self, temp_scripts_dir):
        """Test handling of invalid JSON output."""
        # Create a script that prints invalid JSON
        bad_json_script = temp_scripts_dir / "bad_json_experiment.py"
        bad_json_script.write_text(
            '''
from typing import Annotated

def bad_json_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Bad JSON experiment."""
    print("This is not JSON")
    return {"status": "success", "data": {"result": param1}}
'''
        )

        with pytest.raises(
            RuntimeError, match="Failed to parse experiment output as JSON"
        ):
            run_experiment("bad_json_experiment", {"param1": 5.0}, temp_scripts_dir)

    def test_non_dict_output(self, temp_scripts_dir):
        """Test handling of non-dict return value."""
        # Create a script that returns a list instead of dict
        non_dict_script = temp_scripts_dir / "non_dict_experiment.py"
        non_dict_script.write_text(
            '''
from typing import Annotated

def non_dict_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Non-dict experiment."""
    # Return list even though type hint says dict
    return [param1]
'''
        )

        with pytest.raises(RuntimeError, match="must return a dictionary"):
            run_experiment("non_dict_experiment", {"param1": 5.0}, temp_scripts_dir)

    def test_missing_status_field(self, temp_scripts_dir):
        """Test handling of missing status field in result."""
        # Create a script that returns dict without status
        no_status_script = temp_scripts_dir / "no_status_experiment.py"
        no_status_script.write_text(
            '''
from typing import Annotated

def no_status_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """No status experiment."""
    return {"data": {"result": param1}}
'''
        )

        with pytest.raises(RuntimeError, match="missing 'status' field"):
            run_experiment("no_status_experiment", {"param1": 5.0}, temp_scripts_dir)

    def test_invalid_status_value(self, temp_scripts_dir):
        """Test handling of invalid status value."""
        # Create a script that returns invalid status
        invalid_status_script = temp_scripts_dir / "invalid_status_experiment.py"
        invalid_status_script.write_text(
            '''
from typing import Annotated

def invalid_status_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Invalid status experiment."""
    return {"status": "pending", "data": {"result": param1}}
'''
        )

        with pytest.raises(RuntimeError, match="Invalid status value"):
            run_experiment(
                "invalid_status_experiment", {"param1": 5.0}, temp_scripts_dir
            )

    def test_failed_status_without_error(self, temp_scripts_dir):
        """Test handling of failed status without error field."""
        # Create a script that returns failed status without error
        failed_no_error_script = temp_scripts_dir / "failed_no_error_experiment.py"
        failed_no_error_script.write_text(
            '''
from typing import Annotated

def failed_no_error_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Failed no error experiment."""
    return {"status": "failed", "data": {"result": param1}}
'''
        )

        with pytest.raises(
            RuntimeError, match="Failed experiment must include 'error' field"
        ):
            run_experiment(
                "failed_no_error_experiment", {"param1": 5.0}, temp_scripts_dir
            )

    def test_failed_status_with_error(self, temp_scripts_dir):
        """Test successful handling of failed status with error field."""
        # Create a script that returns failed status with error
        failed_with_error_script = temp_scripts_dir / "failed_with_error_experiment.py"
        failed_with_error_script.write_text(
            '''
from typing import Annotated

def failed_with_error_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Failed with error experiment."""
    return {"status": "failed", "error": "Something went wrong", "data": {}}
'''
        )

        result = run_experiment(
            "failed_with_error_experiment", {"param1": 5.0}, temp_scripts_dir
        )
        assert result["status"] == "failed"
        assert result["error"] == "Something went wrong"

    def test_custom_python_path(self, temp_scripts_dir):
        """Test using custom python path."""
        # Mock subprocess to verify python_path is used
        with patch("core.runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout='{"status": "success", "data": {"result": 10.0}}'
            )

            result = run_experiment(
                "test_experiment",
                {"param1": 5.0},
                temp_scripts_dir,
                python_path="/custom/python",
            )

            # Verify custom python path was used
            call_args = mock_run.call_args
            assert call_args[0][0][0] == "/custom/python"

    def test_python_interpreter_not_found(self, temp_scripts_dir):
        """Test handling of missing python interpreter."""
        with pytest.raises(RuntimeError, match="Python interpreter not found"):
            run_experiment(
                "test_experiment",
                {"param1": 5.0},
                temp_scripts_dir,
                python_path="/nonexistent/python",
            )

    def test_multiple_validation_errors(self, temp_scripts_dir):
        """Test multiple validation errors are reported."""
        # Create schema with multiple params
        schema = ExperimentSchema(
            name="multi_param_exp",
            description="Test",
            parameters=[
                ParameterSpec(
                    name="param1", type="float", required=True, range=(0.0, 10.0)
                ),
                ParameterSpec(name="param2", type="int", required=True, range=(1, 100)),
            ],
            module_path=str(temp_scripts_dir / "test.py"),
        )

        # Missing both required params
        errors = validate_params({}, schema)
        assert len(errors) == 2
        assert any("param1" in e for e in errors)
        assert any("param2" in e for e in errors)
