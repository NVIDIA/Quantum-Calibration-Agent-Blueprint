# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""T1 characterization using the QCA Lite QuTiP twin."""

from typing import Annotated


def lite_t1(
    target: str = "Q1",
    max_delay_us: Annotated[float, (5.0, 200.0)] = 100.0,
    points: Annotated[int, (9, 101)] = 41,
    shots: Annotated[int, (1, 10000)] = 128,
    seed: Annotated[int, (0, 2_147_483_647)] = 0,
) -> dict:
    """Measure T1 without changing the twin session configuration.

    Args:
        target: Qubit label, Q1 or Q2.
        max_delay_us: Maximum relaxation delay in microseconds.
        points: Number of delay points.
        shots: Requested shots per point.
        seed: Deterministic measurement seed.
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
    pulse = config["qubits"][str(qubit)]["pulses"]["X"]
    delays_ns = np.linspace(0.0, max_delay_us * 1000.0, points)
    run = client.run_program(
        session_id,
        program=serial(
            primitive(
                f"q{qubit}.drive",
                amp=pulse["amp"],
                width=pulse["width"],
                phase=pulse["phase"],
            ),
            primitive(f"q{qubit}.delay", duration_ns="$t"),
            primitive(f"q{qubit}.measure", record="r0"),
        ),
        shots=shots,
        returns={"r0": "populations"},
        sweep=[{"name": "t", "kind": "bind", "values": delays_ns.tolist()}],
        seed=seed,
    )
    excited = run.array("r0")[:, 1]
    tau_ns, score, fit, parameters, uncertainty_ns = _fit_exp_decay(
        delays_ns, excited
    )
    passed = score >= 0.90 and 0.0 < tau_ns < max_delay_us * 1000.0
    data = {
        "delays": array(delays_ns / 1000.0, "us", "Relaxation delays"),
        "excited_population": array(excited, "probability", "Excited population"),
        "fit_curve": array(fit, "probability", "Exponential fit"),
        "residuals": array(excited - fit, "probability", "Fit residuals"),
        "t1_time": scalar(tau_ns / 1000.0, "us", "Fitted T1 relaxation time"),
        "fit_r_squared": scalar(score, "", "Fit R-squared"),
        "fit_uncertainty_us": scalar(
            uncertainty_ns / 1000.0, "us", "T1 uncertainty"
        ),
        "fit_parameters": metadata(parameters, "Exponential fit parameters"),
        "configuration_applied": scalar(False, "", "Read-only experiment"),
        "config_version": scalar(
            int(run.provenance.get("config_version", 0)),
            "",
            "Twin configuration version",
        ),
        "backend_provenance": metadata(run.provenance, "Backend provenance"),
    }
    plot = fit_plot(
        name="QCA Lite T1",
        title=f"QCA Lite T1 — {target}",
        x=delays_ns / 1000.0,
        y=excited,
        fit=fit,
        xlabel="Delay (us)",
        ylabel="Excited-state probability",
        feature_x=tau_ns / 1000.0,
        feature_label="fitted T1",
    )
    result = {"status": "success" if passed else "failed", "data": data, "plots": [plot]}
    if not passed:
        result["error"] = f"T1 fit failed: R-squared={score:.4f}, T1={tau_ns/1000.0:.3f} us"
    return result


def _fit_exp_decay(delays_ns, excited):
    import numpy as np
    from scipy.optimize import curve_fit

    delays_ns = np.asarray(delays_ns, dtype=float)
    excited = np.asarray(excited, dtype=float)
    baseline_guess = float(np.min(excited))
    amplitude_guess = float(np.ptp(excited)) or 1e-3
    span_ns = float(delays_ns[-1] - delays_ns[0]) or 1.0

    def exponential(delay, amplitude, tau, baseline):
        return baseline + amplitude * np.exp(-delay / tau)

    popt, covariance = curve_fit(
        exponential,
        delays_ns,
        excited,
        p0=[amplitude_guess, span_ns / 2.0, baseline_guess],
        bounds=([0.0, 1.0, -0.25], [1.5, span_ns * 10.0, 0.5]),
        maxfev=20000,
    )
    predicted = exponential(delays_ns, *popt)
    residual = float(np.sum((excited - predicted) ** 2))
    total = float(np.sum((excited - np.mean(excited)) ** 2)) or 1e-12
    score = 1.0 - residual / total
    uncertainty_ns = float(np.sqrt(abs(covariance[1, 1])))
    parameters = {
        "amplitude": float(popt[0]),
        "tau_ns": float(popt[1]),
        "baseline": float(popt[2]),
    }
    return (
        float(popt[1]),
        max(0.0, min(1.0, score)),
        predicted,
        parameters,
        uncertainty_ns,
    )
