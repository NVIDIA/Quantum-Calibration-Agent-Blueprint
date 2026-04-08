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

"""Unit tests for core/storage.py."""

import pytest
from pathlib import Path
from core.storage import (
    save_experiment,
    load_experiment,
    search_experiments,
    delete_experiment,
    list_arrays,
    get_array,
    get_array_stats,
    list_plots,
    get_plot,
    reindex,
)
from core.models import ExperimentResult


class TestSaveLoadExperiment:
    """Tests for save and load experiment functions."""

    def test_save_and_load(self, temp_data_dir, sample_experiment_result):
        """Save and load experiment."""
        save_experiment(sample_experiment_result, temp_data_dir)
        loaded = load_experiment(sample_experiment_result.id, temp_data_dir)

        assert loaded is not None
        assert loaded.id == sample_experiment_result.id
        assert loaded.type == sample_experiment_result.type
        assert loaded.status == sample_experiment_result.status
        assert loaded.params == sample_experiment_result.params

    def test_load_nonexistent(self, temp_data_dir):
        """Load nonexistent experiment returns None."""
        loaded = load_experiment("nonexistent", temp_data_dir)
        assert loaded is None

    def test_save_with_arrays(self, temp_data_dir):
        """Save experiment with arrays."""
        exp = ExperimentResult(
            id="test_arrays",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            arrays={"freq": [1.0, 2.0, 3.0], "mag": [0.1, 0.2, 0.3]},
        )
        save_experiment(exp, temp_data_dir)
        loaded = load_experiment("test_arrays", temp_data_dir)

        assert loaded.arrays["freq"] == [1.0, 2.0, 3.0]
        assert loaded.arrays["mag"] == [0.1, 0.2, 0.3]

    def test_save_with_plots(self, temp_data_dir):
        """Save experiment with Plotly plots."""
        exp = ExperimentResult(
            id="test_plots",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            plots=[
                {
                    "name": "spectrum",
                    "format": "plotly",
                    "data": {"data": [{"x": [1, 2], "y": [3, 4]}], "layout": {}},
                }
            ],
        )
        save_experiment(exp, temp_data_dir)
        loaded = load_experiment("test_plots", temp_data_dir)

        assert len(loaded.plots) == 1
        assert loaded.plots[0]["name"] == "spectrum"
        assert loaded.plots[0]["format"] == "plotly"

    def test_save_with_target(self, temp_data_dir):
        """Save experiment with target field."""
        exp = ExperimentResult(
            id="test_target",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            target="qubit_1",
        )
        save_experiment(exp, temp_data_dir)
        loaded = load_experiment("test_target", temp_data_dir)

        assert loaded.target == "qubit_1"

    def test_save_with_notes(self, temp_data_dir):
        """Save experiment with notes."""
        exp = ExperimentResult(
            id="test_notes",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            notes="Test notes",
        )
        save_experiment(exp, temp_data_dir)
        loaded = load_experiment("test_notes", temp_data_dir)

        assert loaded.notes == "Test notes"

    def test_load_missing_file(self, temp_data_dir):
        """Load experiment when HDF5 file is missing returns None."""
        exp = ExperimentResult(
            id="test_missing",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
        )
        save_experiment(exp, temp_data_dir)

        # Delete the HDF5 file but leave the index entry
        loaded = load_experiment("test_missing", temp_data_dir)
        assert loaded is not None

        # Now delete the file
        if loaded.file_path:
            Path(loaded.file_path).unlink()

        # Try to load again - should return None
        loaded = load_experiment("test_missing", temp_data_dir)
        assert loaded is None


