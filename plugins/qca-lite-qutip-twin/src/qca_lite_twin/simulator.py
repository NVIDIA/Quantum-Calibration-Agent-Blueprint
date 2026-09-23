# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""QuTiP evolution and measurement for the QCA Lite twin."""

from __future__ import annotations

import importlib.metadata
import itertools
import math
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from .model import Device


class SimulationError(ValueError):
    """Invalid program or unsupported simulation request."""


@dataclass(frozen=True)
class Runtime:
    data_layer: str
    fallback_reason: str | None = None
    work_stream: Any = None


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def resolve_runtime(requested: str) -> Runtime:
    """Resolve CPU/CUDA once at startup, proving CUDA with a real QuTiP solve."""
    requested = requested.strip().lower()
    if requested not in {"auto", "cpu", "cuda"}:
        raise SimulationError("data layer must be auto, cpu, or cuda")
    if requested == "cpu":
        return Runtime("cpu")
    try:
        cuda_root = Path("/usr/local/cuda")
        if "CUDA_PATH" not in os.environ and (cuda_root / "include" / "cuda.h").is_file():
            os.environ["CUDA_PATH"] = str(cuda_root)
            os.environ.setdefault("CUDA_HOME", str(cuda_root))
        import qutip as qt
        import qutip_cuquantum
        from cuquantum.densitymat import WorkStream

        stream = WorkStream()
        qutip_cuquantum.set_as_default(stream)
        result = qt.mesolve(
            0.25 * qt.sigmax(), qt.basis(2, 0), [0.0, 0.1],
            c_ops=[], e_ops=[],
            options={"method": "CuVern7", "store_final_state": True},
        )
        state = result.final_state
        norm = float(state.norm())
        if not math.isfinite(norm) or abs(norm - 1.0) > 1e-6:
            raise RuntimeError(f"CUDA probe returned state norm {norm}")
        return Runtime("cuda", work_stream=stream)
    except BaseException as exc:  # CUDA imports can raise non-Exception driver errors.
        reason = f"CUDA activation unavailable: {type(exc).__name__}: {exc}"
        if requested == "cuda":
            raise SimulationError(reason) from exc
        try:
            import qutip_cuquantum

            qutip_cuquantum.set_as_default(reverse=True)
        except BaseException:
            pass
        return Runtime("cpu", fallback_reason=reason)


def runtime_versions() -> dict[str, str]:
    versions = {
        "qutip": _version("qutip") or "unknown",
        "numpy": np.__version__,
        "qca_lite_twin": "1",
    }
    for package, key in (
        ("qutip-cuquantum", "qutip_cuquantum"),
        ("cuquantum-python-cu13", "cuquantum"),
    ):
        value = _version(package)
        if value is not None:
            versions[key] = value
    return versions


