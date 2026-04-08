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

"""Unit tests for experiment scripts."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# Add scripts to path
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestQubitSpectroscopy:
    """Tests for qubit_spectroscopy script."""

    @patch("qubit_spectroscopy.time.sleep")
    def test_output_format(self, mock_sleep):
        """Output has required format."""
        from qubit_spectroscopy import qubit_spectroscopy

        result = qubit_spectroscopy(
            center_freq=4.8,
            span=0.2,
            num_points=11,
            drive_amplitude=0.1,
            num_averages=500,
        )

        assert result["status"] == "success"
        assert "data" in result
        assert "plots" in result
        assert "qubit_freq" in result["data"]
        assert result["data"]["qubit_freq"]["type"] == "scalar"
        assert "value" in result["data"]["qubit_freq"]
        assert isinstance(result["plots"], list)
        assert len(result["plots"]) > 0


class TestResonatorSpectroscopy:
    """Tests for resonator_spectroscopy script."""

    @patch("resonator_spectroscopy.time.sleep")
    def test_output_format(self, mock_sleep):
        """Output has required format."""
        from resonator_spectroscopy import resonator_spectroscopy

        result = resonator_spectroscopy(
            center_freq=6.0, span=0.1, num_points=11, power=-20.0, num_averages=100
        )

        assert result["status"] == "success"
        assert "data" in result
        assert "resonator_freq" in result["data"]
        assert result["data"]["resonator_freq"]["type"] == "scalar"
        assert "value" in result["data"]["resonator_freq"]
        assert isinstance(result["plots"], list)
        assert len(result["plots"]) > 0


class TestRabiOscillation:
    """Tests for rabi_oscillation script."""

    @patch("rabi_oscillation.time.sleep")
    def test_output_format(self, mock_sleep):
        """Output has required format."""
        from rabi_oscillation import rabi_oscillation

        result = rabi_oscillation(
            max_amplitude=1.0, num_points=11, pulse_width=20.0, num_averages=100
        )

        assert result["status"] == "success"
        assert "data" in result
        assert "pi_amplitude" in result["data"]
        assert result["data"]["pi_amplitude"]["type"] == "scalar"
        assert "value" in result["data"]["pi_amplitude"]
        assert isinstance(result["plots"], list)
        assert len(result["plots"]) > 0


class TestT1Measurement:
    """Tests for t1_measurement script."""

    @patch("t1_measurement.time.sleep")
    def test_output_format(self, mock_sleep):
        """Output has required format."""
        from t1_measurement import t1_measurement

        result = t1_measurement(max_delay=100.0, num_points=11, num_averages=100)

        assert result["status"] == "success"
        assert "data" in result
        assert "t1_time" in result["data"]
        assert result["data"]["t1_time"]["type"] == "scalar"
        assert "value" in result["data"]["t1_time"]
        assert isinstance(result["plots"], list)
        assert len(result["plots"]) > 0


class TestRamseyMeasurement:
    """Tests for ramsey_measurement script."""

    @patch("ramsey_measurement.time.sleep")
    def test_output_format(self, mock_sleep):
        """Output has required format."""
        from ramsey_measurement import ramsey_measurement

        result = ramsey_measurement(
            max_delay=10.0, num_points=11, artificial_detuning=0.01, num_averages=100
        )

        assert result["status"] == "success"
        assert "data" in result
        assert "t2_star" in result["data"]
        assert result["data"]["t2_star"]["type"] == "scalar"
        assert "value" in result["data"]["t2_star"]
        assert isinstance(result["plots"], list)
        assert len(result["plots"]) > 0

    @patch("ramsey_measurement.time.sleep")
    def test_population_has_oscillations(self, mock_sleep):
        """Population data should show Ramsey fringes, not monotonic decay."""
        from ramsey_measurement import ramsey_measurement

        result = ramsey_measurement(
            max_delay=30.0, num_points=81, artificial_detuning=2.0, num_averages=50000
        )

        population = result["data"]["excited_population"]["value"]

        # Count direction changes (oscillations)
        direction_changes = 0
        for i in range(1, len(population) - 1):
            if (population[i] - population[i - 1]) * (population[i + 1] - population[i]) < 0:
                direction_changes += 1

        # With 2 MHz detuning over 30 us, expect ~60 cycles.
        # Even with noise, there should be many direction changes.
        # A monotonic decay (the bug) would have very few.
        assert direction_changes > 10, (
            f"Expected oscillations in Ramsey data but only found "
            f"{direction_changes} direction changes — data may be monotonic"
        )
