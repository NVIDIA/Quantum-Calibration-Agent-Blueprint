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

"""Unit tests for lab_tool.py."""

import pytest
from unittest.mock import patch, MagicMock
from tools.lab_tool import lab, run_experiment, _get_info, _get_schema, _history_list


class TestQcalInfo:
    """Tests for lab info action."""

    def test_info_returns_experiments(self, temp_scripts_dir):
        """Info action returns discovered experiments."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            result = lab.invoke({"action": "info"})
            assert "experiments" in result
            assert "usage" in result
            assert len(result["experiments"]) >= 1

    def test_info_empty_scripts_dir(self, tmp_path):
        """Info with empty scripts directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with patch("tools.lab_tool.SCRIPTS_DIR", empty_dir):
            result = lab.invoke({"action": "info"})
            assert result["experiments"] == []


class TestQcalListExperiments:
    """Tests for lab list_experiments action."""

    def test_list_experiments(self, temp_scripts_dir):
        """List experiments action returns experiment list."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            result = lab.invoke({"action": "list_experiments"})
            assert "experiments" in result
            assert len(result["experiments"]) >= 1

    def test_list_experiments_empty(self, tmp_path):
        """List experiments from empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with patch("tools.lab_tool.SCRIPTS_DIR", empty_dir):
            result = lab.invoke({"action": "list_experiments"})
            assert result["experiments"] == []


class TestQcalSchema:
    """Tests for lab schema action."""

    def test_schema_existing_experiment(self, temp_scripts_dir):
        """Get schema for existing experiment."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            result = lab.invoke(
                {"action": "schema", "experiment_name": "test_experiment"}
            )
            assert result["name"] == "test_experiment"
            assert "parameters" in result

    def test_schema_nonexistent_experiment(self, temp_scripts_dir):
        """Schema for nonexistent experiment returns error."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            result = lab.invoke({"action": "schema", "experiment_name": "nonexistent"})
            assert "error" in result
            assert "available_experiments" in result

    def test_schema_missing_experiment_name(self, temp_scripts_dir):
        """Schema without experiment_name returns error."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            result = lab.invoke({"action": "schema"})
            assert "error" in result
            assert "experiment_name is required" in result["error"]


class TestQcalHistoryList:
    """Tests for lab history_list action."""

    def test_history_list_with_experiments(self, temp_data_dir_with_experiments):
        """List experiments from storage."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke({"action": "history_list"})
            assert "experiments" in result
            assert result["count"] >= 1

    def test_history_list_empty(self, temp_data_dir):
        """List from empty storage."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke({"action": "history_list"})
            assert result["count"] == 0
            assert result["experiments"] == []

    def test_history_list_with_filter(self, temp_data_dir_with_experiments):
        """Filter by experiment type."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke(
                {"action": "history_list", "filter_type": "qubit_spectroscopy"}
            )
            assert all(e["type"] == "qubit_spectroscopy" for e in result["experiments"])

    def test_history_list_with_last_n(self, temp_data_dir_with_experiments):
        """Limit results with last_n."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke({"action": "history_list", "last_n": 1})
            assert len(result["experiments"]) <= 1


class TestQcalHistoryShow:
    """Tests for lab history_show action."""

    def test_history_show_existing(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """Show details of existing experiment."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke(
                {"action": "history_show", "experiment_id": sample_experiment_result.id}
            )
            assert result["id"] == sample_experiment_result.id
            assert result["type"] == sample_experiment_result.type

    def test_history_show_nonexistent(self, temp_data_dir):
        """Show nonexistent experiment returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke(
                {"action": "history_show", "experiment_id": "nonexistent"}
            )
            assert "error" in result

    def test_history_show_missing_id(self, temp_data_dir):
        """Show without experiment_id returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke({"action": "history_show"})
            assert "error" in result
            assert "experiment_id is required" in result["error"]


class TestQcalArrays:
    """Tests for array operations."""

    def test_list_arrays(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """List arrays in experiment."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke(
                {"action": "list_arrays", "experiment_id": sample_experiment_result.id}
            )
            assert "arrays" in result

    def test_list_arrays_missing_id(self, temp_data_dir):
        """List arrays without experiment_id returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke({"action": "list_arrays"})
            assert "error" in result
            assert "experiment_id is required" in result["error"]

    def test_list_arrays_nonexistent(self, temp_data_dir):
        """List arrays for nonexistent experiment returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke(
                {"action": "list_arrays", "experiment_id": "nonexistent"}
            )
            assert "error" in result

    def test_get_array(self, temp_data_dir_with_experiments, sample_experiment_result):
        """Get array data."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke(
                {
                    "action": "get_array",
                    "experiment_id": sample_experiment_result.id,
                    "array_name": "frequencies",
                }
            )
            assert "data" in result
            assert result["array"] == "frequencies"

    def test_get_array_with_slice(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """Get array with slicing."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke(
                {
                    "action": "get_array",
                    "experiment_id": sample_experiment_result.id,
                    "array_name": "frequencies",
                    "slice_start": 0,
                    "slice_end": 2,
                }
            )
            assert len(result["data"]) == 2

    def test_get_array_missing_id(self, temp_data_dir):
        """Get array without experiment_id returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke({"action": "get_array", "array_name": "frequencies"})
            assert "error" in result
            assert "experiment_id is required" in result["error"]

    def test_get_array_missing_name(self, temp_data_dir, sample_experiment_result):
        """Get array without array_name returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke(
                {"action": "get_array", "experiment_id": sample_experiment_result.id}
            )
            assert "error" in result
            assert "array_name is required" in result["error"]

    def test_get_array_nonexistent_array(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """Get nonexistent array returns error with available arrays."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke(
                {
                    "action": "get_array",
                    "experiment_id": sample_experiment_result.id,
                    "array_name": "nonexistent",
                }
            )
            assert "error" in result
            assert "available_arrays" in result


