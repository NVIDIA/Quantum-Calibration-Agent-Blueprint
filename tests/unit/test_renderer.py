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

"""Tests for vlm.renderer.render_plot_to_base64."""

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from vlm.renderer import render_plot_to_base64

SIMPLE_FIGURE = {"data": [{"x": [1, 2, 3], "y": [1, 2, 3]}], "layout": {}}


# --- Successful renders ---


def test_render_dict_input_returns_valid_base64():
    """Successful render with dict input produces a non-empty, decodable base64 string."""
    fake_png = b"\x89PNG fake image bytes"
    mock_fig = MagicMock()
    mock_fig.to_image.return_value = fake_png

    with patch("plotly.io.from_json", return_value=mock_fig):
        result = render_plot_to_base64(SIMPLE_FIGURE)

    assert isinstance(result, str)
    assert len(result) > 0
    decoded = base64.b64decode(result)
    assert decoded == fake_png


def test_render_json_string_input():
    """Successful render with JSON string input."""
    fake_png = b"\x89PNG fake image bytes"
    mock_fig = MagicMock()
    mock_fig.to_image.return_value = fake_png
    json_str = json.dumps(SIMPLE_FIGURE)

    with patch("plotly.io.from_json", return_value=mock_fig):
        result = render_plot_to_base64(json_str)

    assert isinstance(result, str)
    decoded = base64.b64decode(result)
    assert decoded == fake_png


# --- Invalid inputs ---


def test_invalid_json_string_raises_value_error():
    """Invalid JSON string raises ValueError."""
    with pytest.raises(ValueError, match="Invalid JSON string"):
        render_plot_to_base64("{not valid json!!!")


def test_non_dict_input_raises_value_error():
    """Non-dict input (e.g., a list) raises ValueError."""
    with pytest.raises(ValueError, match="Expected dict or JSON string"):
        render_plot_to_base64([1, 2, 3])


def test_invalid_plotly_structure_raises_value_error():
    """Invalid Plotly JSON structure raises ValueError."""
    with patch(
        "plotly.io.from_json", side_effect=Exception("Invalid figure data")
    ):
        with pytest.raises(ValueError, match="Invalid Plotly JSON structure"):
            render_plot_to_base64({"bogus": "data"})


# --- Missing dependencies ---


def test_missing_plotly_raises_runtime_error():
    """Missing plotly import raises RuntimeError."""
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "plotly.io":
            raise ImportError("No module named 'plotly'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.raises(RuntimeError, match="plotly is required"):
            render_plot_to_base64(SIMPLE_FIGURE)


def test_missing_kaleido_raises_runtime_error():
    """Missing kaleido raises RuntimeError when fig.to_image raises ValueError."""
    mock_fig = MagicMock()
    mock_fig.to_image.side_effect = ValueError(
        "Image export using the \"kaleido\" engine requires the kaleido package"
    )

    with patch("plotly.io.from_json", return_value=mock_fig):
        with pytest.raises(RuntimeError, match="kaleido is required"):
            render_plot_to_base64(SIMPLE_FIGURE)


# --- Custom parameters ---


def test_custom_width_height_scale_passed_through():
    """Custom width, height, and scale parameters are forwarded to fig.to_image."""
    fake_png = b"png"
    mock_fig = MagicMock()
    mock_fig.to_image.return_value = fake_png

    with patch("plotly.io.from_json", return_value=mock_fig):
        render_plot_to_base64(SIMPLE_FIGURE, width=1024, height=768, scale=2.0)

    mock_fig.to_image.assert_called_once_with(
        format="png",
        width=1024,
        height=768,
        scale=2.0,
    )
