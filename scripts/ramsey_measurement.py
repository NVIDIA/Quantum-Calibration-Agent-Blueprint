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

"""Mock Ramsey measurement with realistic wall-clock execution time."""

import json
import sys
import time
from typing import Annotated

import numpy as np

from .qubit_params import get_qubit_params


# Redirect progress output to stderr so stdout only has JSON result
def _log(msg):
    print(msg, file=sys.stderr, flush=True)


def ramsey_measurement(
    qubit: str = "Q0",
    max_delay: Annotated[float, (5.0, 100.0)] = 30.0,
    num_points: Annotated[int, (31, 151)] = 81,
    artificial_detuning: Annotated[float, (0.5, 10.0)] = 2.0,
    num_averages: Annotated[int, (1000, 50000)] = 10000,
) -> dict:
    """Perform Ramsey fringe measurement (T2* dephasing).

    Applies pi/2 - delay - pi/2 sequence to measure dephasing.
    Includes realistic execution time simulation.

    Args:
        max_delay: Maximum delay time in microseconds
        num_points: Number of delay points
        artificial_detuning: Intentional detuning for fringes (MHz)
        num_averages: Number of measurement averages

    Returns:
        delays: Array of delay times (us)
        excited_population: Measured excited state population
        t2_star: Fitted T2* dephasing time (us)
        detuning: Fitted frequency detuning (MHz)
    """
    # Get qubit-specific parameters
    params = get_qubit_params(qubit)
    true_t2_star = params["t2_star"]

    _log("=" * 60)
    _log(f"RAMSEY MEASUREMENT (T2*) [{qubit}] - Starting measurement")
    _log("=" * 60)
    _log(f"  Qubit: {qubit}")
    _log(f"  Max delay: {max_delay:.1f} us")
    _log(f"  Number of points: {num_points}")
    _log(f"  Artificial detuning: {artificial_detuning:.2f} MHz")
    _log(f"  Averages: {num_averages}")
    _log("-" * 60)

    # Ramsey is similar to T1 but with more complex pulse sequence (10x for testing)
    base_time = 50.0
    delay_factor = max_delay / 30.0
    point_time = num_points * 0.25 * delay_factor
    avg_time = num_averages * 0.0025
    total_time = base_time + point_time + avg_time

    _log(f"  Estimated execution time: {total_time:.1f} seconds")
    _log("-" * 60)

    # Simulate measurement phases
    _log(f"  [{time.strftime('%H:%M:%S')}] Calibrating pi/2 pulses...")
    time.sleep(0.1)

    _log(f"  [{time.strftime('%H:%M:%S')}] Setting detuning frequency...")
    time.sleep(0.1)

    _log(f"  [{time.strftime('%H:%M:%S')}] Running Ramsey sequence...")

    # Progress with fringe count
    acq_time = total_time * 0.6
    num_fringes_expected = int(artificial_detuning * max_delay * 2)

    for i in range(5):
        time.sleep(0.1)
        current_delay = max_delay * (i + 1) / 5
        fringes_so_far = int(artificial_detuning * current_delay * 2)
        _log(f"      Delay {current_delay:.1f} us - observed ~{fringes_so_far} fringes")

    _log(f"  [{time.strftime('%H:%M:%S')}] Fitting decay envelope...")
    time.sleep(0.1)

    _log(f"  [{time.strftime('%H:%M:%S')}] Extracting frequency...")
    time.sleep(0.1)

    _log("-" * 60)

    # Generate simulated data
    delays = np.linspace(0, max_delay, num_points)

    # Ramsey signal: P_e = 0.5 * (1 + cos(2*pi*delta*t) * exp(-t/T2*))
    true_detuning = artificial_detuning * (1 + np.random.normal(0, 0.02))

    phase = 2 * np.pi * true_detuning * delays  # MHz * us = dimensionless -> radians
    decay = np.exp(-delays / true_t2_star)

    population = 0.5 * (1 + np.cos(phase) * decay)

    # Add noise
    noise_level = 0.015 / np.sqrt(num_averages / 1000)
    population_noisy = np.clip(
        population + np.random.normal(0, noise_level, num_points), 0, 1
    )

    # Fit T2* (from envelope)
    # Find peaks and fit decay
    fitted_t2_star = true_t2_star * (1 + np.random.normal(0, 0.08))
    fitted_detuning = true_detuning * (1 + np.random.normal(0, 0.03))

    _log(f"  T2* dephasing time: {fitted_t2_star:.2f} us")
    _log(f"  Fitted detuning: {fitted_detuning:.3f} MHz")
    _log(f"  Number of fringes: ~{num_fringes_expected}")
    _log(f"  Fringe visibility: {decay[-1]*100:.1f}% at max delay")
    _log("=" * 60)
    _log("RAMSEY MEASUREMENT - Complete")
    _log("=" * 60)

    return {
        "status": "success",
        "data": {
            "delays": {
                "type": "array",
                "value": delays.tolist(),
                "unit": "us",
                "name": "Delay times between pi/2 pulses",
            },
            "excited_population": {
                "type": "array",
                "value": population_noisy.tolist(),
                "unit": "probability",
                "name": "Excited state population",
            },
            "t2_star": {
                "type": "scalar",
                "value": float(fitted_t2_star),
                "unit": "us",
                "name": "Fitted T2* dephasing time",
            },
            "detuning": {
                "type": "scalar",
                "value": float(fitted_detuning),
                "unit": "MHz",
                "name": "Fitted frequency detuning",
            },
        },
        "plots": [
            {
                "name": "Ramsey fringe measurement",
                "format": "plotly",
                "data": {
                    "data": [
                        {
                            "x": delays.tolist(),
                            "y": population_noisy.tolist(),
                            "type": "scatter",
                            "mode": "lines+markers",
                            "name": "Data",
                            "marker": {"size": 4},
                        },
                        {
                            "x": delays.tolist(),
                            "y": (
                                0.5 * (1 + np.exp(-delays / fitted_t2_star))
                            ).tolist(),
                            "type": "scatter",
                            "mode": "lines",
                            "name": "Upper envelope",
                            "line": {"color": "red", "dash": "dash"},
                        },
                        {
                            "x": delays.tolist(),
                            "y": (
                                0.5 * (1 - np.exp(-delays / fitted_t2_star))
                            ).tolist(),
                            "type": "scatter",
                            "mode": "lines",
                            "name": "Lower envelope",
                            "line": {"color": "red", "dash": "dash"},
                        },
                    ],
                    "layout": {
                        "title": f"Ramsey Fringes - T2* = {fitted_t2_star:.2f} µs, Δf = {fitted_detuning:.2f} MHz",
                        "xaxis": {"title": "Delay Time (µs)"},
                        "yaxis": {"title": "Excited State Population", "range": [0, 1]},
                    },
                },
            }
        ],
    }
