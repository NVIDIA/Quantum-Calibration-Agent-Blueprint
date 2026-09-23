# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Run the QCA Lite twin as a serial local service."""

from __future__ import annotations

import argparse
import os

from werkzeug.serving import make_server

from .app import create_app
from .simulator import SimulationError, resolve_runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the minimal QuTiP QCA twin")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument(
        "--data-layer", choices=("auto", "cpu", "cuda"),
        default=os.environ.get("QCA_LITE_TWIN_DATA_LAYER", "auto"),
    )
    args = parser.parse_args()
    try:
        runtime = resolve_runtime(args.data_layer)
    except SimulationError as exc:
        parser.error(str(exc))
    app = create_app(runtime)
    server = make_server(args.host, args.port, app, threaded=False)
    print(
        f"QCA Lite twin ready on http://{args.host}:{args.port} "
        f"(qutip/{runtime.data_layer})",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
