# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Focused contracts for the small QuTiP twin."""

import builtins
import copy
import math

import pytest

from scripts._lite_twin.app import create_app
from scripts._lite_twin.model import ModelError, provision
from scripts._lite_twin.simulator import Runtime, SimulationError, resolve_runtime, run


def _truth(*, t1_us=20.0, tphi_us=1.0e9):
    return {
        "qubits": {"0": {
            "f01_hz": 5.0e9,
            "drive_scale_hz_per_amp": 125.0e6,
            "t1_us": t1_us,
            "tphi_us": tphi_us,
            "resonator_freq_hz": 6.8e9,
            "kappa_hz": 2.0e6,
            "chi_hz": -0.5e6,
            "iq_centers": [[1.0, 0.0], [-1.0, 0.0]],
            "readout_noise": 0.08,
            "assignment_error": 0.01,
        }},
        "edges": [],
        "static_zz_hz": 0.0,
        "cz_rate_hz": 5.0e6,
    }


def _primitive(name, **arguments):
    return {"op": "primitive", "name": name, "arguments": arguments}


def _serial(*children):
    return {"op": "serial", "children": list(children)}


def _populations(device, program, *, sweep=None):
    body = {
        "program": program,
        "shots": 32,
        "returns": {"r0": "populations"},
        "seed": 3,
    }
    if sweep is not None:
        body["sweep"] = {"axes": sweep}
    return run(device, body, Runtime("cpu"))["records"]["r0"]["data"]


def test_truth_modes_are_reproducible_hidden_and_immutable():
    request = {"profile": "qca-lite-1q", "n_qubits": 1, "seed": 7}
    first = provision(request)
    second = provision(request)
    assert first.truth_digest == second.truth_digest
    assert first.truth_digest != provision({**request, "seed": 8}).truth_digest

    explicit = {"truth_mode": "explicit", "profile": "fixture", "seed": 4,
                "truth": _truth()}
    assert provision(explicit).truth_digest == provision(copy.deepcopy(explicit)).truth_digest
    before = first.truth_digest
    first.patch({"qubit": 0, "fields": {"drive_freq": 5.01e9}})
    assert first.truth_digest == before
    snapshot = first.public_config()
    with pytest.raises(ModelError):
        first.patch({"qubit": 0, "fields": {"drive_freq": -1.0},
                     "readout": {"freq": 6.8e9}})
    assert first.public_config() == snapshot
    with pytest.raises(ModelError):
        provision({**explicit, "n_qubits": 1})
    with pytest.raises(ModelError):
        provision({**request, "truth": _truth()})


def test_real_qutip_x_ramsey_and_t1_evolution():
    device = provision({"truth_mode": "explicit", "profile": "physics", "seed": 1,
                        "truth": _truth()})
    device.patch({"qubit": 0, "fields": {"drive_freq": 5.0e9}})
    x = _serial(
        _primitive("q0.drive", amp=0.1, width=40.0, phase=0.0),
        _primitive("q0.measure", record="r0"),
    )
    assert _populations(device, x)[0][1] > 0.99

    ramsey = _serial(
        _primitive("q0.drive", amp=0.05, width=40.0, phase=0.0, freq=5.002e9),
        _primitive("q0.delay", duration_ns="$t", freq=5.002e9),
        _primitive("q0.drive", amp=0.05, width=40.0, phase=0.0, freq=5.002e9),
        _primitive("q0.measure", record="r0"),
    )
    fringe = _populations(
        device, ramsey,
        sweep=[{"name": "t", "kind": "bind", "values": [0.0, 250.0]}],
    )
    assert fringe[0][1] > 0.9 and fringe[1][1] < 0.11

    t1 = _serial(
        _primitive("q0.drive", amp=0.1, width=40.0, phase=0.0),
        _primitive("q0.delay", duration_ns=20000.0),
        _primitive("q0.measure", record="r0"),
    )
    assert _populations(device, t1)[0][1] == pytest.approx(math.exp(-1.002), abs=0.01)

    dephasing_device = provision({
        "truth_mode": "explicit", "profile": "dephasing", "seed": 1,
        "truth": _truth(t1_us=1.0e9, tphi_us=1.0),
    })
    dephasing_device.patch({"qubit": 0, "fields": {"drive_freq": 5.0e9}})
    echo = _serial(
        _primitive("q0.drive", amp=0.05, width=40.0, phase=0.0),
        _primitive("q0.delay", duration_ns=1000.0, freq=5.0e9),
        _primitive("q0.drive", amp=0.05, width=40.0, phase=0.0),
        _primitive("q0.measure", record="r0"),
    )
    expected = 0.5 * (1.0 + math.exp(-1.0))
    assert _populations(dephasing_device, echo)[0][1] == pytest.approx(expected, abs=0.05)


def test_http_subset_is_safe_and_twin_client_shaped():
    client = create_app(Runtime("cpu")).test_client()
    created = client.post("/sessions", json={
        "truth_mode": "explicit", "profile": "fixture", "seed": 2, "truth": _truth(),
    })
    assert created.status_code == 201
    assert b"f01_hz" not in created.data and b"drive_scale_hz_per_amp" not in created.data
    session_id = created.get_json()["device_session"]
    assert client.get(f"/sessions/{session_id}").get_json()["status"] == "active"
    baseline = client.get(f"/device/{session_id}/config").get_json()["config"]
    patched = client.patch(
        f"/device/{session_id}/config",
        json={"qubit": 0, "fields": {"drive_freq": 5.01e9}},
    )
    assert patched.status_code == 200
    reset = client.post(f"/device/{session_id}/reset", json={}).get_json()
    assert reset["config"] == baseline
    probe = client.post(f"/device/{session_id}/run", json={
        "program": _primitive("q0.measure", record="r0"),
        "shots": 1, "returns": {"r0": "populations"}, "seed": 2,
    })
    assert probe.status_code == 200
    assert probe.get_json()["provenance"]["dynamics"]["engine_used"] == "qutip"


def test_readout_is_seeded_and_cpu_refuses_two_qubit_evolution():
    device = provision({"profile": "qca-lite-1q", "n_qubits": 1, "seed": 12})
    request = {
        "program": _primitive("q0.measure", record="r0"),
        "shots": 512,
        "returns": {"r0": "iq_shot"},
        "seed": 99,
    }
    assert run(device, request, Runtime("cpu"))["records"] == run(
        device, request, Runtime("cpu"))["records"]

    two_qubit = provision({"profile": "qca-lite-2q", "n_qubits": 2, "seed": 12})
    with pytest.raises(SimulationError, match="two-qubit evolution requires CUDA"):
        run(two_qubit, {
            "program": _primitive("q0.measure", record="r0"),
            "shots": 1,
            "returns": {"r0": "populations"},
        }, Runtime("cpu"))


def test_cuda_requests_fail_closed_when_activation_is_unavailable(monkeypatch):
    real_import = builtins.__import__

    def unavailable(name, *args, **kwargs):
        if name == "qutip_cuquantum":
            raise ImportError("simulated missing CUDA layer")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", unavailable)
    assert resolve_runtime("auto").data_layer == "cpu"
    with pytest.raises(SimulationError, match="CUDA activation unavailable"):
        resolve_runtime("cuda")
