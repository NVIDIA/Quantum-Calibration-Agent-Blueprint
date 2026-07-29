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
        """Float type checking — int is accepted since JSON has no int/float distinction."""
        assert _check_type(5.0, "float") is True
        assert _check_type(5, "float") is True
        assert _check_type(True, "float") is False

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


class TestArrayExtraction:
    """Tests that tagged arrays are promoted to a top-level `arrays` key."""

    def test_arrays_extracted_from_data(self, temp_scripts_dir):
        """Arrays tagged in `data` are promoted; scalars are excluded."""
        script = temp_scripts_dir / "array_experiment.py"
        script.write_text(
            '''
from typing import Annotated

def array_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Experiment returning tagged arrays and a scalar."""
    return {
        "status": "success",
        "data": {
            "delays": {"type": "array", "value": [0.0, 1.0, 2.0], "unit": "us"},
            "population": {"type": "array", "value": [0.9, 0.5, 0.2]},
            "t1_time": {"type": "scalar", "value": 42.0, "unit": "us"},
        },
    }
'''
        )
        result = run_experiment("array_experiment", {"param1": 5.0}, temp_scripts_dir)
        assert result["arrays"] == {
            "delays": [0.0, 1.0, 2.0],
            "population": [0.9, 0.5, 0.2],
        }
        # Scalars must not leak into arrays.
        assert "t1_time" not in result["arrays"]

    def test_existing_arrays_win_but_do_not_suppress_promotion(
        self, temp_scripts_dir
    ):
        """Top-level `arrays` entries win, and tagged arrays still extend them.

        Precedence is `arrays` > `results` > `data` with first writer wins, so
        `freq` keeps the script's own value while `mag` is still promoted.
        """
        script = temp_scripts_dir / "prebuilt_arrays_experiment.py"
        script.write_text(
            '''
from typing import Annotated

def prebuilt_arrays_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Experiment that already supplies a top-level arrays key."""
    return {
        "status": "success",
        "arrays": {"freq": [1.0, 2.0]},
        "data": {"mag": {"type": "array", "value": [9.0]}},
    }
'''
        )
        result = run_experiment(
            "prebuilt_arrays_experiment", {"param1": 5.0}, temp_scripts_dir
        )
        assert result["arrays"] == {"freq": [1.0, 2.0], "mag": [9.0]}

    def test_no_arrays_yields_empty_dict(self, temp_scripts_dir):
        """A result with only scalars yields an empty arrays dict, not a crash."""
        script = temp_scripts_dir / "scalar_only_experiment.py"
        script.write_text(
            '''
from typing import Annotated

def scalar_only_experiment(
    param1: Annotated[float, (0.0, 10.0)] = 5.0,
) -> dict:
    """Experiment returning only scalar data."""
    return {
        "status": "success",
        "data": {"t1_time": {"type": "scalar", "value": 42.0}},
    }
'''
        )
        result = run_experiment(
            "scalar_only_experiment", {"param1": 5.0}, temp_scripts_dir
        )
        assert result["arrays"] == {}


