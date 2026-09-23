# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Small QCA-side adapter for the standalone QCA Lite QuTiP twin plugin."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import requests


URL_ENV = "QCA_LITE_TWIN_URL"
SESSION_ENV = "QCA_LITE_TWIN_SESSION_ID"
DEFAULT_URL = "http://127.0.0.1:8090"


class LiteTwinError(RuntimeError):
    """Typed transport or service failure from the lite twin."""

    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(f"[{code}] {message}" + (f" (HTTP {status})" if status else ""))
        self.code = code
        self.status = status


@dataclass(frozen=True)
class LiteRun:
    records: dict[str, np.ndarray]
    provenance: dict[str, Any]
    failures: list[dict[str, Any]]

    def array(self, record_id: str) -> np.ndarray:
        return self.records[record_id]


class LiteTwinClient:
    """HTTP client limited to the routes used by the five plugin experiments."""

    def __init__(self, base_url: str, *, timeout: float = 600.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "LiteTwinClient":
        return cls(os.environ.get(URL_ENV, DEFAULT_URL))

    def _request(self, method: str, path: str, *, body: Any = None) -> dict[str, Any]:
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                json=body,
                timeout=(5.0, self.timeout),
            )
        except requests.RequestException as exc:
            raise LiteTwinError("unreachable", str(exc)) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise LiteTwinError(
                "bad_response", "service returned non-JSON data", status=response.status_code
            ) from exc
        if not response.ok:
            raise LiteTwinError(
                str(payload.get("code", "http_error")),
                str(payload.get("message", payload)),
                status=response.status_code,
            )
        if not isinstance(payload, dict):
            raise LiteTwinError("bad_response", "service response must be an object")
        return payload

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/healthz")

    def create_session(self, request: Mapping[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/sessions", body=dict(request))

    def describe_session(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/sessions/{session_id}")

    def get_config(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/device/{session_id}/config")

    def patch_config(self, session_id: str, patch: Mapping[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/device/{session_id}/config", body=dict(patch))

    def run_program(
        self,
        session_id: str,
        *,
        program: Mapping[str, Any],
        shots: int,
        returns: Mapping[str, str],
        sweep: list[dict[str, Any]] | None = None,
        seed: int = 0,
    ) -> LiteRun:
        health = self.health()
        layer = health["backend"]["data_layer_used"]
        body: dict[str, Any] = {
            "program": dict(program),
            "shots": shots,
            "returns": dict(returns),
            "seed": seed,
            "options": {"engine": "qutip", "qutip_data_layer": layer},
        }
        if sweep is not None:
            body["sweep"] = {"axes": sweep}
        payload = self._request("POST", f"/device/{session_id}/run", body=body)
        records: dict[str, np.ndarray] = {}
        for record_id, record in payload.get("records", {}).items():
            array = np.asarray(record["data"])
            if record.get("return_type", "").startswith("iq_"):
                if array.shape[-1] != 2:
                    raise LiteTwinError("bad_response", f"{record_id} has malformed IQ data")
                array = array[..., 0] + 1j * array[..., 1]
            records[str(record_id)] = array
        return LiteRun(
            records=records,
            provenance=dict(payload.get("provenance", {})),
            failures=list(payload.get("failures", [])),
        )


def session_id_from_env(client: LiteTwinClient) -> str:
    """Resolve and verify the operator-provisioned session inherited by QCA."""
    session_id = os.environ.get(SESSION_ENV)
    if not session_id:
        raise LiteTwinError(
            "missing_session",
            f"{SESSION_ENV} is required; provision a seeded or explicit session first",
        )
    descriptor = client.describe_session(session_id)
    if descriptor.get("status") != "active":
        raise LiteTwinError("inactive_session", f"session {session_id!r} is not active")
    return session_id


def qubit_index(target: str) -> int:
    if not isinstance(target, str) or not target.startswith("Q"):
        raise ValueError("target must be Q1 or Q2")
    try:
        qubit = int(target[1:]) - 1
    except ValueError as exc:
        raise ValueError("target must be Q1 or Q2") from exc
    if qubit not in (0, 1):
        raise ValueError("target must be Q1 or Q2")
    return qubit


def primitive(name: str, **arguments: Any) -> dict[str, Any]:
    return {"op": "primitive", "name": name, "arguments": arguments}


def serial(*children: Mapping[str, Any]) -> dict[str, Any]:
    return {"op": "serial", "children": [dict(child) for child in children]}


def scalar(value: Any, unit: str, name: str) -> dict[str, Any]:
    if isinstance(value, np.generic):
        value = value.item()
    return {"type": "scalar", "value": value, "unit": unit, "name": name}


def array(value: Any, unit: str, name: str) -> dict[str, Any]:
    return {
        "type": "array",
        "value": np.asarray(value).tolist(),
        "unit": unit,
        "name": name,
    }


def metadata(value: Mapping[str, Any], name: str) -> dict[str, Any]:
    return {"type": "metadata", "value": dict(value), "unit": "", "name": name}


def fit_plot(
    *,
    name: str,
    title: str,
    x: Any,
    y: Any,
    fit: Any,
    xlabel: str,
    ylabel: str,
    feature_x: float,
    feature_label: str,
) -> dict[str, Any]:
    x_values = np.asarray(x, dtype=float).tolist()
    y_values = np.asarray(y, dtype=float).tolist()
    fit_values = np.asarray(fit, dtype=float).tolist()
    return {
        "name": name,
        "format": "plotly",
        "data": {
            "data": [
                {
                    "x": x_values,
                    "y": y_values,
                    "type": "scatter",
                    "mode": "markers",
                    "name": "QuTiP data",
                },
                {
                    "x": x_values,
                    "y": fit_values,
                    "type": "scatter",
                    "mode": "lines",
                    "name": "fit",
                },
            ],
            "layout": {
                "title": title,
                "xaxis": {"title": xlabel},
                "yaxis": {"title": ylabel},
                "shapes": [
                    {
                        "type": "line",
                        "x0": feature_x,
                        "x1": feature_x,
                        "y0": 0,
                        "y1": 1,
                        "yref": "paper",
                        "line": {"color": "red", "dash": "dash"},
                    }
                ],
                "annotations": [
                    {
                        "x": feature_x,
                        "y": 1,
                        "yref": "paper",
                        "text": feature_label,
                        "showarrow": False,
                    }
                ],
            },
        },
    }


def failure(message: str) -> dict[str, Any]:
    return {"status": "failed", "error": message}