class TestQcalStats:
    """Tests for get_stats action."""

    def test_get_stats(self, temp_data_dir_with_experiments, sample_experiment_result):
        """Get array statistics."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke(
                {
                    "action": "get_stats",
                    "experiment_id": sample_experiment_result.id,
                    "array_name": "frequencies",
                }
            )
            assert "stats" in result
            assert result["array"] == "frequencies"

    def test_get_stats_missing_id(self, temp_data_dir):
        """Get stats without experiment_id returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke({"action": "get_stats", "array_name": "frequencies"})
            assert "error" in result
            assert "experiment_id is required" in result["error"]

    def test_get_stats_missing_name(self, temp_data_dir):
        """Get stats without array_name returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
            result = lab.invoke({"action": "get_stats", "experiment_id": "test_id"})
            assert "error" in result
            assert "array_name is required" in result["error"]

    def test_get_stats_nonexistent_array(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """Get stats for nonexistent array returns error."""
        with patch("tools.lab_tool.DATA_DIR", temp_data_dir_with_experiments):
            result = lab.invoke(
                {
                    "action": "get_stats",
                    "experiment_id": sample_experiment_result.id,
                    "array_name": "nonexistent",
                }
            )
            assert "error" in result
            assert "available_arrays" in result


class TestRunExperiment:
    """Tests for run_experiment tool."""

    def test_run_experiment_validation_error(self, temp_scripts_dir, temp_data_dir):
        """Run with invalid params returns error."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
                result = run_experiment.invoke(
                    {
                        "experiment_name": "test_experiment",
                        "params": {"param1": 100.0},  # Out of range (max is 10.0)
                    }
                )
                assert "error" in result
                assert "hint" in result

    def test_run_experiment_not_found(self, temp_scripts_dir, temp_data_dir):
        """Run nonexistent experiment returns error."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
                result = run_experiment.invoke(
                    {"experiment_name": "nonexistent", "params": {}}
                )
                assert "error" in result
                assert "available_experiments" in result

    def test_run_experiment_success(self, temp_scripts_dir, temp_data_dir):
        """Successfully run experiment."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
                result = run_experiment.invoke(
                    {"experiment_name": "test_experiment", "params": {"param1": 5.0}}
                )
                assert result["status"] == "success"
                assert "id" in result
                assert "timestamp" in result
                assert "results" in result

    def test_run_experiment_data_key_fallback(self, temp_scripts_dir, temp_data_dir):
        """Experiment returning 'data' key (not 'results') should still preserve results.

        Regression test: scripts return data under 'data' key, but the storage
        layer expects 'results'. The fallback logic must map 'data' -> 'results'
        so experiment results are not silently discarded.
        """
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
                result = run_experiment.invoke(
                    {"experiment_name": "test_experiment", "params": {"param1": 5.0}}
                )
                # The test_experiment fixture returns {"data": {"result": 10.0}}
                # with no "results" key — the fallback must pick up "data"
                assert result["results"] != {}, "Results should not be empty when script returns 'data' key"
                assert result["results"]["result"] == 10.0

    def test_run_experiment_with_notes(self, temp_scripts_dir, temp_data_dir):
        """Run experiment with notes."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
                result = run_experiment.invoke(
                    {
                        "experiment_name": "test_experiment",
                        "params": {"param1": 5.0},
                        "notes": "Test notes",
                    }
                )
                assert result["status"] == "success"


class TestQcalUnknownAction:
    """Tests for unknown actions."""

    def test_unknown_action(self):
        """Unknown action returns error with valid actions list."""
        result = lab.invoke({"action": "unknown"})
        assert "error" in result
        assert "valid_actions" in result
        assert "Unknown action" in result["error"]

    def test_run_action_redirects(self):
        """Run action redirects to run_experiment tool."""
        result = lab.invoke({"action": "run"})
        assert "error" in result
        assert "run_experiment tool" in result["error"]


class TestErrorHandling:
    """Tests for general error handling."""

    def test_exception_handling(self, temp_scripts_dir):
        """Exceptions are caught and returned as errors."""
        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            # Force an exception by passing bad data to storage
            with patch(
                "tools.lab_tool.storage.search_experiments",
                side_effect=Exception("Test error"),
            ):
                result = lab.invoke({"action": "history_list"})
                assert "error" in result
                assert "Test error" in result["error"]
