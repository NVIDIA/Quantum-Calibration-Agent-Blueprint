# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Qubit spectroscopy using real QCA Lite QuTiP dynamics."""

from typing import Annotated


def lite_qubit_spectroscopy(
    target: str = "Q1",
    span_mhz: Annotated[float, (5.0, 200.0)] = 60.0,
    points: Annotated[int, (9, 201)] = 61,
    shots: Annotated[int, (1, 10000)] = 128,
    probe_amp: Annotated[float, (0.001, 0.2)] = 0.025,
    seed: Annotated[int, (0, 2_147_483_647)] = 0,
    apply: bool = True,
) -> dict:
    """Locate a qubit transition and optionally apply the fitted drive frequency.

    Args:
        target: Qubit label, Q1 or Q2.
        span_mhz: Half-span around the current drive frequency in MHz.
        points: Number of frequency points.
        shots: Requested shots per point.
        probe_amp: Square-pulse probe amplitude.
        seed: Deterministic measurement seed.
        apply: Apply the measured frequency to the plugin session when the fit passes.
    """
    import numpy as np

    from ._lite_twin_client import (
        LiteTwinClient,
        array,
        fit_plot,
        metadata,
        primitive,
        qubit_index,
        scalar,
        serial,
        session_id_from_env,
    )

    qubit = qubit_index(target)
    client = LiteTwinClient.from_env()
    session_id = session_id_from_env(client)
    config = client.get_config(session_id)["config"]
    center_hz = float(config["qubits"][str(qubit)]["drive_freq"])
    freqs = np.linspace(center_hz - span_mhz * 1e6, center_hz + span_mhz * 1e6, points)
    run = client.run_program(
        session_id,
        program=serial(
            primitive(
                f"q{qubit}.drive", freq="$f", width=200.0, amp=probe_amp, phase=0.0
            ),
            primitive(f"q{qubit}.measure", record="r0"),
        ),
        shots=shots,
        returns={"r0": "populations"},
        sweep=[{"name": "f", "kind": "bind", "values": freqs.tolist()}],
        seed=seed,
    )
    excited = run.array("r0")[:, 1]
    fitted, score, contrast, fit, parameters, uncertainty = _fit_peak(
        freqs, excited, width_ns=200.0
    )
    passed = score >= 0.85 and contrast >= 0.10 and freqs[0] < fitted < freqs[-1]
    applied = False
    config_version = int(run.provenance.get("config_version", 0))
    if apply and passed:
        updated = client.patch_config(
            session_id, {"qubit": qubit, "fields": {"drive_freq": fitted}}
        )
        applied = True
        config_version = int(updated["config_version"])

    data = {
        "frequencies": array(freqs / 1e9, "GHz", "Drive frequencies"),
        "excited_population": array(excited, "probability", "Excited population"),
        "fit_curve": array(fit, "probability", "Physical square-pulse fit"),
        "residuals": array(excited - fit, "probability", "Fit residuals"),
        "qubit_frequency": scalar(fitted / 1e9, "GHz", "Fitted qubit frequency"),
        "qubit_frequency_hz": scalar(fitted, "Hz", "Fitted qubit frequency"),
        "fit_r_squared": scalar(score, "", "Fit R-squared"),
        "peak_contrast": scalar(contrast, "probability", "Spectral contrast"),
        "fit_uncertainty_hz": scalar(uncertainty, "Hz", "Center uncertainty"),
        "fit_parameters": metadata(parameters, "Square-pulse fit parameters"),
        "configuration_applied": scalar(applied, "", "Applied to plugin session"),
        "config_version": scalar(config_version, "", "Plugin configuration version"),
        "backend_provenance": metadata(run.provenance, "Backend provenance"),
    }
    plot = fit_plot(
        name="QCA Lite qubit spectroscopy",
        title=f"QCA Lite Qubit Spectroscopy — {target}",
        x=freqs / 1e9,
        y=excited,
        fit=fit,
        xlabel="Drive frequency (GHz)",
        ylabel="Excited-state probability",
        feature_x=fitted / 1e9,
        feature_label="f01",
    )
    result = {"status": "success" if passed else "failed", "data": data, "plots": [plot]}
    if not passed:
        result["error"] = (
            f"qubit fit failed: R-squared={score:.4f}, contrast={contrast:.4f}"
        )
    return result


def _fit_peak(freqs, excited, *, width_ns):
    import numpy as np
    from scipy.optimize import curve_fit

    freqs = np.asarray(freqs, dtype=float)
    excited = np.asarray(excited, dtype=float)
    duration = width_ns * 1e-9

    def response(frequency, center, rabi_hz, amplitude, baseline):
        detuning = frequency - center
        generalized = np.sqrt(rabi_hz**2 + detuning**2)
        envelope = rabi_hz**2 / np.maximum(generalized**2, 1e-30)
        return baseline + amplitude * envelope * np.sin(np.pi * generalized * duration) ** 2

    peak = int(np.argmax(excited))
    span = float(np.ptp(freqs))
    popt, covariance = curve_fit(
        response,
        freqs,
        excited,
        p0=[float(freqs[peak]), 3.0e6, 1.0, float(np.min(excited))],
        bounds=(
            [float(freqs[0]), 1.0e3, 0.0, -0.25],
            [float(freqs[-1]), max(span, 1.0), 2.0, 0.25],
        ),
        maxfev=30000,
    )
    predicted = response(freqs, *popt)
    residual = excited - predicted
    total = float(np.sum((excited - np.mean(excited)) ** 2)) or 1e-12
    score = 1.0 - float(np.sum(residual**2)) / total
    uncertainty = float(np.sqrt(max(0.0, float(covariance[0, 0]))))
    parameters = {
        "center_hz": float(popt[0]),
        "rabi_hz": float(popt[1]),
        "linewidth_hz": 1.0 / duration,
        "amplitude": float(popt[2]),
        "baseline": float(popt[3]),
    }
    return (
        float(popt[0]),
        max(0.0, min(1.0, score)),
        float(np.ptp(excited)),
        predicted,
        parameters,
        uncertainty,
    )