class TestSearchExperiments:
    """Tests for search_experiments function."""

    def test_search_all(self, temp_data_dir_with_experiments):
        """Search all experiments."""
        results = search_experiments(temp_data_dir_with_experiments)
        assert len(results) >= 1

    def test_search_by_type(self, temp_data_dir_with_experiments):
        """Search by experiment type."""
        results = search_experiments(
            temp_data_dir_with_experiments, type="qubit_spectroscopy"
        )
        assert all(r["type"] == "qubit_spectroscopy" for r in results)

    def test_search_with_limit(self, temp_data_dir_with_experiments):
        """Search with limit."""
        results = search_experiments(temp_data_dir_with_experiments, last=1)
        assert len(results) <= 1

    def test_search_empty(self, temp_data_dir):
        """Search empty database."""
        results = search_experiments(temp_data_dir)
        assert results == []

    def test_search_by_target(self, temp_data_dir):
        """Search by target."""
        # Create experiments with different targets
        exp1 = ExperimentResult(
            id="exp_target1",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            target="qubit_0",
        )
        exp2 = ExperimentResult(
            id="exp_target2",
            type="test",
            timestamp="2026-03-22T10:01:00Z",
            status="success",
            target="qubit_1",
        )
        save_experiment(exp1, temp_data_dir)
        save_experiment(exp2, temp_data_dir)

        results = search_experiments(temp_data_dir, target="qubit_0")
        assert len(results) == 1
        assert results[0]["target"] == "qubit_0"

    def test_search_by_type_and_target(self, temp_data_dir):
        """Search by both type and target."""
        exp1 = ExperimentResult(
            id="exp_combo1",
            type="qubit_spectroscopy",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            target="qubit_0",
        )
        exp2 = ExperimentResult(
            id="exp_combo2",
            type="qubit_spectroscopy",
            timestamp="2026-03-22T10:01:00Z",
            status="success",
            target="qubit_1",
        )
        exp3 = ExperimentResult(
            id="exp_combo3",
            type="resonator_spectroscopy",
            timestamp="2026-03-22T10:02:00Z",
            status="success",
            target="qubit_0",
        )
        save_experiment(exp1, temp_data_dir)
        save_experiment(exp2, temp_data_dir)
        save_experiment(exp3, temp_data_dir)

        results = search_experiments(
            temp_data_dir, type="qubit_spectroscopy", target="qubit_0"
        )
        assert len(results) == 1
        assert results[0]["type"] == "qubit_spectroscopy"
        assert results[0]["target"] == "qubit_0"


class TestDeleteExperiment:
    """Tests for delete_experiment function."""

    def test_delete_existing(self, temp_data_dir, sample_experiment_result):
        """Delete existing experiment."""
        save_experiment(sample_experiment_result, temp_data_dir)
        delete_experiment(sample_experiment_result.id, temp_data_dir)
        loaded = load_experiment(sample_experiment_result.id, temp_data_dir)
        assert loaded is None

    def test_delete_nonexistent(self, temp_data_dir):
        """Delete nonexistent experiment (no error)."""
        delete_experiment("nonexistent", temp_data_dir)  # Should not raise

    def test_delete_removes_file(self, temp_data_dir, sample_experiment_result):
        """Delete removes HDF5 file."""
        save_experiment(sample_experiment_result, temp_data_dir)
        loaded = load_experiment(sample_experiment_result.id, temp_data_dir)
        file_path = Path(loaded.file_path)
        assert file_path.exists()

        delete_experiment(sample_experiment_result.id, temp_data_dir)
        assert not file_path.exists()


