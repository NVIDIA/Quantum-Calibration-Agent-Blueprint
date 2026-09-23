# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Ramsey frequency refinement using the QCA Lite QuTiP twin plugin."""

from typing import Annotated


def lite_ramsey_frequency(
    target: str = "Q1",
    max_delay_ns: Annotated[float, (200.0, 10000.0)] = 3000.0,
    points: Annotated[int, (15, 201)] = 61,
    shots: Annotated[int, (1, 10000)] = 128,
    detuning_hz: Annotated[float, (500_000.0, 10_000_000.0)] = 2_000_000.0,
    seed: Annotated[int, (0, 2_147_483_647)] = 0,
    apply: bool = True,
) -> dict:
    """Refine the drive frequency with a deliberately detuned Ramsey sequence.

    Args:
        target: Qubit label, Q1 or Q2.
        max_delay_ns: Maximum Ramsey delay in nanoseconds.
        points: Number of delay points.
        shots: Requested shots per point.
        detuning_hz: Deliberate probe detuning from the current drive frequency.
        seed: Deterministic measurement seed.
        apply: Apply the refined drive frequency when the fit passes.
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
    qconfig = config["qubits"][str(qubit)]
    center_hz = float(qconfig["drive_freq"])
    x90_amp = float(qconfig["pulses"]["X90"]["amp"])
    probe_hz = center_hz + detuning_hz
    delays = np.linspace(0.0, max_delay_ns, points)
    run = client.run_program(
        session_id,
        program=serial(
            primitive(
                f"q{qubit}.drive", amp=x90_amp, width=40.0, phase=0.0, freq=probe_hz
            ),
            primitive(f"q{qubit}.delay", duration_ns="$t", freq=probe_hz),
            primitive(
                f"q{qubit}.drive", amp=x90_amp, width=40.0, phase=0.0, freq=probe_hz
            ),
            primitive(f"q{qubit}.measure", record="r0"),
        ),
        shots=shots,
        returns={"r0": "populations"},
        sweep=[{"name": "t", "kind": "bind", "values": delays.tolist()}],
        seed=seed,
    )
    excited = run.array("r0")[:, 1]
    fringe_hz, score, contrast, fit, parameters, uncertainty_hz = _fit_ramsey(
        delays, excited
    )
    signed_error_hz = fringe_hz - detuning_hz
    refined_hz = center_hz - signed_error_hz
    period_ns = 1e9 / max(fringe_hz, 1e-12)
    period_uncertainty_ns = uncertainty_hz * 1e9 / max(fringe_hz**2, 1e-12)
    passed = score >= 0.80 and contrast >= 0.10 and refined_hz > 0.0
    applied = False
    config_version = int(run.provenance.get("config_version", 0))
    if apply and passed:
        updated = client.patch_config(
            session_id, {"qubit": qubit, "fields": {"drive_freq": refined_hz}}
        )
        applied = True
        config_version = int(updated["config_version"])

    data = {
        "delays": array(delays, "ns", "Ramsey delays"),
        "excited_population": array(excited, "probability", "Excited population"),
        "fit_curve": array(fit, "probability", "Decaying-cosine fit"),
        "residuals": array(excited - fit, "probability", "Fit residuals"),
        "refined_drive_frequency": scalar(
            refined_hz / 1e9, "GHz", "Refined drive frequency"
        ),
        "refined_drive_frequency_hz": scalar(
            refined_hz, "Hz", "Refined drive frequency"
        ),
        "frequency_error_hz": scalar(
            abs(signed_error_hz), "Hz", "Drive-frequency correction magnitude"
        ),
        "fitted_detuning_hz": scalar(fringe_hz, "Hz", "Fitted Ramsey detuning"),
        "fitted_period_ns": scalar(period_ns, "ns", "Fitted Ramsey period"),
        "fit_r_squared": scalar(score, "", "Fit R-squared"),
        "ramsey_contrast": scalar(contrast, "probability", "Ramsey contrast"),
        "fit_uncertainty_hz": scalar(uncertainty_hz, "Hz", "Frequency uncertainty"),
        "fit_uncertainty_period_ns": scalar(
            period_uncertainty_ns, "ns", "Period uncertainty"
        ),
        "fit_parameters": metadata(parameters, "Ramsey fit parameters"),
        "configuration_applied": scalar(applied, "", "Applied to plugin session"),
        "config_version": scalar(config_version, "", "Plugin configuration version"),
        "backend_provenance": metadata(run.provenance, "Backend provenance"),
    }
    plot = fit_plot(
        name="QCA Lite Ramsey frequency",
        title=f"QCA Lite Ramsey Frequency — {target}",
        x=delays,
        y=excited,
        fit=fit,
        xlabel="Delay (ns)",
        ylabel="Excited-state probability",
        feature_x=period_ns,
        feature_label="fringe period",
    )
    result = {"status": "success" if passed else "failed", "data": data, "plots": [plot]}
    if not passed:
        result["error"] = (
            f"Ramsey fit failed: R-squared={score:.4f}, contrast={contrast:.4f}"
        )
    return result


def _fit_ramsey(delays_ns, excited):
    import numpy as np
    from scipy.optimize import curve_fit

    delays_ns = np.asarray(delays_ns, dtype=float)
    excited = np.asarray(excited, dtype=float)
    contrast = float(np.ptp(excited))
    baseline_guess = float(np.mean(excited))
    amplitude_guess = float(np.ptp(excited) / 2.0) or 1e-3
    span_ns = float(delays_ns[-1] - delays_ns[0]) or 1.0
    tau_guess = span_ns / 2.0
    spacing = span_ns / (len(delays_ns) - 1)
    spectrum = np.abs(np.fft.rfft(excited - baseline_guess))
    bins = np.fft.rfftfreq(len(delays_ns), d=spacing)
    frequency_guess = float(bins[1 + int(np.argmax(spectrum[1:]))])

    def decaying_cosine(delay, frequency, tau, amplitude, phase, baseline):
        return baseline + amplitude * np.exp(-delay / tau) * np.cos(
            2.0 * np.pi * frequency * delay + phase
        )

    popt, covariance = curve_fit(
        decaying_cosine,
        delays_ns,
        excited,
        p0=[frequency_guess, tau_guess, amplitude_guess, 0.0, baseline_guess],
        bounds=(
            [0.0, spacing, -1.0, -2.0 * np.pi, -0.25],
            [0.5 / spacing, span_ns * 100.0, 1.0, 2.0 * np.pi, 1.25],
        ),
        maxfev=30000,
    )
    predicted = decaying_cosine(delays_ns, *popt)
    residual = float(np.sum((excited - predicted) ** 2))
    total = float(np.sum((excited - np.mean(excited)) ** 2)) or 1e-12
    score = 1.0 - residual / total
    frequency_per_ns = abs(float(popt[0]))
    uncertainty_hz = float(np.sqrt(abs(covariance[0, 0])) * 1e9)
    parameters = {
        "frequency_per_ns": frequency_per_ns,
        "tau_ns": float(popt[1]),
        "amplitude": float(popt[2]),
        "phase": float(popt[3]),
        "baseline": float(popt[4]),
    }
    return (
        frequency_per_ns * 1e9,
        max(0.0, min(1.0, score)),
        contrast,
        predicted,
        parameters,
        uncertainty_hz,
    )
