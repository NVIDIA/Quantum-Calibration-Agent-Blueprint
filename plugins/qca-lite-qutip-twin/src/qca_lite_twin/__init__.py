# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0

"""Small QuTiP-backed digital twin for focused QCA calibration workflows."""

__version__ = "1"


def create_app(*args, **kwargs):
    """Import Flask and QuTiP only when the service is actually requested."""
    from .app import create_app as _create_app

    return _create_app(*args, **kwargs)


__all__ = ["__version__", "create_app"]