class TestArrayPromotionAcrossContainers:
    """Tagged arrays must be collected from every container, not just one."""

    @staticmethod
    def _promote(result):
        from core.runner import _parse_and_validate_result
        import json as _json

        return _parse_and_validate_result(_json.dumps(result))

    def test_results_does_not_shadow_data(self):
        """A non-empty `results` must not hide tagged arrays in `data`.

        The single-container selection previously picked `results` because it
        was truthy and never inspected `data`, so the array never reached the
        HDF5 arrays group this promotion exists to fill.
        """
        promoted = self._promote(
            {
                "status": "success",
                "results": {"fit": 1.0},
                "data": {"signal": {"type": "array", "value": [1, 2, 3]}},
            }
        )
        assert promoted["arrays"] == {"signal": [1, 2, 3]}

    def test_both_containers_are_merged(self):
        """Tagged arrays in `results` and `data` are combined."""
        promoted = self._promote(
            {
                "status": "success",
                "results": {"a": {"type": "array", "value": [1]}},
                "data": {"b": {"type": "array", "value": [2]}},
            }
        )
        assert promoted["arrays"] == {"a": [1], "b": [2]}

    def test_results_wins_name_collision(self):
        """On a duplicate name, `results` takes precedence over `data`."""
        promoted = self._promote(
            {
                "status": "success",
                "results": {"x": {"type": "array", "value": [1]}},
                "data": {"x": {"type": "array", "value": [2]}},
            }
        )
        assert promoted["arrays"] == {"x": [1]}

    def test_non_dict_results_does_not_block_data(self):
        """A truthy non-dict `results` must not suppress promotion from `data`."""
        promoted = self._promote(
            {
                "status": "success",
                "results": ["not", "a", "mapping"],
                "data": {"signal": {"type": "array", "value": [1, 2]}},
            }
        )
        assert promoted["arrays"] == {"signal": [1, 2]}

    def test_non_dict_top_level_arrays_is_replaced(self):
        """A non-dict top-level `arrays` must not reach storage."""
        promoted = self._promote(
            {
                "status": "success",
                "arrays": "not a mapping",
                "data": {"signal": {"type": "array", "value": [1, 2]}},
            }
        )
        assert promoted["arrays"] == {"signal": [1, 2]}

    @pytest.mark.parametrize(
        "tagged",
        [
            {"type": "scalar", "value": 42.0},
            {"type": "array"},
            {"type": "array", "value": 42.0},
            {"type": "array", "value": "abc"},
            {"type": "array", "value": {"a": 1}},
        ],
    )
    def test_invalid_tagged_entries_are_skipped(self, tagged):
        """Only a tagged array whose value is a list is promoted."""
        promoted = self._promote(
            {"status": "success", "data": {"candidate": tagged}}
        )
        assert promoted["arrays"] == {}

    def test_non_list_top_level_array_value_is_dropped(self):
        """A top-level `arrays` entry that is not a list is not persisted."""
        promoted = self._promote(
            {
                "status": "success",
                "arrays": {"good": [1, 2], "bad": 42.0},
            }
        )
        assert promoted["arrays"] == {"good": [1, 2]}


class TestPromotedArraysArePersistable:
    """Every promoted array must survive the real storage round trip."""

    def test_promoted_arrays_round_trip_through_storage(self, tmp_path):
        """Promotion output is written to and read back from HDF5 unchanged."""
        from core import storage
        from core.models import ExperimentResult
        from core.runner import _parse_and_validate_result
        import json as _json

        promoted = _parse_and_validate_result(
            _json.dumps(
                {
                    "status": "success",
                    "results": {"fit": 1.0, "trace": {"type": "array", "value": [1.0, 2.0]}},
                    "data": {
                        "signal": {"type": "array", "value": [3.0, 4.0, 5.0]},
                        "scalar": {"type": "scalar", "value": 9.0},
                    },
                }
            )
        )
        assert promoted["arrays"] == {
            "trace": [1.0, 2.0],
            "signal": [3.0, 4.0, 5.0],
        }

        result = ExperimentResult(
            id="20260727_000000_round_trip",
            type="round_trip",
            timestamp="2026-07-27T00:00:00Z",
            status="success",
            arrays=promoted["arrays"],
        )
        storage.save_experiment(result, tmp_path)

        loaded = storage.load_experiment(result.id, tmp_path)
        assert loaded is not None
        assert loaded.arrays == promoted["arrays"]


