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

"""Mock qubit spectroscopy with realistic wall-clock execution time."""

import json
import sys
import time
from typing import Annotated

import numpy as np

from .qubit_params import get_qubit_params


# Redirect progress output to stderr so stdout only has JSON result
def _log(msg):
    print(msg, file=sys.stderr, flush=True)


def qubit_spectroscopy(
    qubit: str = "Q0",
    center_freq: Annotated[float, (4.0, 5.5)] = 4.8,
    span: Annotated[float, (0.05, 0.5)] = 0.2,
    num_points: Annotated[int, (51, 201)] = 101,
    drive_amplitude: Annotated[float, (0.01, 1.0)] = 0.1,
    num_averages: Annotated[int, (500, 20000)] = 5000,
) -> dict:
    """Perform qubit spectroscopy measurement.

    Sweeps drive frequency to find the qubit transition frequency.
    Includes realistic execution time simulation.

    Args:
        center_freq: Center frequency of sweep (GHz)
        span: Frequency span of sweep (GHz)
        num_points: Number of frequency points
        drive_amplitude: Drive pulse amplitude (a.u.)
        num_averages: Number of measurement averages

    Returns:
        frequencies: Array of drive frequencies (GHz)
        excited_population: Measured excited state population
        qubit_freq: Fitted qubit frequency (GHz)
    """
    # Get qubit-specific parameters
    params = get_qubit_params(qubit)
    f_qubit = params["qubit_freq"]

    _log("=" * 60)
    _log(f"QUBIT SPECTROSCOPY [{qubit}] - Starting measurement")
    _log("=" * 60)
    _log(f"  Qubit: {qubit}")
    _log(f"  Center frequency: {center_freq:.4f} GHz")
    _log(f"  Span: {span:.3f} GHz")
    _log(f"  Number of points: {num_points}")
    _log(f"  Drive amplitude: {drive_amplitude:.3f}")
    _log(f"  Averages: {num_averages}")
    _log("-" * 60)

    # Calculate execution time
    # Qubit experiments typically take longer due to state preparation (10x for testing)
    base_time = 30.0
    point_time = num_points * 0.2
    avg_time = num_averages * 0.003
    total_time = base_time + point_time + avg_time

    _log(f"  Estimated execution time: {total_time:.1f} seconds")
    _log("-" * 60)

    # Simulate measurement phases
    phases = [
        ("Initializing qubit control", 0.5),
        ("Calibrating readout", 0.8),
        ("Configuring pulse sequence", 0.3),
    ]

    for phase_name, phase_time in phases:
        _log(f"  [{time.strftime('%H:%M:%S')}] {phase_name}...")
        time.sleep(phase_time)

    # Data acquisition with progress
    acq_time = total_time * 0.5
    num_chunks = 5
    chunk_time = acq_time / num_chunks

    _log(f"  [{time.strftime('%H:%M:%S')}] Acquiring data...")
    for i in range(num_chunks):
        time.sleep(0.1)
        progress = (i + 1) * 100 // num_chunks
        _log(
            f"      Progress: {progress}% ({(i+1)*num_averages//num_chunks}/{num_averages} averages)"
        )

    _log(f"  [{time.strftime('%H:%M:%S')}] Analyzing spectrum...")
    time.sleep(0.1)

    _log("-" * 60)

    # Generate simulated data
    frequencies = np.linspace(
        center_freq - span / 2, center_freq + span / 2, num_points
    )

    # Qubit response (Lorentzian peak)
    t2_star = 5.0  # us
    linewidth = 1000 / (np.pi * t2_star) / 1000  # GHz

    # Check if qubit is in range
    qubit_in_range = (center_freq - span / 2) <= f_qubit <= (center_freq + span / 2)

    delta = frequencies - f_qubit
    if qubit_in_range:
        max_pop = min(0.8, drive_amplitude * 5)
        population = max_pop * linewidth**2 / (delta**2 + linewidth**2)
    else:
        population = np.zeros_like(frequencies)

    # Add noise
    noise_level = 0.02 / np.sqrt(num_averages / 1000)
    population_noisy = np.clip(
        population + np.random.normal(0, noise_level, num_points), 0, 1
    )

    # Find peak
    peak_idx = np.argmax(population_noisy)
    fitted_freq = frequencies[peak_idx]
    peak_value = population_noisy[peak_idx]
    snr = peak_value / noise_level if noise_level > 0 else 0

    _log(f"  Qubit frequency: {fitted_freq:.6f} GHz")
    _log(f"  Peak population: {peak_value:.3f}")
    _log(f"  SNR: {snr:.1f}")
    _log(f"  Qubit in search range: {qubit_in_range}")
    _log("=" * 60)
    _log("QUBIT SPECTROSCOPY - Complete")
    _log("=" * 60)

    return {
        "status": "success",
        "data": {
            "frequencies": {
                "type": "array",
                "value": frequencies.tolist(),
                "unit": "GHz",
                "name": "Drive frequencies",
            },
            "excited_population": {
                "type": "array",
                "value": population_noisy.tolist(),
                "unit": "probability",
                "name": "Excited state population",
            },
            "qubit_freq": {
                "type": "scalar",
                "value": float(fitted_freq),
                "unit": "GHz",
                "name": "Fitted qubit transition frequency",
            },
            "snr": {
                "type": "scalar",
                "value": float(snr),
                "unit": "dimensionless",
                "name": "Signal-to-noise ratio",
            },
        },
        "plots": [
            {
                "name": "Qubit spectroscopy response",
                "format": "plotly",
                "data": {
                    "data": [
                        {
                            "x": frequencies.tolist(),
                            "y": population_noisy.tolist(),
                            "type": "scatter",
                            "mode": "lines+markers",
                            "name": "Population",
                            "marker": {"size": 4},
                        }
                    ],
                    "layout": {
                        "title": f"Qubit Spectroscopy - f_01 = {fitted_freq:.4f} GHz",
                        "xaxis": {"title": "Drive Frequency (GHz)"},
                        "yaxis": {"title": "Excited State Population", "range": [0, 1]},
                    },
                },
            }
        ],
    }
