# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Amplitude-Rabi calibration using the QCA Lite QuTiP twin."""

from typing import Annotated


def lite_rabi_amplitude(
    target: str = "Q1",
    max_amp: Annotated[float, (0.02, 0.5)] = 0.20,
    points: Annotated[int, (9, 201)] = 51,
    shots: Annotated[int, (1, 10000)] = 128,
    seed: Annotated[int, (0, 2_147_483_647)] = 0,
    apply: bool = True,
) -> dict:
    """Fit a pi-pulse amplitude and optionally apply X and X90 amplitudes.

    Args:
        target: Qubit label, Q1 or Q2.
        max_amp: Maximum dimensionless drive amplitude.
        points: Number of amplitude points.
        shots: Requested shots per point.
        seed: Deterministic measurement seed.
        apply: Apply the measured X and X90 amplitudes when the fit passes.
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
    amplitudes = np.linspace(0.0, max_amp, points)
    run = client.run_program(
        session_id,
        program=serial(
            primitive(f"q{qubit}.drive", amp="$a", width=40.0, phase=0.0),
            primitive(f"q{qubit}.measure", record="r0"),
        ),
        shots=shots,
        returns={"r0": "populations"},
        sweep=[{"name": "a", "kind": "bind", "values": amplitudes.tolist()}],
        seed=seed,
    )
    excited = run.array("r0")[:, 1]
    pi_amp, residual, fit, parameters, uncertainty = _fit_rabi(amplitudes, excited)
    contrast = float(np.ptp(excited))
    inversion = float(np.max(excited))
    passed = residual <= 0.05 and contrast >= 0.50 and 0.0 < pi_amp <= max_amp
    applied = False
    config_version = int(run.provenance.get("config_version", 0))
    if apply and passed:
        client.patch_config(
            session_id,
            {"qubit": qubit, "gate": "X", "overrides": {"amp": pi_amp}},
        )
        updated = client.patch_config(
            session_id,
            {"qubit": qubit, "gate": "X90", "overrides": {"amp": pi_amp / 2.0}},
        )
        applied = True
        config_version = int(updated["config_version"])

    data = {
        "amplitudes": array(amplitudes, "a.u.", "Drive amplitudes"),
        "excited_population": array(excited, "probability", "Excited population"),
        "fit_curve": array(fit, "probability", "Rabi fit"),
        "residuals": array(excited - fit, "probability", "Fit residuals"),
        "pi_amplitude": scalar(pi_amp, "a.u.", "Calibrated pi-pulse amplitude"),
        "pi_half_amplitude": scalar(pi_amp / 2.0, "a.u.", "Calibrated pi/2 amplitude"),
        "fit_residual": scalar(residual, "probability", "RMS fit residual"),
        "fit_uncertainty_amp": scalar(uncertainty, "a.u.", "Pi-amplitude uncertainty"),
        "rabi_contrast": scalar(contrast, "probability", "Rabi contrast"),
        "peak_inversion": scalar(inversion, "probability", "Peak inversion"),
        "fit_parameters": metadata(parameters, "Rabi fit parameters"),
        "configuration_applied": scalar(applied, "", "Applied to twin session"),
        "config_version": scalar(config_version, "", "Twin configuration version"),
        "backend_provenance": metadata(run.provenance, "Backend provenance"),
    }
    plot = fit_plot(
        name="QCA Lite Rabi amplitude",
        title=f"QCA Lite Rabi Amplitude — {target}",
        x=amplitudes,
        y=excited,
        fit=fit,
        xlabel="Drive amplitude (a.u.)",
        ylabel="Excited-state probability",
        feature_x=pi_amp,
        feature_label="pi amplitude",
    )
    result = {"status": "success" if passed else "failed", "data": data, "plots": [plot]}
    if not passed:
        result["error"] = (
            f"Rabi fit failed: residual={residual:.4f}, contrast={contrast:.4f}"
        )
    return result


def _fit_rabi(amplitudes, excited):
    import numpy as np
    from scipy.optimize import curve_fit

    amplitudes = np.asarray(amplitudes, dtype=float)
    excited = np.asarray(excited, dtype=float)
    span = float(amplitudes[-1] - amplitudes[0]) or 1.0

    def cosine(amplitude, scale, frequency, phase, offset):
        return scale * (1.0 - np.cos(2.0 * np.pi * frequency * amplitude + phase)) / 2.0 + offset

    popt, covariance = curve_fit(
        cosine,
        amplitudes,
        excited,
        p0=[float(np.ptp(excited)) or 1.0, 1.0 / span, 0.0, float(np.min(excited))],
        maxfev=20000,
    )
    frequency = abs(float(popt[1])) or 1.0 / span
    pi_amp = (np.pi - float(popt[2])) / (2.0 * np.pi * frequency)
    if not np.isfinite(pi_amp) or not 0.0 < pi_amp <= amplitudes[-1]:
        pi_amp = 0.5 / frequency
    if not np.isfinite(pi_amp) or not 0.0 < pi_amp <= amplitudes[-1]:
        pi_amp = float(amplitudes[int(np.argmax(excited))])
    predicted = cosine(amplitudes, *popt)
    residual = float(np.sqrt(np.mean((excited - predicted) ** 2)))
    uncertainty = float(np.sqrt(abs(covariance[1, 1])) * abs(pi_amp / frequency))
    parameters = {
        "amplitude": float(popt[0]),
        "frequency_per_amp": float(popt[1]),
        "phase": float(popt[2]),
        "offset": float(popt[3]),
    }
    return float(pi_amp), residual, predicted, parameters, uncertainty
