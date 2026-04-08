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

"""Unit tests for vlm_tool.py."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path


class TestVlmInspect:
    """Tests for vlm_inspect tool."""

    def test_no_vlm_config(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """Return error when VLM not configured."""
        from tools.vlm_tool import vlm_inspect

        with patch("tools.vlm_tool.CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            with patch("tools.vlm_tool.DATA_DIR", temp_data_dir_with_experiments):
                result = vlm_inspect.invoke(
                    {
                        "experiment_id": sample_experiment_result.id,
                        "prompt": "Analyze this plot",
                    }
                )
                assert result["status"] == "error"
                assert "not configured" in result["error"]

    def test_experiment_not_found(self, temp_data_dir):
        """Return error for nonexistent experiment."""
        from tools.vlm_tool import vlm_inspect, _get_vlm_config

        with patch("tools.vlm_tool.DATA_DIR", temp_data_dir):
            with patch(
                "tools.vlm_tool._get_vlm_config", return_value={"model": "test"}
            ):
                result = vlm_inspect.invoke(
                    {"experiment_id": "nonexistent", "prompt": "Analyze"}
                )
                assert result["status"] == "error"
                assert "not found" in result["error"]

    def test_no_plots_in_experiment(self, temp_data_dir_with_experiments):
        """Return error when experiment has no plots."""
        from tools.vlm_tool import vlm_inspect, _get_vlm_config
        from core.models import ExperimentResult
        from core.storage import save_experiment

        # Create experiment without plots
        exp_no_plots = ExperimentResult(
            id="no_plots_exp",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            plots=[],
        )
        save_experiment(exp_no_plots, temp_data_dir_with_experiments)

        with patch("tools.vlm_tool.DATA_DIR", temp_data_dir_with_experiments):
            with patch(
                "tools.vlm_tool._get_vlm_config", return_value={"model": "test"}
            ):
                result = vlm_inspect.invoke(
                    {"experiment_id": "no_plots_exp", "prompt": "Analyze"}
                )
                assert result["status"] == "error"
                assert "No plots" in result["error"]

    def test_successful_analysis(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """Successful VLM analysis."""
        from tools.vlm_tool import vlm_inspect, _get_vlm_config

        mock_vlm = MagicMock()
        mock_vlm.analyze_images = AsyncMock(
            return_value="Analysis: Peak found at 4.85 GHz"
        )

        with patch("tools.vlm_tool.DATA_DIR", temp_data_dir_with_experiments):
            with patch(
                "tools.vlm_tool._get_vlm_config", return_value={"model": "test"}
            ):
                with patch("tools.vlm_tool.get_vlm_client", return_value=mock_vlm):
                    with patch(
                        "tools.vlm_tool.render_plot_to_base64",
                        return_value="base64data",
                    ):
                        result = vlm_inspect.invoke(
                            {
                                "experiment_id": sample_experiment_result.id,
                                "prompt": "Analyze this plot",
                            }
                        )
                        assert result["status"] == "success"
                        assert "analysis" in result
                        assert result["plot_count"] >= 1

    def test_unsupported_plot_format(self, temp_data_dir):
        """Return error with partial failure when plot format is unsupported."""
        from tools.vlm_tool import vlm_inspect, _get_vlm_config
        from core.models import ExperimentResult
        from core.storage import save_experiment

        # Create experiment with unsupported plot format
        exp_unsupported = ExperimentResult(
            id="unsupported_fmt_exp",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            plots=[
                {
                    "name": "unsupported_plot",
                    "format": "svg",  # Unsupported format
                    "data": {"some": "data"},
                }
            ],
        )
        save_experiment(exp_unsupported, temp_data_dir)

        with patch("tools.vlm_tool.DATA_DIR", temp_data_dir):
            with patch(
                "tools.vlm_tool._get_vlm_config", return_value={"model": "test"}
            ):
                result = vlm_inspect.invoke(
                    {"experiment_id": "unsupported_fmt_exp", "prompt": "Analyze"}
                )
                assert result["status"] == "error"
                assert "Failed to render" in result["error"]

    def test_render_failure(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """Handle render_plot_to_base64 failure gracefully."""
        from tools.vlm_tool import vlm_inspect, _get_vlm_config

        with patch("tools.vlm_tool.DATA_DIR", temp_data_dir_with_experiments):
            with patch(
                "tools.vlm_tool._get_vlm_config", return_value={"model": "test"}
            ):
                with patch(
                    "tools.vlm_tool.render_plot_to_base64",
                    side_effect=Exception("Render error"),
                ):
                    result = vlm_inspect.invoke(
                        {
                            "experiment_id": sample_experiment_result.id,
                            "prompt": "Analyze",
                        }
                    )
                    assert result["status"] == "error"
                    assert "Failed to render" in result["error"]
                    assert "details" in result

    def test_vlm_provider_failure(
        self, temp_data_dir_with_experiments, sample_experiment_result
    ):
        """Handle VLM provider call failure."""
        from tools.vlm_tool import vlm_inspect, _get_vlm_config

        mock_vlm = MagicMock()
        mock_vlm.analyze_images = AsyncMock(side_effect=Exception("API error"))

        with patch("tools.vlm_tool.DATA_DIR", temp_data_dir_with_experiments):
            with patch(
                "tools.vlm_tool._get_vlm_config", return_value={"model": "test"}
            ):
                with patch("tools.vlm_tool.get_vlm_client", return_value=mock_vlm):
                    with patch(
                        "tools.vlm_tool.render_plot_to_base64",
                        return_value="base64data",
                    ):
                        result = vlm_inspect.invoke(
                            {
                                "experiment_id": sample_experiment_result.id,
                                "prompt": "Analyze",
                            }
                        )
                        assert result["status"] == "error"
                        assert "VLM analysis failed" in result["error"]

    def test_multiple_plots_analysis(self, temp_data_dir):
        """Successful analysis with multiple plots."""
        from tools.vlm_tool import vlm_inspect, _get_vlm_config
        from core.models import ExperimentResult
        from core.storage import save_experiment

        # Create experiment with multiple plots
        exp_multi_plots = ExperimentResult(
            id="multi_plots_exp",
            type="test",
            timestamp="2026-03-22T10:00:00Z",
            status="success",
            plots=[
                {
                    "name": "plot1",
                    "format": "plotly",
                    "data": {"data": [{"x": [1, 2], "y": [3, 4]}], "layout": {}},
                },
                {
                    "name": "plot2",
                    "format": "plotly",
                    "data": {"data": [{"x": [5, 6], "y": [7, 8]}], "layout": {}},
                },
            ],
        )
        save_experiment(exp_multi_plots, temp_data_dir)

        mock_vlm = MagicMock()
        mock_vlm.analyze_images = AsyncMock(return_value="Analysis of all plots")

        with patch("tools.vlm_tool.DATA_DIR", temp_data_dir):
            with patch(
                "tools.vlm_tool._get_vlm_config", return_value={"model": "test"}
            ):
                with patch("tools.vlm_tool.get_vlm_client", return_value=mock_vlm):
                    with patch(
                        "tools.vlm_tool.render_plot_to_base64",
                        return_value="base64data",
                    ):
                        result = vlm_inspect.invoke(
                            {
                                "experiment_id": "multi_plots_exp",
                                "prompt": "Analyze all plots",
                            }
                        )
                        assert result["status"] == "success"
                        assert result["plot_count"] == 2
                        assert len(result["plots_analyzed"]) == 2

                        # Verify VLM was called with enhanced prompt
                        call_args = mock_vlm.analyze_images.call_args
                        assert "2 plots" in call_args[0][0]
                        assert "plot1" in call_args[0][0]
                        assert "plot2" in call_args[0][0]


class TestGetVlmConfig:
    """Tests for _get_vlm_config function."""

    def test_config_exists(self, tmp_path):
        """Load config from existing file."""
        from tools.vlm_tool import _get_vlm_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("vlm:\n  model: test-model\n  provider: nvidia")

        with patch("tools.vlm_tool.CONFIG_PATH", config_file):
            config = _get_vlm_config()
            assert config["model"] == "test-model"
            assert config["provider"] == "nvidia"

    def test_config_not_exists(self, tmp_path):
        """Return empty dict when config doesn't exist."""
        from tools.vlm_tool import _get_vlm_config

        with patch("tools.vlm_tool.CONFIG_PATH", tmp_path / "nonexistent.yaml"):
            config = _get_vlm_config()
            assert config == {}

    def test_config_no_vlm_section(self, tmp_path):
        """Return empty dict when config has no vlm section."""
        from tools.vlm_tool import _get_vlm_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text("other:\n  key: value")

        with patch("tools.vlm_tool.CONFIG_PATH", config_file):
            config = _get_vlm_config()
            assert config == {}

    def test_config_invalid_yaml(self, tmp_path):
        """Handle invalid YAML gracefully - should return empty dict."""
        from tools.vlm_tool import _get_vlm_config
        import yaml

        config_file = tmp_path / "config.yaml"
        config_file.write_text("invalid: yaml: syntax: error:")

        with patch("tools.vlm_tool.CONFIG_PATH", config_file):
            # The function should either:
            # 1. Return empty dict on invalid YAML, or
            # 2. Raise yaml.YAMLError specifically
            try:
                config = _get_vlm_config()
                # If no exception, must return empty dict
                assert (
                    config == {}
                ), f"Expected empty dict on invalid YAML, got {config}"
            except yaml.YAMLError:
                # YAML parsing error is acceptable and expected
                pass