class TestArrayOperations:
    """Tests for array operations."""

    @pytest.fixture
    def exp_with_arrays(self, temp_data_dir):
        """Create experiment with arrays."""
        exp = ExperimentResult(
            id="array_test",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            arrays={"freq": [1.0, 2.0, 3.0, 4.0, 5.0]},
        )
        save_experiment(exp, temp_data_dir)
        return temp_data_dir

    def test_list_arrays(self, exp_with_arrays):
        """List arrays in experiment."""
        arrays = list_arrays("array_test", exp_with_arrays)
        assert arrays is not None
        assert any(a["name"] == "freq" for a in arrays)

    def test_list_arrays_nonexistent(self, temp_data_dir):
        """List arrays for nonexistent experiment returns None."""
        arrays = list_arrays("nonexistent", temp_data_dir)
        assert arrays is None

    def test_list_arrays_no_arrays(self, temp_data_dir):
        """List arrays for experiment without arrays returns empty list."""
        exp = ExperimentResult(
            id="no_arrays",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
        )
        save_experiment(exp, temp_data_dir)
        arrays = list_arrays("no_arrays", temp_data_dir)
        assert arrays == []

    def test_get_array_full(self, exp_with_arrays):
        """Get full array."""
        data = get_array("array_test", "freq", exp_with_arrays)
        assert data == [1.0, 2.0, 3.0, 4.0, 5.0]

    def test_get_array_sliced(self, exp_with_arrays):
        """Get sliced array."""
        data = get_array("array_test", "freq", exp_with_arrays, start=1, end=3)
        assert data == [2.0, 3.0]

    def test_get_array_start_only(self, exp_with_arrays):
        """Get array with start index only."""
        data = get_array("array_test", "freq", exp_with_arrays, start=3)
        assert data == [4.0, 5.0]

    def test_get_array_end_only(self, exp_with_arrays):
        """Get array with end index only."""
        data = get_array("array_test", "freq", exp_with_arrays, end=2)
        assert data == [1.0, 2.0]

    def test_get_array_nonexistent_experiment(self, temp_data_dir):
        """Get array from nonexistent experiment returns None."""
        data = get_array("nonexistent", "freq", temp_data_dir)
        assert data is None

    def test_get_array_nonexistent_array(self, exp_with_arrays):
        """Get nonexistent array returns None."""
        data = get_array("array_test", "nonexistent", exp_with_arrays)
        assert data is None

    def test_get_array_stats(self, exp_with_arrays):
        """Get array statistics."""
        stats = get_array_stats("array_test", "freq", exp_with_arrays)
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["count"] == 5
        assert stats["mean"] == 3.0  # (1+2+3+4+5)/5 = 3

    def test_get_array_stats_nonexistent(self, temp_data_dir):
        """Get stats for nonexistent experiment returns None."""
        stats = get_array_stats("nonexistent", "freq", temp_data_dir)
        assert stats is None

    def test_list_arrays_metadata(self, temp_data_dir):
        """List arrays includes metadata (shape, dtype)."""
        exp = ExperimentResult(
            id="metadata_test",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            arrays={"data": [1.0, 2.0, 3.0]},
        )
        save_experiment(exp, temp_data_dir)
        arrays = list_arrays("metadata_test", temp_data_dir)

        assert len(arrays) == 1
        assert arrays[0]["name"] == "data"
        assert "shape" in arrays[0]
        assert "dtype" in arrays[0]


