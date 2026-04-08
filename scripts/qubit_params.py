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

"""Qubit-specific parameter generation with reproducible randomness."""

import re
import numpy as np


def _get_qubit_params(qubit: str) -> dict:
    """Get reproducible qubit-specific parameters seeded by qubit ID.

    Args:
        qubit: Qubit identifier string (e.g., "Q0", "Q1", "Q12")

    Returns:
        Dictionary with qubit-specific physical parameters
    """
    # Extract number from qubit string (Q0 -> 0, Q12 -> 12, qubit_5 -> 5)
    match = re.search(r'\d+', qubit)
    qubit_num = int(match.group()) if match else 0

    # Create reproducible RNG seeded by qubit number
    rng = np.random.default_rng(seed=qubit_num)

    # Generate parameters with realistic variations
    return {
        "qubit_freq": 4.85 + rng.uniform(-0.3, 0.3),       # 4.55-5.15 GHz
        "resonator_freq": 6.02 + rng.uniform(-0.2, 0.2),   # 5.82-6.22 GHz
        "pi_amp": 0.32 * (1 + rng.uniform(-0.15, 0.15)),   # ±15%
        "t1": 45.0 * (1 + rng.uniform(-0.3, 0.3)),         # 31-58 µs
        "t2_star": 12.0 * (1 + rng.uniform(-0.3, 0.3)),    # 8-16 µs
        "q_factor": 5000 * (1 + rng.uniform(-0.2, 0.2)),   # 4000-6000
    }


# Public alias (not discovered as experiment since it's not a function def)
get_qubit_params = _get_qubit_params
