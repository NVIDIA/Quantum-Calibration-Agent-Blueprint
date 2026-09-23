# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Dispersive resonator spectroscopy using the QCA Lite QuTiP twin."""

from typing import Annotated


def lite_resonator_spectroscopy(
    target: str = "Q1",
    span_mhz: Annotated[float, (2.0, 100.0)] = 40.0,
    points: Annotated[int, (9, 201)] = 61,
    shots: Annotated[int, (32, 10000)] = 256,
    seed: Annotated[int, (0, 2_147_483_647)] = 0,
    apply: bool = True,
) -> dict:
    """Locate a readout resonance and optionally apply the fitted frequency.

    Args:
        target: Qubit label, Q1 or Q2.
        span_mhz: Half-span around the current readout frequency in MHz.
        points: Number of frequency points.
        shots: IQ shots per point.
        seed: Deterministic measurement seed.
        apply: Apply the measured frequency to the twin session when the fit passes.
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
    center_hz = float(config["qubits"][str(qubit)]["readout"]["freq"])
    freqs = np.linspace(center_hz - span_mhz * 1e6, center_hz + span_mhz * 1e6, points)
    run = client.run_program(
        session_id,
        program=serial(primitive(f"q{qubit}.measure", record="r0", freq="$f")),
        shots=shots,
        returns={"r0": "iq_shot"},
        sweep=[{"name": "f", "kind": "bind", "values": freqs.tolist()}],
        seed=seed,
    )
    magnitude = np.abs(run.array("r0").mean(axis=1))
    fitted, score, contrast, fit, parameters, uncertainty = _fit_resonance(
        freqs, magnitude
    )
    passed = score >= 0.85 and freqs[0] < fitted < freqs[-1]
    applied = False
    config_version = int(run.provenance.get("config_version", 0))
    if apply and passed:
        updated = client.patch_config(
            session_id, {"qubit": qubit, "readout": {"freq": fitted}}
        )
        applied = True
        config_version = int(updated["config_version"])

    data = {
        "frequencies": array(freqs / 1e9, "GHz", "Readout frequencies"),
        "magnitude": array(magnitude, "a.u.", "Mean IQ magnitude"),
        "fit_curve": array(fit, "a.u.", "Lorentzian fit"),
        "residuals": array(magnitude - fit, "a.u.", "Fit residuals"),
        "readout_frequency": scalar(fitted / 1e9, "GHz", "Fitted readout frequency"),
        "readout_frequency_hz": scalar(fitted, "Hz", "Fitted readout frequency"),
        "fit_r_squared": scalar(score, "", "Fit R-squared"),
        "fit_uncertainty_hz": scalar(uncertainty, "Hz", "Center uncertainty"),
        "contrast": scalar(contrast, "a.u.", "Resonance contrast"),
        "fit_parameters": metadata(parameters, "Lorentzian parameters"),
        "configuration_applied": scalar(applied, "", "Applied to twin session"),
        "config_version": scalar(config_version, "", "Twin configuration version"),
        "backend_provenance": metadata(run.provenance, "Backend provenance"),
    }
    plot = fit_plot(
        name="QCA Lite resonator spectroscopy",
        title=f"QCA Lite Resonator Spectroscopy — {target}",
        x=freqs / 1e9,
        y=magnitude,
        fit=fit,
        xlabel="Readout frequency (GHz)",
        ylabel="|IQ| (a.u.)",
        feature_x=fitted / 1e9,
        feature_label="fitted resonance",
    )
    result = {"status": "success" if passed else "failed", "data": data, "plots": [plot]}
    if not passed:
        result["error"] = f"resonator fit failed: R-squared={score:.4f}"
    return result


def _fit_resonance(freqs, magnitude):
    import numpy as np
    from scipy.optimize import curve_fit

    baseline = float(np.median(magnitude))
    peak_index = int(np.argmax(np.abs(magnitude - baseline)))
    f0_guess = float(freqs[peak_index])
    amplitude_guess = float(magnitude[peak_index] - baseline)
    width_guess = float((freqs[-1] - freqs[0]) / 10.0) or 1.0

    def lorentzian(frequency, center, half_width, amplitude, offset):
        return offset + amplitude * half_width**2 / (
            (frequency - center) ** 2 + half_width**2
        )

    popt, covariance = curve_fit(
        lorentzian,
        freqs,
        magnitude,
        p0=[f0_guess, width_guess, amplitude_guess, baseline],
        maxfev=20000,
    )
    predicted = lorentzian(freqs, *popt)
    residual = float(np.sum((magnitude - predicted) ** 2))
    total = float(np.sum((magnitude - np.mean(magnitude)) ** 2)) or 1e-12
    score = max(0.0, min(1.0, 1.0 - residual / total))
    uncertainty = float(np.sqrt(abs(covariance[0, 0])))
    parameters = {
        "center_hz": float(popt[0]),
        "half_width_hz": abs(float(popt[1])),
        "amplitude": float(popt[2]),
        "baseline": float(popt[3]),
    }
    return (
        float(popt[0]),
        score,
        float(np.ptp(magnitude)),
        np.asarray(predicted),
        parameters,
        uncertainty,
    )
