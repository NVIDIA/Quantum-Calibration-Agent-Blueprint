# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Integration proof for the upstream QCA experiment adapters."""

from __future__ import annotations

import sys
import threading
from pathlib import Path

from werkzeug.serving import make_server

from qca_lite_twin.app import create_app
from qca_lite_twin.simulator import Runtime


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


def test_upstream_qca_adapters_complete_the_calibration_chain(monkeypatch):
    from scripts.lite_qubit_spectroscopy import lite_qubit_spectroscopy
    from scripts.lite_rabi_amplitude import lite_rabi_amplitude
    from scripts.lite_ramsey_frequency import lite_ramsey_frequency
    from scripts.lite_resonator_spectroscopy import lite_resonator_spectroscopy
    from scripts.lite_t1 import lite_t1

    server = make_server("127.0.0.1", 0, create_app(Runtime("cpu")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        monkeypatch.setenv("QCA_LITE_TWIN_URL", base_url)

        import requests

        response = requests.post(
            f"{base_url}/sessions",
            json={"profile": "qca-lite-1q", "n_qubits": 1, "seed": 17},
            timeout=5,
        )
        response.raise_for_status()
        session_id = response.json()["session_id"]
        monkeypatch.setenv("QCA_LITE_TWIN_SESSION_ID", session_id)

        results = [
            lite_resonator_spectroscopy(points=41, shots=64, seed=1),
            lite_qubit_spectroscopy(points=41, shots=64, seed=2),
            lite_rabi_amplitude(points=41, shots=64, seed=3),
            lite_ramsey_frequency(points=41, shots=64, seed=4),
            lite_t1(points=31, shots=64, seed=5),
        ]

        assert [result["status"] for result in results] == ["success"] * 5
        assert all(len(result["plots"]) == 1 for result in results)
        assert all(
            result["data"]["backend_provenance"]["value"]["dynamics"][
                "engine_used"
            ]
            == "qutip"
            for result in results
        )
        assert results[-1]["data"]["configuration_applied"]["value"] is False

        config = requests.get(
            f"{base_url}/device/{session_id}/config", timeout=5
        ).json()
        assert config["config_version"] == 5
    finally:
        server.shutdown()
        thread.join(timeout=5)
