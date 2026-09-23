# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Live CUDA activation proof for the QCA Lite twin."""

import pytest

from scripts._lite_twin.model import provision
from scripts._lite_twin.simulator import resolve_runtime, run


@pytest.mark.gpu
def test_lite_twin_uses_cuda_after_a_real_probe():
    runtime = resolve_runtime("auto")
    if runtime.data_layer != "cuda":
        pytest.skip(runtime.fallback_reason or "QuTiP CUDA layer unavailable")
    device = provision({"profile": "qca-lite-1q", "n_qubits": 1, "seed": 5})
    bundle = run(device, {
        "program": {"op": "serial", "children": [
            {"op": "primitive", "name": "q0.X", "arguments": {}},
            {"op": "primitive", "name": "q0.measure", "arguments": {"record": "r0"}},
        ]},
        "shots": 8,
        "returns": {"r0": "populations"},
        "seed": 5,
        "options": {"engine": "qutip", "qutip_data_layer": "cuda"},
    }, runtime)
    assert bundle["provenance"]["dynamics"]["data_layer_used"] == "cuda"