class TestOnlyPersistableArraysArePromoted:
    """A list is not enough: storage must be able to write and read it back.

    core/storage.py calls np.array() on write and slices with [:] on read, so
    a ragged list raises from numpy and string, object or None-bearing lists
    raise from h5py. Promoting them would turn a good run into a save failure.
    """

    @staticmethod
    def _promote(result):
        from core.runner import _parse_and_validate_result
        import json as _json

        return _parse_and_validate_result(_json.dumps(result))

    @pytest.mark.parametrize(
        "value",
        [
            [[1, 2], [3]],
            ["a", "b"],
            [{"a": 1}],
            [1, "a"],
            [None, 1],
        ],
        ids=["ragged", "strings", "dicts", "mixed", "with_none"],
    )
    def test_unwritable_lists_are_not_promoted(self, value):
        promoted = self._promote(
            {
                "status": "success",
                "data": {"candidate": {"type": "array", "value": value}},
            }
        )
        assert promoted["arrays"] == {}

    @pytest.mark.parametrize(
        "value",
        [
            [[1, 2], [3]],
            ["a", "b"],
            [{"a": 1}],
        ],
        ids=["ragged", "strings", "dicts"],
    )
    def test_unwritable_top_level_arrays_are_dropped(self, value):
        promoted = self._promote({"status": "success", "arrays": {"bad": value}})
        assert promoted["arrays"] == {}

    @pytest.mark.parametrize(
        "value",
        [
            [1.0, 2.0],
            [1, 2, 3],
            [[1, 2], [3, 4]],
            [True, False],
            [],
        ],
        ids=["floats", "ints", "nested_rectangular", "bools", "empty"],
    )
    def test_writable_lists_are_still_promoted(self, value):
        promoted = self._promote(
            {
                "status": "success",
                "data": {"good": {"type": "array", "value": value}},
            }
        )
        assert promoted["arrays"] == {"good": value}

    @pytest.mark.parametrize(
        "value",
        [
            [1.0, 2.0],
            [[1, 2], [3, 4]],
            [True, False],
            [],
        ],
        ids=["floats", "nested_rectangular", "bools", "empty"],
    )
    def test_every_promoted_shape_survives_storage(self, value, tmp_path):
        """The promotion filter is verified against the real storage path."""
        from core import storage
        from core.models import ExperimentResult

        promoted = self._promote(
            {
                "status": "success",
                "data": {"good": {"type": "array", "value": value}},
            }
        )
        assert promoted["arrays"] == {"good": value}

        result = ExperimentResult(
            id="20260727_000000_shapes",
            type="shapes",
            timestamp="2026-07-27T00:00:00Z",
            status="success",
            arrays=promoted["arrays"],
        )
        storage.save_experiment(result, tmp_path)
        loaded = storage.load_experiment(result.id, tmp_path)

        assert loaded is not None
        assert loaded.arrays == {"good": value}


class TestArrayNamesMustBePersistable:
    """A promoted name becomes an HDF5 dataset name, so it must be usable.

    The value was validated but the key was not: an
    empty name is invalid, "." and ".." address existing groups rather than a
    new dataset, and a name containing "/" silently creates intermediate
    groups that load_experiment then tries to slice as a dataset.
    """

    @staticmethod
    def _promote(result):
        from core.runner import _parse_and_validate_result
        import json as _json

        return _parse_and_validate_result(_json.dumps(result))

    @pytest.mark.parametrize(
        "name", ["", ".", "..", "/", "a/b", "nested/deep/name"]
    )
    def test_unusable_names_are_not_promoted(self, name):
        promoted = self._promote(
            {
                "status": "success",
                "data": {name: {"type": "array", "value": [1, 2]}},
            }
        )
        assert promoted["arrays"] == {}

    @pytest.mark.parametrize("name", ["", ".", "a/b"])
    def test_unusable_names_in_top_level_arrays_are_dropped(self, name):
        promoted = self._promote({"status": "success", "arrays": {name: [1, 2]}})
        assert promoted["arrays"] == {}

    def test_usable_names_still_promote(self):
        promoted = self._promote(
            {
                "status": "success",
                "data": {"signal_1": {"type": "array", "value": [1, 2]}},
            }
        )
        assert promoted["arrays"] == {"signal_1": [1, 2]}

    def test_promoted_name_survives_storage(self, tmp_path):
        """Verified against the real write, not against an assumption."""
        from core import storage
        from core.models import ExperimentResult

        promoted = self._promote(
            {
                "status": "success",
                "arrays": {"bad/name": [9, 9]},
                "data": {"good_name": {"type": "array", "value": [1, 2]}},
            }
        )
        assert promoted["arrays"] == {"good_name": [1, 2]}

        result = ExperimentResult(
            id="20260727_000000_names",
            type="names",
            timestamp="2026-07-27T00:00:00Z",
            status="success",
            arrays=promoted["arrays"],
        )
        storage.save_experiment(result, tmp_path)
        loaded = storage.load_experiment(result.id, tmp_path)

        assert loaded is not None
        assert loaded.arrays == {"good_name": [1, 2]}


