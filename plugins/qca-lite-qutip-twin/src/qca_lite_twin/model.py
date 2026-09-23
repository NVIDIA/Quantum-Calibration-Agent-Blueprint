# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Device truth/configuration for the intentionally small QCA Lite twin."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from dataclasses import dataclass
from typing import Any, Mapping


PROFILE_BUILD_VERSION = 1
SUPPORTED_PROFILES = {"qca-lite-1q": 1, "qca-lite-2q": 2}


class ModelError(ValueError):
    """Invalid profile, truth document, or public configuration patch."""


def _number(value: Any, name: str, *, positive: bool = False,
            probability: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ModelError(f"{name} must be a finite number")
    if positive and result <= 0:
        raise ModelError(f"{name} must be > 0")
    if probability and not 0 <= result < 1:
        raise ModelError(f"{name} must be in [0, 1)")
    return result


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ModelError(f"{name} must be an integer >= {minimum}")
    return value


def _keys(value: Mapping[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ModelError(f"{name} has unknown field(s): {', '.join(unknown)}")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode()).hexdigest()


@dataclass
class Device:
    profile: str
    seed: int
    truth_mode: str
    truth: dict[str, Any]
    config: dict[str, Any]
    config_version: int = 0

    @property
    def qubit_ids(self) -> list[int]:
        return sorted(int(key) for key in self.truth["qubits"])

    @property
    def edges(self) -> list[list[int]]:
        return [list(edge) for edge in self.truth.get("edges", [])]

    @property
    def truth_digest(self) -> str:
        return digest({"build": PROFILE_BUILD_VERSION, "truth": self.truth})

    def public_config(self) -> dict[str, Any]:
        return copy.deepcopy(self.config)

    def patch(self, patch: Mapping[str, Any]) -> None:
        if not isinstance(patch, Mapping):
            raise ModelError("configuration patch must be an object")
        _keys(patch, {"qubit", "fields", "readout", "gate", "overrides"}, "patch")
        q_raw = patch.get("qubit")
        q = _integer(q_raw, "qubit")
        key = str(q)
        if key not in self.config["qubits"]:
            raise ModelError(f"unknown qubit {q}")
        updated = copy.deepcopy(self.config)
        qcfg = updated["qubits"][key]
        kinds = sum(name in patch for name in ("fields", "readout", "gate"))
        if kinds != 1:
            raise ModelError("patch must select exactly one of fields, readout, or gate")
        if "overrides" in patch and "gate" not in patch:
            raise ModelError("overrides is valid only with a gate patch")
        if "fields" in patch:
            fields = patch["fields"]
            if not isinstance(fields, Mapping):
                raise ModelError("fields must be an object")
            _keys(fields, {"drive_freq", "vz_frame"}, "fields")
            if not fields:
                raise ModelError("fields must not be empty")
            if "drive_freq" in fields:
                qcfg["drive_freq"] = _number(
                    fields["drive_freq"], "drive_freq", positive=True)
            if "vz_frame" in fields:
                qcfg["vz_frame"] = _number(fields["vz_frame"], "vz_frame")
        elif "readout" in patch:
            readout = patch["readout"]
            if not isinstance(readout, Mapping):
                raise ModelError("readout must be an object")
            _keys(readout, {"freq", "amp", "width", "threshold"}, "readout")
            if not readout:
                raise ModelError("readout must not be empty")
            for name, value in readout.items():
                qcfg["readout"][name] = _number(
                    value, f"readout.{name}", positive=name in {"freq", "width"})
        else:
            gate = patch.get("gate")
            overrides = patch.get("overrides")
            if not isinstance(gate, str) or gate not in qcfg["pulses"]:
                raise ModelError(f"qubit {q} has no calibrated gate {gate!r}")
            if not isinstance(overrides, Mapping) or not overrides:
                raise ModelError("gate overrides must be a non-empty object")
            _keys(overrides, {"shape", "amp", "phase", "width"}, "overrides")
            pulse = qcfg["pulses"][gate]
            for name, value in overrides.items():
                if name == "shape":
                    if value not in {"square", "gaussian"}:
                        raise ModelError("shape must be square or gaussian")
                    pulse[name] = value
                else:
                    pulse[name] = _number(
                        value, f"pulse.{name}", positive=name == "width")
        self.config = updated
        self.config_version += 1

    def reset(self) -> None:
        """Restore the public configuration without changing immutable truth."""
        self.config = _initial_config(self.truth)
        self.config_version += 1


def _validate_qubit_truth(raw: Mapping[str, Any], name: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ModelError(f"{name} must be an object")
    allowed = {
        "f01_hz", "drive_scale_hz_per_amp", "t1_us", "tphi_us",
        "resonator_freq_hz", "kappa_hz", "chi_hz", "iq_centers",
        "readout_noise", "assignment_error",
    }
    _keys(raw, allowed, name)
    missing = sorted(allowed - set(raw))
    if missing:
        raise ModelError(f"{name} is missing: {', '.join(missing)}")
    centers = raw["iq_centers"]
    if (not isinstance(centers, list) or len(centers) != 2
            or any(not isinstance(pair, list) or len(pair) != 2 for pair in centers)):
        raise ModelError(f"{name}.iq_centers must contain two [real, imag] pairs")
    return {
        "f01_hz": _number(raw["f01_hz"], f"{name}.f01_hz", positive=True),
        "drive_scale_hz_per_amp": _number(
            raw["drive_scale_hz_per_amp"], f"{name}.drive_scale_hz_per_amp", positive=True),
        "t1_us": _number(raw["t1_us"], f"{name}.t1_us", positive=True),
        "tphi_us": _number(raw["tphi_us"], f"{name}.tphi_us", positive=True),
        "resonator_freq_hz": _number(
            raw["resonator_freq_hz"], f"{name}.resonator_freq_hz", positive=True),
        "kappa_hz": _number(raw["kappa_hz"], f"{name}.kappa_hz", positive=True),
        "chi_hz": _number(raw["chi_hz"], f"{name}.chi_hz"),
        "iq_centers": [
            [_number(pair[0], f"{name}.iq_centers"),
             _number(pair[1], f"{name}.iq_centers")]
            for pair in centers
        ],
        "readout_noise": _number(
            raw["readout_noise"], f"{name}.readout_noise", positive=True),
        "assignment_error": _number(
            raw["assignment_error"], f"{name}.assignment_error", probability=True),
    }


def validate_truth(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ModelError("truth must be an object")
    _keys(raw, {"qubits", "edges", "static_zz_hz", "cz_rate_hz"}, "truth")
    qubits = raw.get("qubits")
    if not isinstance(qubits, Mapping) or not 1 <= len(qubits) <= 2:
        raise ModelError("truth.qubits must contain one or two qubits")
    parsed_qubits: dict[str, Any] = {}
    for key, value in qubits.items():
        try:
            q = int(key)
        except (TypeError, ValueError) as exc:
            raise ModelError(f"invalid qubit id {key!r}") from exc
        if str(q) != str(key) or q < 0:
            raise ModelError(f"invalid qubit id {key!r}")
        parsed_qubits[str(q)] = _validate_qubit_truth(value, f"truth.qubits.{q}")
    expected_ids = {str(index) for index in range(len(parsed_qubits))}
    if set(parsed_qubits) != expected_ids:
        raise ModelError("truth qubit ids must be contiguous from 0")
    edges_raw = raw.get("edges", [])
    if not isinstance(edges_raw, list):
        raise ModelError("truth.edges must be an array")
    edges: list[list[int]] = []
    known = {int(key) for key in parsed_qubits}
    for index, edge in enumerate(edges_raw):
        if (not isinstance(edge, list) or len(edge) != 2
                or any(isinstance(q, bool) or not isinstance(q, int) for q in edge)):
            raise ModelError(f"truth.edges[{index}] must be [int, int]")
        a, b = sorted(edge)
        if a == b or a not in known or b not in known or [a, b] in edges:
            raise ModelError(f"invalid truth edge {edge!r}")
        edges.append([a, b])
    if len(parsed_qubits) == 2 and not edges:
        raise ModelError("a two-qubit truth requires one edge")
    return {
        "qubits": dict(sorted(parsed_qubits.items(), key=lambda item: int(item[0]))),
        "edges": sorted(edges),
        "static_zz_hz": _number(raw.get("static_zz_hz", 0.0), "truth.static_zz_hz"),
        "cz_rate_hz": _number(raw.get("cz_rate_hz", 5.0e6), "truth.cz_rate_hz", positive=True),
    }


def _seeded_truth(n_qubits: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    qubits: dict[str, Any] = {}
    for q in range(n_qubits):
        qubits[str(q)] = {
            "f01_hz": rng.uniform(4.97e9, 5.03e9),
            "drive_scale_hz_per_amp": rng.uniform(118e6, 132e6),
            "t1_us": rng.uniform(24.0, 42.0),
            "tphi_us": rng.uniform(30.0, 55.0),
            "resonator_freq_hz": rng.uniform(6.77e9, 6.83e9),
            "kappa_hz": rng.uniform(1.5e6, 2.5e6),
            "chi_hz": rng.uniform(-0.8e6, -0.3e6),
            "iq_centers": [[1.0, 0.0], [-1.0, 0.0]],
            "readout_noise": rng.uniform(0.06, 0.10),
            "assignment_error": rng.uniform(0.005, 0.02),
        }
    return validate_truth({
        "qubits": qubits,
        "edges": [[0, 1]] if n_qubits == 2 else [],
        "static_zz_hz": 60e3 if n_qubits == 2 else 0.0,
        "cz_rate_hz": 5e6,
    })


def _initial_config(truth: Mapping[str, Any]) -> dict[str, Any]:
    qubits: dict[str, Any] = {}
    for key in truth["qubits"]:
        qubits[key] = {
            "drive_freq": 5.0e9,
            "vz_frame": 0.0,
            "pulses": {
                "X": {"shape": "square", "amp": 0.10, "phase": 0.0, "width": 40.0},
                "X90": {"shape": "square", "amp": 0.05, "phase": 0.0, "width": 40.0},
                "Y90": {"shape": "square", "amp": 0.05,
                         "phase": math.pi / 2.0, "width": 40.0},
            },
            "readout": {"freq": 6.8e9, "amp": 0.1, "width": 300.0, "threshold": 0.0},
        }
    couplers = {
        f"{a}-{b}": {"gates": {"CZ": {
            "shape": "square", "amp": 1.0, "phase": 0.0, "width": 100.0,
        }}}
        for a, b in truth.get("edges", [])
    }
    return {"qubits": qubits, "couplers": couplers}


def provision(request: Any) -> Device:
    if not isinstance(request, Mapping):
        raise ModelError("session request must be an object")
    mode = request.get("truth_mode", "seeded")
    if mode not in {"seeded", "explicit"}:
        raise ModelError("truth_mode must be seeded or explicit")
    seed = _integer(request.get("seed", 0), "seed")
    if mode == "seeded":
        _keys(request, {"truth_mode", "profile", "n_qubits", "seed"}, "session")
        profile = request.get("profile", "qca-lite-1q")
        if profile not in SUPPORTED_PROFILES:
            raise ModelError(f"unsupported profile {profile!r}")
        n_qubits = _integer(
            request.get("n_qubits", SUPPORTED_PROFILES[profile]), "n_qubits", minimum=1)
        if n_qubits != SUPPORTED_PROFILES[profile]:
            raise ModelError(f"profile {profile!r} requires {SUPPORTED_PROFILES[profile]} qubits")
        truth = _seeded_truth(n_qubits, seed)
    else:
        _keys(request, {"truth_mode", "profile", "seed", "truth"}, "session")
        if "truth" not in request:
            raise ModelError("explicit mode requires truth")
        profile = request.get("profile", "qca-lite-explicit")
        if not isinstance(profile, str) or not profile.strip():
            raise ModelError("profile must be a non-empty string")
        truth = validate_truth(request["truth"])
    return Device(
        profile=str(profile), seed=seed, truth_mode=mode, truth=truth,
        config=_initial_config(truth),
    )
