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

"""Mock T1 measurement with realistic wall-clock execution time."""

import json
import sys
import time
from typing import Annotated

import numpy as np

from .qubit_params import get_qubit_params


# Redirect progress output to stderr so stdout only has JSON result
def _log(msg):
    print(msg, file=sys.stderr, flush=True)


def t1_measurement(
    qubit: str = "Q0",
    max_delay: Annotated[float, (10.0, 500.0)] = 100.0,
    num_points: Annotated[int, (21, 101)] = 51,
    num_averages: Annotated[int, (1000, 50000)] = 10000,
) -> dict:
    """Perform T1 relaxation time measurement.

    Applies pi pulse then measures decay vs wait time.
    Includes realistic execution time simulation.

    Args:
        max_delay: Maximum delay time in microseconds
        num_points: Number of delay points
        num_averages: Number of measurement averages

    Returns:
        delays: Array of delay times (us)
        excited_population: Measured excited state population
        t1_time: Fitted T1 relaxation time (us)
    """
    # Get qubit-specific parameters
    params = get_qubit_params(qubit)
    true_t1 = params["t1"]

    _log("=" * 60)
    _log(f"T1 MEASUREMENT [{qubit}] - Starting measurement")
    _log("=" * 60)
    _log(f"  Qubit: {qubit}")
    _log(f"  Max delay: {max_delay:.1f} us")
    _log(f"  Number of points: {num_points}")
    _log(f"  Averages: {num_averages}")
    _log("-" * 60)

    # T1 measurements typically take longer due to long delays (10x for testing)
    base_time = 40.0
    # Each point requires waiting for the delay time (scaled)
    delay_factor = max_delay / 100.0  # Normalize to 100us reference
    point_time = num_points * 0.3 * delay_factor
    avg_time = num_averages * 0.002
    total_time = base_time + point_time + avg_time

    _log(f"  Estimated execution time: {total_time:.1f} seconds")
    _log("-" * 60)

    # Simulate measurement phases
    _log(f"  [{time.strftime('%H:%M:%S')}] Verifying pi pulse calibration...")
    time.sleep(0.1)

    _log(f"  [{time.strftime('%H:%M:%S')}] Configuring delay sequence...")
    time.sleep(0.1)

    _log(f"  [{time.strftime('%H:%M:%S')}] Running T1 decay measurement...")

    # Progress updates
    acq_time = total_time * 0.65
    checkpoints = [0, 25, 50, 75, 100]
    for i, pct in enumerate(checkpoints[:-1]):
        next_pct = checkpoints[i + 1]
        delay_at_checkpoint = max_delay * next_pct / 100
        time.sleep(0.1)
        _log(f"      {next_pct}% complete (delay = {delay_at_checkpoint:.1f} us)")

    _log(f"  [{time.strftime('%H:%M:%S')}] Fitting exponential decay...")
    time.sleep(0.1)

    _log("-" * 60)

    # Generate simulated data
    delays = np.linspace(0, max_delay, num_points)

    # T1 decay: P_e = A * exp(-t/T1) + B
    amplitude = 0.92
    offset = 0.03

    population = amplitude * np.exp(-delays / true_t1) + offset

    # Add noise
    noise_level = 0.012 / np.sqrt(num_averages / 1000)
    population_noisy = np.clip(
        population + np.random.normal(0, noise_level, num_points), 0, 1
    )

    # Fit T1 (simple estimate from 1/e point)
    target = amplitude / np.e + offset
    for i, pop in enumerate(population_noisy):
        if pop < target:
            fitted_t1 = delays[i] * (1 + np.random.normal(0, 0.05))
            break
    else:
        fitted_t1 = true_t1 * (1 + np.random.normal(0, 0.05))

    _log(f"  T1 relaxation time: {fitted_t1:.2f} us")
    _log(f"  Initial population: {population_noisy[0]:.3f}")
    _log(f"  Final population: {population_noisy[-1]:.3f}")
    _log("=" * 60)
    _log("T1 MEASUREMENT - Complete")
    _log("=" * 60)

    return {
        "status": "success",
        "data": {
            "delays": {
                "type": "array",
                "value": delays.tolist(),
                "unit": "us",
                "name": "Delay times",
            },
            "excited_population": {
                "type": "array",
                "value": population_noisy.tolist(),
                "unit": "probability",
                "name": "Excited state population",
            },
            "t1_time": {
                "type": "scalar",
                "value": float(fitted_t1),
                "unit": "us",
                "name": "Fitted T1 relaxation time",
            },
        },
        "plots": [
            {
                "name": "T1 decay measurement",
                "format": "plotly",
                "data": {
                    "data": [
                        {
                            "x": delays.tolist(),
                            "y": population_noisy.tolist(),
                            "type": "scatter",
                            "mode": "markers",
                            "name": "Data",
                            "marker": {"size": 6},
                        },
                        {
                            "x": delays.tolist(),
                            "y": (
                                amplitude * np.exp(-delays / fitted_t1) + offset
                            ).tolist(),
                            "type": "scatter",
                            "mode": "lines",
                            "name": f"Fit (T1={fitted_t1:.1f} us)",
                            "line": {"color": "red"},
                        },
                    ],
                    "layout": {
                        "title": f"T1 Measurement - T1 = {fitted_t1:.2f} µs",
                        "xaxis": {"title": "Delay Time (µs)"},
                        "yaxis": {"title": "Excited State Population", "range": [0, 1]},
                    },
                },
            }
        ],
    }
