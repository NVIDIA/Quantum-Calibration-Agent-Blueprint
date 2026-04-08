# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""VLM inspection tool for deep agent."""

import asyncio
import logging
from pathlib import Path
from typing import Any

import yaml
from langchain_core.tools import tool

from vlm.renderer import render_plot_to_base64
from vlm.providers import get_vlm_client

# Import core storage
ROOT_DIR = Path(__file__).parent.parent
from core import storage

logger = logging.getLogger(__name__)

# Paths
DATA_DIR = ROOT_DIR / "data" / "experiments"
CONFIG_PATH = ROOT_DIR / "config.yaml"


def _get_vlm_config() -> dict:
    """Load VLM configuration from config.yaml (reloads every call)."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)
            return config.get("vlm", {})
    return {}


@tool
def vlm_inspect(
    experiment_id: str,
    prompt: str = "Analyze this plot and describe what you observe. Note any peaks, trends, anomalies, or notable features.",
) -> dict[str, Any]:
    """Visually inspect all experiment plots using a vision language model.

    Use this tool to get AI-powered visual analysis of experiment plots.
    The VLM can identify peaks, trends, anomalies, and other features.
    All plots from the experiment are sent to the VLM for analysis.

    Args:
        experiment_id: ID of the experiment to analyze (from history_list)
        prompt: Analysis instructions - what to look for in the plots

    Returns:
        Dictionary with VLM analysis results
    """
    # Run async function in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_vlm_inspect_async(experiment_id, prompt))


async def _vlm_inspect_async(
    experiment_id: str,
    prompt: str,
) -> dict[str, Any]:
    """Async implementation of vlm_inspect."""
    try:
        # 1. Get VLM config
        vlm_config = _get_vlm_config()
        if not vlm_config:
            return {
                "status": "error",
                "error": "VLM not configured. Add 'vlm' section to config.yaml",
            }

        # 2. List available plots
        plots_meta = storage.list_plots(experiment_id, DATA_DIR)
        if plots_meta is None:
            return {
                "status": "error",
                "error": f"Experiment '{experiment_id}' not found",
            }

        if not plots_meta:
            return {
                "status": "error",
                "error": f"No plots found in experiment '{experiment_id}'",
                "hint": "This experiment may not have generated any plots",
            }

        # 3. Render ALL plots to base64 PNG
        images_base64 = []
        plot_names = []
        errors = []

        for plot_meta in plots_meta:
            plot_name = plot_meta["name"]
            plot = storage.get_plot(experiment_id, plot_name, DATA_DIR)

            if plot is None:
                errors.append(f"Failed to load plot '{plot_name}'")
                continue

            try:
                if plot["format"] == "plotly":
                    # Render Plotly JSON to PNG
                    img_b64 = render_plot_to_base64(plot["data"])
                elif plot["format"] in ("png", "jpeg", "jpg"):
                    # Already base64 encoded
                    img_b64 = plot["data"]
                else:
                    errors.append(
                        f"Unsupported format for plot '{plot_name}': {plot['format']}"
                    )
                    continue

                images_base64.append(img_b64)
                plot_names.append(plot_name)
            except Exception as e:
                logger.error(f"Failed to render plot '{plot_name}': {e}")
                errors.append(f"Failed to render '{plot_name}': {e}")

        if not images_base64:
            return {
                "status": "error",
                "error": "Failed to render any plots",
                "details": errors,
                "hint": "Ensure kaleido is installed: pip install kaleido",
            }

        # 4. Call VLM with all plots
        try:
            vlm = get_vlm_client(vlm_config)

            # Enhance prompt with plot count info
            full_prompt = prompt
            if len(images_base64) > 1:
                full_prompt = f"You are analyzing {len(images_base64)} plots from experiment '{experiment_id}'. Plot names: {', '.join(plot_names)}.\n\n{prompt}"

            analysis = await vlm.analyze_images(full_prompt, images_base64)
        except Exception as e:
            logger.error(f"VLM call failed: {e}")
            return {
                "status": "error",
                "error": f"VLM analysis failed: {e}",
            }

        result = {
            "status": "success",
            "experiment_id": experiment_id,
            "plots_analyzed": plot_names,
            "plot_count": len(images_base64),
            "analysis": analysis,
        }

        if errors:
            result["warnings"] = errors

        return result

    except Exception as e:
        logger.error(f"vlm_inspect failed: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }
