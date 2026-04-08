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

"""Mock Rabi oscillation with realistic wall-clock execution time."""

import json
import sys
import time
from typing import Annotated

import numpy as np

from .qubit_params import get_qubit_params


# Redirect progress output to stderr so stdout only has JSON result
def _log(msg):
    print(msg, file=sys.stderr, flush=True)


def rabi_oscillation(
    qubit: str = "Q0",
    max_amplitude: Annotated[float, (0.1, 1.0)] = 0.5,
    num_points: Annotated[int, (21, 101)] = 51,
    pulse_width: Annotated[float, (0.01, 0.5)] = 0.1,
    num_averages: Annotated[int, (500, 20000)] = 5000,
) -> dict:
    """Perform Rabi oscillation measurement.

    Sweeps drive amplitude to calibrate pi pulse.
    Includes realistic execution time simulation.

    Args:
        max_amplitude: Maximum drive amplitude (a.u.)
        num_points: Number of amplitude points
        pulse_width: Pulse width in microseconds
        num_averages: Number of measurement averages

    Returns:
        amplitudes: Array of drive amplitudes
        excited_population: Measured excited state population
        pi_amplitude: Calibrated pi pulse amplitude
    """
    # Get qubit-specific parameters
    params = get_qubit_params(qubit)
    true_pi_amp = params["pi_amp"]

    _log("=" * 60)
    _log(f"RABI OSCILLATION [{qubit}] - Starting measurement")
    _log("=" * 60)
    _log(f"  Qubit: {qubit}")
    _log(f"  Max amplitude: {max_amplitude:.3f}")
    _log(f"  Number of points: {num_points}")
    _log(f"  Pulse width: {pulse_width:.3f} us")
    _log(f"  Averages: {num_averages}")
    _log("-" * 60)

    # Calculate execution time (10x for testing)
    base_time = 25.0
    point_time = num_points * 0.15
    avg_time = num_averages * 0.004
    total_time = base_time + point_time + avg_time

    _log(f"  Estimated execution time: {total_time:.1f} seconds")
    _log("-" * 60)

    # Simulate measurement phases
    _log(f"  [{time.strftime('%H:%M:%S')}] Loading pulse calibration...")
    time.sleep(0.1)

    _log(f"  [{time.strftime('%H:%M:%S')}] Configuring AWG...")
    time.sleep(0.1)

    _log(f"  [{time.strftime('%H:%M:%S')}] Running amplitude sweep...")

    # Progress updates during acquisition
    acq_time = total_time * 0.6
    for i in range(num_points):
        if i % (num_points // 5) == 0 or i == num_points - 1:
            _log(
                f"      Point {i+1}/{num_points} (amplitude = {max_amplitude * (i+1) / num_points:.3f})"
            )
        time.sleep(0.1)

    _log(f"  [{time.strftime('%H:%M:%S')}] Fitting Rabi oscillation...")
    time.sleep(0.1)

    _log("-" * 60)

    # Generate simulated data
    amplitudes = np.linspace(0, max_amplitude, num_points)

    # Rabi oscillation: P_e = sin^2(pi * amp / amp_pi)
    rabi_freq = 1 / (2 * true_pi_amp)  # Oscillation frequency vs amplitude

    population = np.sin(np.pi * amplitudes / true_pi_amp) ** 2

    # Add decoherence and noise
    decay = np.exp(-((amplitudes / max_amplitude) ** 2) * 0.3)
    population = 0.5 + (population - 0.5) * decay

    noise_level = 0.015 / np.sqrt(num_averages / 1000)
    population_noisy = np.clip(
        population + np.random.normal(0, noise_level, num_points), 0, 1
    )

    # Find pi pulse amplitude (first maximum)
    # Simple: find first point where population starts decreasing after rising
    for i in range(1, len(population_noisy) - 1):
        if (
            population_noisy[i] > population_noisy[i - 1]
            and population_noisy[i] > population_noisy[i + 1]
        ):
            if population_noisy[i] > 0.8:  # Must be a significant peak
                pi_amp = amplitudes[i]
                break
    else:
        pi_amp = true_pi_amp * (1 + np.random.normal(0, 0.02))

    pi_half_amp = pi_amp / 2

    _log(f"  Pi pulse amplitude: {pi_amp:.4f}")
    _log(f"  Pi/2 pulse amplitude: {pi_half_amp:.4f}")
    _log(f"  Rabi frequency: {1/(2*pi_amp):.2f} MHz/a.u.")
    _log("=" * 60)
    _log("RABI OSCILLATION - Complete")
    _log("=" * 60)

    return {
        "status": "success",
        "data": {
            "amplitudes": {
                "type": "array",
                "value": amplitudes.tolist(),
                "unit": "a.u.",
                "name": "Drive amplitudes",
            },
            "excited_population": {
                "type": "array",
                "value": population_noisy.tolist(),
                "unit": "probability",
                "name": "Excited state population",
            },
            "pi_amplitude": {
                "type": "scalar",
                "value": float(pi_amp),
                "unit": "a.u.",
                "name": "Calibrated pi pulse amplitude",
            },
            "pi_half_amplitude": {
                "type": "scalar",
                "value": float(pi_half_amp),
                "unit": "a.u.",
                "name": "Calibrated pi/2 pulse amplitude",
            },
        },
        "plots": [
            {
                "name": "Rabi oscillation measurement",
                "format": "plotly",
                "data": {
                    "data": [
                        {
                            "x": amplitudes.tolist(),
                            "y": population_noisy.tolist(),
                            "type": "scatter",
                            "mode": "lines+markers",
                            "name": "Data",
                            "marker": {"size": 5},
                        }
                    ],
                    "layout": {
                        "title": f"Rabi Oscillation - π amp = {pi_amp:.4f}",
                        "xaxis": {"title": "Drive Amplitude (a.u.)"},
                        "yaxis": {"title": "Excited State Population", "range": [0, 1]},
                        "shapes": [
                            {
                                "type": "line",
                                "x0": pi_amp,
                                "x1": pi_amp,
                                "y0": 0,
                                "y1": 1,
                                "line": {"color": "red", "dash": "dash"},
                            }
                        ],
                    },
                },
            }
        ],
    }