class TestPlotOperations:
    """Tests for plot operations."""

    @pytest.fixture
    def exp_with_plots(self, temp_data_dir):
        """Create experiment with plots."""
        exp = ExperimentResult(
            id="plot_test",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            plots=[
                {
                    "name": "spectrum",
                    "format": "plotly",
                    "data": {
                        "data": [{"x": [1, 2], "y": [3, 4]}],
                        "layout": {"title": "Test"},
                    },
                }
            ],
        )
        save_experiment(exp, temp_data_dir)
        return temp_data_dir

    def test_list_plots(self, exp_with_plots):
        """List plots in experiment."""
        plots = list_plots("plot_test", exp_with_plots)
        assert plots is not None
        assert any(p["name"] == "spectrum" for p in plots)

    def test_list_plots_nonexistent(self, temp_data_dir):
        """List plots for nonexistent experiment returns None."""
        plots = list_plots("nonexistent", temp_data_dir)
        assert plots is None

    def test_list_plots_no_plots(self, temp_data_dir):
        """List plots for experiment without plots returns empty list."""
        exp = ExperimentResult(
            id="no_plots",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
        )
        save_experiment(exp, temp_data_dir)
        plots = list_plots("no_plots", temp_data_dir)
        assert plots == []

    def test_get_plot(self, exp_with_plots):
        """Get plot data."""
        plot = get_plot("plot_test", "spectrum", exp_with_plots)
        assert plot is not None
        assert plot["format"] == "plotly"
        assert "data" in plot["data"]

    def test_get_plot_nonexistent_experiment(self, temp_data_dir):
        """Get plot from nonexistent experiment returns None."""
        plot = get_plot("nonexistent", "spectrum", temp_data_dir)
        assert plot is None

    def test_get_plot_nonexistent_plot(self, exp_with_plots):
        """Get nonexistent plot returns None."""
        plot = get_plot("plot_test", "nonexistent", exp_with_plots)
        assert plot is None

    def test_plot_roundtrip_plotly(self, temp_data_dir):
        """Test Plotly plot round-trip (save and load)."""
        original_data = {
            "data": [{"x": [1, 2, 3], "y": [4, 5, 6], "type": "scatter"}],
            "layout": {"title": "Test Plot", "xaxis": {"title": "X"}},
        }
        exp = ExperimentResult(
            id="roundtrip_test",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            plots=[{"name": "test_plot", "format": "plotly", "data": original_data}],
        )
        save_experiment(exp, temp_data_dir)

        # Load and verify
        plot = get_plot("roundtrip_test", "test_plot", temp_data_dir)
        assert plot["data"] == original_data

    def test_plot_roundtrip_base64(self, temp_data_dir):
        """Test base64 plot round-trip (save and load)."""
        base64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        exp = ExperimentResult(
            id="base64_test",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            plots=[{"name": "image", "format": "png", "data": base64_data}],
        )
        save_experiment(exp, temp_data_dir)

        # Load and verify
        plot = get_plot("base64_test", "image", temp_data_dir)
        assert plot["data"] == base64_data
        assert plot["format"] == "png"

    def test_list_plots_multiple(self, temp_data_dir):
        """List multiple plots."""
        exp = ExperimentResult(
            id="multi_plots",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            plots=[
                {"name": "plot1", "format": "plotly", "data": {"data": []}},
                {"name": "plot2", "format": "png", "data": "base64data"},
            ],
        )
        save_experiment(exp, temp_data_dir)

        plots = list_plots("multi_plots", temp_data_dir)
        assert len(plots) == 2
        plot_names = {p["name"] for p in plots}
        assert plot_names == {"plot1", "plot2"}


class TestReindex:
    """Tests for reindex function."""

    def test_reindex_empty(self, temp_data_dir):
        """Reindex empty database."""
        reindex(temp_data_dir)
        results = search_experiments(temp_data_dir)
        assert results == []

    def test_reindex_with_experiments(self, temp_data_dir):
        """Reindex database with experiments."""
        # Save some experiments
        exp1 = ExperimentResult(
            id="exp1", type="test", timestamp="2026-03-22T10:00:00Z", status="success"
        )
        exp2 = ExperimentResult(
            id="exp2", type="test", timestamp="2026-03-22T10:01:00Z", status="success"
        )
        save_experiment(exp1, temp_data_dir)
        save_experiment(exp2, temp_data_dir)

        # Reindex
        reindex(temp_data_dir)

        # Verify both experiments are still findable
        results = search_experiments(temp_data_dir)
        assert len(results) == 2

    def test_reindex_no_experiments_dir(self, temp_data_dir):
        """Reindex when experiments directory doesn't exist."""
        # Don't create any experiments
        reindex(temp_data_dir)
        results = search_experiments(temp_data_dir)
        assert results == []

    def test_reindex_rebuilds_from_files(self, temp_data_dir):
        """Reindex rebuilds index from HDF5 files."""
        # Save experiment
        exp = ExperimentResult(
            id="rebuild_test",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            target="qubit_0",
        )
        save_experiment(exp, temp_data_dir)

        # Manually corrupt the index by deleting the entry
        import sqlite3

        db_path = temp_data_dir / "index.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM experiments WHERE id = ?", ("rebuild_test",))
        conn.commit()
        conn.close()

        # Verify it's gone
        loaded = load_experiment("rebuild_test", temp_data_dir)
        assert loaded is None

        # Reindex
        reindex(temp_data_dir)

        # Verify it's back
        loaded = load_experiment("rebuild_test", temp_data_dir)
        assert loaded is not None
        assert loaded.id == "rebuild_test"
