# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Minimal Flask HTTP surface consumed by QCA's existing TwinClient."""

from __future__ import annotations

import threading
import uuid
from typing import Any

from flask import Flask, jsonify, request

from .model import Device, ModelError, PROFILE_BUILD_VERSION, provision
from .simulator import Runtime, SimulationError, run, runtime_versions


_ERROR_STATUS = {
    "invalid_program": 400,
    "device_session": 404,
    "unsupported_feature": 422,
    "backend_unavailable": 503,
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def _descriptor(session_id: str, device: Device, runtime: Runtime) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "profile": device.profile,
        "construction": {"seed": device.seed, "truth_mode": device.truth_mode},
        "status": "active",
        "current_revision": device.config_version + 1,
        "qubit_ids": device.qubit_ids,
        "topology": {"edges": device.edges},
        "truth_digest": device.truth_digest,
        "profile_build_version": PROFILE_BUILD_VERSION,
        "data_layer_used": runtime.data_layer,
    }


def create_app(runtime: Runtime | None = None) -> Flask:
    runtime = runtime or Runtime("cpu")
    app = Flask(__name__)
    sessions: dict[str, Device] = {}
    execution_lock = threading.Lock()

    def get_session(session_id: str) -> Device:
        device = sessions.get(session_id)
        if device is None:
            raise ApiError("device_session", f"unknown device session {session_id!r}")
        return device

    @app.errorhandler(ApiError)
    def api_error(exc: ApiError):
        return jsonify({
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        }), _ERROR_STATUS.get(exc.code, 500)

    @app.errorhandler(ModelError)
    @app.errorhandler(SimulationError)
    def validation_error(exc):
        return jsonify({
            "code": "invalid_program",
            "message": str(exc),
            "details": None,
        }), 400

    @app.get("/healthz")
    def health():
        versions = runtime_versions()
        qutip_capability = {
            "available": True,
            "data_layers": {
                "cpu": True,
                "cuda": runtime.data_layer == "cuda",
            },
        }
        return jsonify({
            "status": "ready",
            "backend": {
                "cudaq_pulse_version": "qca-lite-qutip/1",
                "native_extension_available": False,
                "data_layer_used": runtime.data_layer,
                "fallback_reason": runtime.fallback_reason,
                "engines": {"qutip": qutip_capability},
                "versions": versions,
            },
        })

    @app.post("/sessions")
    def create_session():
        device = provision(request.get_json(silent=True) or {})
        session_id = str(uuid.uuid4())
        sessions[session_id] = device
        body = _descriptor(session_id, device, runtime)
        body["device_session"] = session_id
        return jsonify(body), 201

    @app.get("/sessions")
    def list_sessions():
        return jsonify({
            "sessions": [_descriptor(sid, device, runtime)
                         for sid, device in sessions.items()],
        })

    @app.get("/sessions/<session_id>")
    def describe_session(session_id: str):
        return jsonify(_descriptor(session_id, get_session(session_id), runtime))

    @app.get("/device/<session_id>/config")
    def get_config(session_id: str):
        device = get_session(session_id)
        return jsonify({
            "config": device.public_config(),
            "config_version": device.config_version,
        })

    @app.patch("/device/<session_id>/config")
    def patch_config(session_id: str):
        device = get_session(session_id)
        device.patch(request.get_json(silent=True) or {})
        return jsonify({
            "config": device.public_config(),
            "config_version": device.config_version,
        })

    @app.post("/device/<session_id>/reset")
    def reset_config(session_id: str):
        device = get_session(session_id)
        device.reset()
        return jsonify({
            "config": device.public_config(),
            "config_version": device.config_version,
        })

    @app.post("/device/<session_id>/run")
    def run_program(session_id: str):
        device = get_session(session_id)
        if not execution_lock.acquire(blocking=False):
            raise ApiError("backend_unavailable", "the serial lite twin is already running")
        try:
            return jsonify(run(device, request.get_json(silent=True) or {}, runtime)), 200
        finally:
            execution_lock.release()

    return app
