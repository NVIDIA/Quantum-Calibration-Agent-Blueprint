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

"""Mock resonator spectroscopy with realistic wall-clock execution time."""

import json
import sys
import time
from typing import Annotated

import numpy as np

from .qubit_params import get_qubit_params


# Redirect progress output to stderr so stdout only has JSON result
def _log(msg):
    print(msg, file=sys.stderr, flush=True)


def resonator_spectroscopy(
    qubit: str = "Q0",
    center_freq: Annotated[float, (5.5, 6.5)] = 6.0,
    span: Annotated[float, (0.05, 0.5)] = 0.1,
    num_points: Annotated[int, (51, 201)] = 101,
    power: Annotated[float, (-40.0, 0.0)] = -20.0,
    num_averages: Annotated[int, (100, 10000)] = 1000,
) -> dict:
    """Perform resonator spectroscopy measurement.

    Sweeps microwave frequency to find the resonator dip.
    Includes realistic execution time simulation.

    Args:
        center_freq: Center frequency of sweep (GHz)
        span: Frequency span of sweep (GHz)
        num_points: Number of frequency points
        power: Drive power (dBm)
        num_averages: Number of measurement averages

    Returns:
        frequencies: Array of probe frequencies (GHz)
        magnitude: S21 magnitude response (dB)
        resonator_freq: Fitted resonator frequency (GHz)
    """
    # Get qubit-specific parameters
    params = get_qubit_params(qubit)
    f_res = params["resonator_freq"]
    q_factor = params["q_factor"]

    _log("=" * 60)
    _log(f"RESONATOR SPECTROSCOPY [{qubit}] - Starting measurement")
    _log("=" * 60)
    _log(f"  Qubit: {qubit}")
    _log(f"  Center frequency: {center_freq:.4f} GHz")
    _log(f"  Span: {span:.3f} GHz")
    _log(f"  Number of points: {num_points}")
    _log(f"  Power: {power:.1f} dBm")
    _log(f"  Averages: {num_averages}")
    _log("-" * 60)

    # Calculate execution time based on parameters
    # More points and averages = longer execution (10x realistic for testing)
    base_time = 20.0  # Base time in seconds
    point_time = num_points * 0.1  # ~10s per 100 points
    avg_time = num_averages * 0.005  # ~5s per 1000 averages
    total_time = base_time + point_time + avg_time

    _log(f"  Estimated execution time: {total_time:.1f} seconds")
    _log("-" * 60)

    # Simulate measurement phases
    phases = [
        ("Initializing VNA connection", 0.3),
        ("Configuring frequency sweep", 0.2),
        ("Setting power level", 0.1),
        ("Acquiring data", total_time * 0.6),
        ("Processing averages", total_time * 0.2),
        ("Fitting resonance", 0.3),
    ]

    for phase_name, phase_time in phases:
        _log(f"  [{time.strftime('%H:%M:%S')}] {phase_name}...")
        time.sleep(phase_time)

    _log("-" * 60)

    # Generate simulated data
    frequencies = np.linspace(
        center_freq - span / 2, center_freq + span / 2, num_points
    )

    # Resonator response (Lorentzian dip)
    kappa = f_res / q_factor  # Linewidth

    # S21 magnitude (dip at resonance)
    delta = frequencies - f_res
    baseline = -5.0 + power * 0.1
    dip_depth = 15.0 + power * 0.2
    magnitude = baseline - dip_depth * (kappa / 2) ** 2 / (delta**2 + (kappa / 2) ** 2)

    # Add noise
    noise_level = 0.5 / np.sqrt(num_averages / 1000)
    magnitude += np.random.normal(0, noise_level, num_points)

    # Find resonance
    min_idx = np.argmin(magnitude)
    fitted_freq = frequencies[min_idx]
    fitted_depth = baseline - magnitude[min_idx]

    _log(f"  Resonator frequency: {fitted_freq:.6f} GHz")
    _log(f"  Dip depth: {fitted_depth:.2f} dB")
    _log(f"  Q factor: ~{q_factor}")
    _log("=" * 60)
    _log("RESONATOR SPECTROSCOPY - Complete")
    _log("=" * 60)

    return {
        "status": "success",
        "data": {
            "frequencies": {
                "type": "array",
                "value": frequencies.tolist(),
                "unit": "GHz",
                "name": "Probe frequencies",
            },
            "magnitude": {
                "type": "array",
                "value": magnitude.tolist(),
                "unit": "dB",
                "name": "S21 magnitude response",
            },
            "resonator_freq": {
                "type": "scalar",
                "value": float(fitted_freq),
                "unit": "GHz",
                "name": "Fitted resonator frequency",
            },
            "q_factor": {
                "type": "scalar",
                "value": float(q_factor),
                "unit": "dimensionless",
                "name": "Quality factor estimate",
            },
        },
        "plots": [
            {
                "name": "Resonator spectroscopy S21 response",
                "format": "plotly",
                "data": {
                    "data": [
                        {
                            "x": frequencies.tolist(),
                            "y": magnitude.tolist(),
                            "type": "scatter",
                            "mode": "lines",
                            "name": "S21",
                        }
                    ],
                    "layout": {
                        "title": f"Resonator Spectroscopy - f_res = {fitted_freq:.4f} GHz",
                        "xaxis": {"title": "Frequency (GHz)"},
                        "yaxis": {"title": "S21 Magnitude (dB)"},
                    },
                },
            }
        ],
    }