def _bind(value: Any, bindings: Mapping[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$"):
        name = value[1:]
        if name not in bindings:
            raise SimulationError(f"unbound symbol {value!r}")
        return bindings[name]
    if isinstance(value, list):
        return [_bind(item, bindings) for item in value]
    if isinstance(value, dict):
        return {key: _bind(item, bindings) for key, item in value.items()}
    return value


def _parse_primitive(node: Mapping[str, Any], bindings: Mapping[str, Any]) -> dict[str, Any]:
    if set(node) != {"op", "name", "arguments"}:
        raise SimulationError("primitive requires exactly op, name, and arguments")
    name = node["name"]
    args = node["arguments"]
    if not isinstance(name, str) or not isinstance(args, Mapping):
        raise SimulationError("primitive name/arguments are malformed")
    return {"name": name, "arguments": _bind(dict(args), bindings)}


def _expand(node: Any, bindings: Mapping[str, Any], *, budget: list[int]) -> list[list[dict]]:
    if not isinstance(node, Mapping):
        raise SimulationError("program node must be an object")
    op = node.get("op")
    budget[0] -= 1
    if budget[0] < 0:
        raise SimulationError("program exceeds the 10000-operation limit")
    if op == "primitive":
        return [[_parse_primitive(node, bindings)]]
    if op == "serial":
        if set(node) != {"op", "children"} or not isinstance(node["children"], list):
            raise SimulationError("serial requires a children array")
        result: list[list[dict]] = []
        for child in node["children"]:
            result.extend(_expand(child, bindings, budget=budget))
        return result
    if op == "parallel":
        if set(node) != {"op", "children"} or not isinstance(node["children"], list):
            raise SimulationError("parallel requires a children array")
        group: list[dict] = []
        for child in node["children"]:
            expanded = _expand(child, bindings, budget=budget)
            if len(expanded) != 1:
                raise SimulationError("parallel arms must be single primitives")
            group.extend(expanded[0])
        return [group]
    if op == "repeat":
        if set(node) != {"op", "count", "body"}:
            raise SimulationError("repeat requires exactly op, count, and body")
        count = node["count"]
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 10000:
            raise SimulationError("repeat count must be an integer in [0, 10000]")
        result = []
        for _ in range(count):
            result.extend(_expand(node["body"], bindings, budget=budget))
        return result
    raise SimulationError(f"unsupported program op {op!r}")


def _target(name: str) -> tuple[tuple[int, ...], str]:
    if name.startswith("q") and "." in name:
        left, operation = name.split(".", 1)
        try:
            return (int(left[1:]),), operation
        except ValueError as exc:
            raise SimulationError(f"invalid primitive target {name!r}") from exc
    if name.startswith("c") and "." in name:
        left, operation = name.split(".", 1)
        try:
            pair = tuple(int(part) for part in left[1:].split("_"))
        except ValueError as exc:
            raise SimulationError(f"invalid coupler target {name!r}") from exc
        if len(pair) == 2:
            return pair, operation
    raise SimulationError(f"invalid primitive target {name!r}")


def _tensor_operator(qt, base, qubit: int, n_qubits: int):
    factors = [qt.qeye(2) for _ in range(n_qubits)]
    factors[qubit] = base
    return qt.tensor(factors)


def _segment(device: Device, group: list[dict], frames: dict[int, float]):
    """Return (duration_ns, [(qubit, amp, phase, freq)], measurements, cz_pair)."""
    durations: list[float] = []
    drives = []
    measurements: list[tuple[str, int, dict]] = []
    cz_pair = None
    touched: set[int] = set()
    for primitive in group:
        targets, operation = _target(primitive["name"])
        args = primitive["arguments"]
        for qubit in targets:
            if str(qubit) not in device.config["qubits"]:
                raise SimulationError(f"program references unknown qubit {qubit}")
        if operation == "measure":
            record = args.get("record")
            if not isinstance(record, str) or not record:
                raise SimulationError("measure requires a non-empty record")
            measurements.append((record, targets[0], args))
            continue
        if operation == "vz":
            if len(group) != 1:
                raise SimulationError("vz cannot be parallelized in the lite twin")
            phase = float(args.get("phase", 0.0))
            frames[targets[0]] += phase
            return 0.0, [], [], None
        if operation == "delay":
            duration = float(args.get("duration_ns", args.get("duration", 0.0)))
            if duration < 0:
                raise SimulationError("delay duration must be non-negative")
            if "freq" in args:
                frequency = float(args["freq"])
                if not math.isfinite(frequency) or frequency <= 0:
                    raise SimulationError("delay frame frequency must be finite and positive")
                drives.append((targets[0], 0.0, frames[targets[0]], frequency))
            durations.append(duration)
            continue
        if operation == "CZ":
            if len(targets) != 2:
                raise SimulationError("CZ requires a coupler target such as c0_1.CZ")
            if device.truth_mode and len(device.qubit_ids) > 1:
                cz_pair = tuple(sorted(targets))
            width = float(args.get("width", 100.0))
            durations.append(width)
            continue
        qubit = targets[0]
        if qubit in touched:
            raise SimulationError(f"parallel drive conflict on qubit {qubit}")
        touched.add(qubit)
        qcfg = device.config["qubits"][str(qubit)]
        if operation in qcfg["pulses"]:
            pulse = {**qcfg["pulses"][operation], **args}
        elif operation == "drive":
            pulse = dict(args)
        else:
            raise SimulationError(f"unsupported primitive {primitive['name']!r}")
        width = float(pulse.get("width", 0.0))
        amp = float(pulse.get("amp", 0.0))
        phase = float(pulse.get("phase", 0.0)) + frames[qubit]
        freq = float(pulse.get("freq", qcfg["drive_freq"]))
        if width <= 0 or not all(math.isfinite(value) for value in (amp, phase, freq)):
            raise SimulationError("drive parameters must be finite and width must be positive")
        drives.append((qubit, amp, phase, freq))
        durations.append(width)
    if measurements and len(measurements) != len(group):
        raise SimulationError("measurement must be terminal and cannot share a drive group")
    if durations and max(durations) - min(durations) > 1e-9:
        raise SimulationError("parallel operations must have equal duration")
    return (durations[0] if durations else 0.0), drives, measurements, cz_pair


def evolve(device: Device, program: Mapping[str, Any], bindings: Mapping[str, Any],
           runtime: Runtime):
    import qutip as qt

    n_qubits = len(device.qubit_ids)
    groups = _expand(program, bindings, budget=[10000])
    referenced = set()
    for group in groups:
        for primitive in group:
            referenced.update(_target(primitive["name"])[0])
    if n_qubits > 1 and runtime.data_layer != "cuda":
        raise SimulationError("two-qubit evolution requires CUDA")
    zero = qt.basis(2, 0)
    state = qt.tensor([zero] * n_qubits)
    frames = {q: float(device.config["qubits"][str(q)]["vz_frame"])
              for q in device.qubit_ids}
    sx = [_tensor_operator(qt, qt.sigmax(), q, n_qubits) for q in device.qubit_ids]
    sy = [_tensor_operator(qt, qt.sigmay(), q, n_qubits) for q in device.qubit_ids]
    sz = [_tensor_operator(qt, qt.sigmaz(), q, n_qubits) for q in device.qubit_ids]
    # ``destroy(2)`` maps |1> -> |0>, matching the service's |0>=ground convention.
    sm = [_tensor_operator(qt, qt.destroy(2), q, n_qubits) for q in device.qubit_ids]
    c_ops = []
    for q in device.qubit_ids:
        truth = device.truth["qubits"][str(q)]
        c_ops.append(math.sqrt(1.0 / (truth["t1_us"] * 1000.0)) * sm[q])
        c_ops.append(math.sqrt(1.0 / (2.0 * truth["tphi_us"] * 1000.0)) * sz[q])
    measurement_map: dict[str, tuple[int, dict]] = {}
    for group in groups:
        duration, drives, measurements, cz_pair = _segment(device, group, frames)
        for record, qubit, args in measurements:
            if record in measurement_map:
                raise SimulationError(f"duplicate measurement record {record!r}")
            measurement_map[record] = (qubit, args)
        if measurements or duration == 0:
            continue
        hamiltonian = 0 * sz[0]
        for q in device.qubit_ids:
            truth = device.truth["qubits"][str(q)]
            active = next((drive for drive in drives if drive[0] == q), None)
            drive_freq = active[3] if active else device.config["qubits"][str(q)]["drive_freq"]
            detuning = 2.0 * math.pi * (truth["f01_hz"] - drive_freq) * 1e-9
            hamiltonian += 0.5 * detuning * sz[q]
            if active:
                _, amp, phase, _ = active
                omega = 2.0 * math.pi * truth["drive_scale_hz_per_amp"] * amp * 1e-9
                hamiltonian += 0.5 * omega * (
                    math.cos(phase) * sx[q] + math.sin(phase) * sy[q])
        if n_qubits == 2:
            zz_hz = device.truth["static_zz_hz"]
            if cz_pair is not None:
                zz_hz += device.truth["cz_rate_hz"]
            hamiltonian += 0.25 * 2.0 * math.pi * zz_hz * 1e-9 * sz[0] * sz[1]
        options = {"store_final_state": True, "nsteps": 10000}
        if runtime.data_layer == "cuda":
            options["method"] = "CuVern7"
        result = qt.mesolve(
            hamiltonian, state, [0.0, duration],
            c_ops=c_ops, e_ops=[], options=options,
        )
        state = result.final_state
    return state, measurement_map


def _axes(sweep: Any) -> list[dict[str, Any]]:
    if sweep is None:
        return []
    if not isinstance(sweep, Mapping) or set(sweep) != {"axes"}:
        raise SimulationError("sweep must contain exactly an axes array")
    axes = sweep["axes"]
    if not isinstance(axes, list):
        raise SimulationError("sweep.axes must be an array")
    parsed = []
    seen = set()
    for axis in axes:
        if (not isinstance(axis, Mapping) or set(axis) != {"name", "kind", "values"}
                or not isinstance(axis["name"], str) or not axis["name"]
                or axis["name"] in seen or axis["kind"] not in {"bind", "choice"}
                or not isinstance(axis["values"], list) or not axis["values"]):
            raise SimulationError("malformed sweep axis")
        seen.add(axis["name"])
        parsed.append(dict(axis))
    if sum(axis["kind"] == "choice" for axis in parsed) > 1:
        raise SimulationError("at most one choice axis is supported")
    return parsed


def _points(axes: list[dict[str, Any]]):
    if not axes:
        return [({}, None)]
    result = []
    for values in itertools.product(*(axis["values"] for axis in axes)):
        bindings = {}
        choice = None
        for axis, value in zip(axes, values):
            if axis["kind"] == "choice":
                if isinstance(value, bool) or not isinstance(value, int):
                    raise SimulationError("choice values must be integer program indices")
                choice = value
            else:
                bindings[axis["name"]] = value
        result.append((bindings, choice))
    return result


def _probabilities(qt, state, n_qubits: int) -> np.ndarray:
    rho = qt.ket2dm(state) if state.isket else state
    diagonal = np.real(np.asarray(rho.diag())).astype(float)
    diagonal = np.clip(diagonal, 0.0, None)
    total = diagonal.sum()
    if total <= 0:
        raise SimulationError("evolved state has no probability mass")
    return diagonal / total


def _marginal(probabilities: np.ndarray, qubit: int, n_qubits: int) -> np.ndarray:
    out = np.zeros(2, dtype=float)
    for basis, probability in enumerate(probabilities):
        bit = (basis >> (n_qubits - 1 - qubit)) & 1
        out[bit] += probability
    return out


def _iq_samples(device: Device, qubit: int, args: Mapping[str, Any], probability: np.ndarray,
                shots: int, rng: np.random.Generator) -> np.ndarray:
    truth = device.truth["qubits"][str(qubit)]
    config = device.config["qubits"][str(qubit)]["readout"]
    states = rng.choice(2, size=shots, p=probability)
    errors = rng.random(shots) < truth["assignment_error"]
    states = np.where(errors, 1 - states, states)
    freq = float(args.get("freq", config["freq"]))
    values = np.empty(shots, dtype=np.complex128)
    for state_index in (0, 1):
        selected = states == state_index
        resonance = truth["resonator_freq_hz"] + state_index * 2.0 * truth["chi_hz"]
        detuning = 2.0 * (freq - resonance) / truth["kappa_hz"]
        response = 1.0 - 0.8 / (1.0 + 1j * detuning)
        center_pair = truth["iq_centers"][state_index]
        center = complex(center_pair[0], center_pair[1]) * response
        count = int(selected.sum())
        noise = truth["readout_noise"] * (
            rng.normal(size=count) + 1j * rng.normal(size=count))
        values[selected] = center + noise
    return values


def run(device: Device, body: Any, runtime: Runtime) -> dict[str, Any]:
    import qutip as qt

    if not isinstance(body, Mapping):
        raise SimulationError("run request must be an object")
    allowed = {"program", "programs", "shots", "returns", "sweep", "groups", "seed", "options"}
    unknown = sorted(set(body) - allowed)
    if unknown:
        raise SimulationError(f"run request has unknown field(s): {', '.join(unknown)}")
    if ("program" in body) == ("programs" in body):
        raise SimulationError("provide exactly one of program or programs")
    shots = body.get("shots")
    if isinstance(shots, bool) or not isinstance(shots, int) or not 1 <= shots <= 100000:
        raise SimulationError("shots must be an integer in [1, 100000]")
    returns = body.get("returns")
    if not isinstance(returns, Mapping) or not returns:
        raise SimulationError("returns must be a non-empty object")
    options = body.get("options") or {}
    if not isinstance(options, Mapping):
        raise SimulationError("options must be an object")
    engine = str(options.get("engine", "qutip")).lower()
    layer = str(options.get("qutip_data_layer", runtime.data_layer)).lower()
    if engine != "qutip" or layer != runtime.data_layer:
        raise SimulationError(
            f"service runs qutip/{runtime.data_layer}; requested {engine}/{layer}")
    axes = _axes(body.get("sweep"))
    points = _points(axes)
    programs = body.get("programs")
    if programs is not None and (not isinstance(programs, list) or not programs):
        raise SimulationError("programs must be a non-empty array")
    if programs is not None and not any(axis["kind"] == "choice" for axis in axes):
        raise SimulationError("programs requires one choice axis")
    if programs is None and any(axis["kind"] == "choice" for axis in axes):
        raise SimulationError("choice axis requires programs")
    seed = body.get("seed", device.seed)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise SimulationError("seed must be an integer")
    groups = body.get("groups") or {}
    if not isinstance(groups, Mapping):
        raise SimulationError("groups must be an object")
    rows: dict[str, list[Any]] = {str(record): [] for record in returns}
    for index, (bindings, choice) in enumerate(points):
        if programs is None:
            program = body["program"]
        else:
            if choice is None or not 0 <= choice < len(programs):
                raise SimulationError(f"choice index {choice!r} is out of range")
            program = programs[choice]
        state, measurements = evolve(device, program, bindings, runtime)
        probabilities = _probabilities(qt, state, len(device.qubit_ids))
        rng = np.random.default_rng(seed + index)
        for record_id, return_type in returns.items():
            if return_type == "joint_shots":
                members = groups.get(record_id)
                if not isinstance(members, list) or not members:
                    raise SimulationError(f"joint_shots {record_id!r} requires a group")
                qubits = []
                for member in members:
                    if member not in measurements:
                        raise SimulationError(f"unknown group record {member!r}")
                    qubits.append(measurements[member][0])
                basis_samples = rng.choice(len(probabilities), size=shots, p=probabilities)
                outcomes = np.zeros(shots, dtype=np.int64)
                for bit_index, qubit in enumerate(qubits):
                    bit = (basis_samples >> (len(device.qubit_ids) - 1 - qubit)) & 1
                    error = rng.random(shots) < device.truth["qubits"][str(qubit)][
                        "assignment_error"]
                    bit = np.where(error, 1 - bit, bit)
                    outcomes |= bit.astype(np.int64) << bit_index
                rows[record_id].append(outcomes)
                continue
            if record_id not in measurements:
                raise SimulationError(f"return references unknown record {record_id!r}")
            qubit, measure_args = measurements[record_id]
            marginal = _marginal(probabilities, qubit, len(device.qubit_ids))
            if return_type == "populations":
                rows[record_id].append(marginal)
            elif return_type == "iq_shot":
                rows[record_id].append(
                    _iq_samples(device, qubit, measure_args, marginal, shots, rng))
            elif return_type == "state_shots":
                samples = rng.choice(2, size=shots, p=marginal)
                errors = rng.random(shots) < device.truth["qubits"][str(qubit)][
                    "assignment_error"]
                rows[record_id].append(np.where(errors, 1 - samples, samples))
            else:
                raise SimulationError(f"unsupported return type {return_type!r}")
    records = {}
    for record_id, values in rows.items():
        array = np.asarray(values)
        return_type = str(returns[record_id])
        if np.iscomplexobj(array):
            data = np.stack([array.real, array.imag], axis=-1).tolist()
        else:
            data = array.tolist()
        records[record_id] = {
            "record_id": record_id,
            "return_type": return_type,
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "data": data,
        }
    sweep_indices = list(range(len(points)))
    dynamics = {
        "engine_used": "qutip",
        "data_layer_used": runtime.data_layer,
        "model": "qca-lite-v1",
        "solver": "mesolve",
        "levels_per_transmon": 2,
        "versions": runtime_versions(),
    }
    provenance = {
        "result_schema_version": 1,
        "device_schema_version": 1,
        "config_version": device.config_version,
        "seed": seed,
        "backend": {"cudaq_pulse_version": "qca-lite-qutip/1"},
        "truth_digest": device.truth_digest,
        "profile_build_version": 1,
        "sweep_axes": axes,
        "sweep_success_indices": sweep_indices,
        "record_sweep_indices": {record: sweep_indices for record in records},
        "sweep_program_indices": [choice for _, choice in points if choice is not None],
        "readout_groups": dict(groups),
        "envelope": {"status": "not_measured"},
        "dynamics": dynamics,
    }
    return {"records": records, "provenance": provenance, "failures": []}