class TestResultContainersAreNormalised:
    """`results` and `data` collapse into one container before persistence.

    The documented script return format has no `results` key; scalars and
    tagged arrays go under `data`, and `results` is the stored field name that
    the persistence paths tolerate as an alias. Because only one container is
    ever read downstream while arrays were gathered from both, the stored
    scalars and the stored arrays could describe different subsets of one run.
    """

    @staticmethod
    def _parse(result):
        from core.runner import _parse_and_validate_result
        import json as _json

        return _parse_and_validate_result(_json.dumps(result))

    @staticmethod
    def _downstream(result):
        """What the CLI and lab persistence paths read."""
        container = result.get("results") or result.get("data", {})
        return container if isinstance(container, dict) else {}

    def test_scalars_and_arrays_come_from_the_same_container(self):
        parsed = self._parse(
            {
                "status": "success",
                "results": {"fit": 1.0},
                "data": {"signal": {"type": "array", "value": [1, 2, 3]}},
            }
        )
        stored = self._downstream(parsed)

        assert stored["fit"] == 1.0
        assert "signal" in stored
        assert parsed["arrays"] == {"signal": [1, 2, 3]}

    def test_documented_data_only_form_is_unchanged(self):
        parsed = self._parse(
            {
                "status": "success",
                "data": {
                    "t1": {"type": "scalar", "value": 42.0},
                    "signal": {"type": "array", "value": [1, 2]},
                },
            }
        )
        stored = self._downstream(parsed)

        assert set(stored) == {"t1", "signal"}
        assert parsed["arrays"] == {"signal": [1, 2]}

    def test_results_wins_a_name_collision(self):
        parsed = self._parse(
            {
                "status": "success",
                "results": {"x": {"type": "array", "value": [1]}},
                "data": {"x": {"type": "array", "value": [9]}},
            }
        )
        assert parsed["arrays"] == {"x": [1]}
        assert self._downstream(parsed)["x"]["value"] == [1]

    def test_non_dict_results_does_not_shadow_data(self):
        parsed = self._parse(
            {
                "status": "success",
                "results": ["not a mapping"],
                "data": {"signal": {"type": "array", "value": [7]}},
            }
        )
        assert self._downstream(parsed) == {
            "signal": {"type": "array", "value": [7]}
        }
        assert parsed["arrays"] == {"signal": [7]}


class TestArrayConversionIsLossless:
    """A numeric dtype is not proof the conversion preserved the value."""

    @staticmethod
    def _promote(result):
        from core.runner import _parse_and_validate_result
        import json as _json

        return _parse_and_validate_result(_json.dumps(result))

    def test_integer_beyond_float_mantissa_is_rejected(self):
        """Mixing a large int with a float silently rounds it to float64."""
        promoted = self._promote(
            {
                "status": "success",
                "data": {
                    "lossy": {
                        "type": "array",
                        "value": [9007199254740993, 0.5],
                    }
                },
            }
        )
        assert promoted["arrays"] == {}

    @pytest.mark.parametrize(
        "value",
        [[1, 2, 3], [1.0, 2.5], [[1, 2], [3, 4]], [True, False], [9007199254740993]],
        ids=["ints", "floats", "nested", "bools", "big_int_alone"],
    )
    def test_lossless_values_are_still_promoted(self, value):
        promoted = self._promote(
            {"status": "success", "data": {"ok": {"type": "array", "value": value}}}
        )
        assert promoted["arrays"] == {"ok": value}

    @pytest.mark.parametrize("name", ["bad\ud800name", "\udfff"])
    def test_names_that_cannot_be_encoded_are_rejected(self, name):
        """h5py encodes the name as UTF-8; a lone surrogate raises there."""
        promoted = self._promote(
            {
                "status": "success",
                "data": {name: {"type": "array", "value": [1, 2]}},
            }
        )
        assert promoted["arrays"] == {}
