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

"""Integration tests for experiment execution pipeline."""

import pytest
from pathlib import Path
from unittest.mock import patch


class TestExperimentPipeline:
    """End-to-end tests for experiment pipeline."""

    def test_discover_run_store_load(self, temp_scripts_dir, temp_data_dir):
        """Full pipeline: discover → run → store → load."""
        from core import discovery, runner, storage
        from core.models import ExperimentResult
        from datetime import datetime, timezone

        # 1. Discover experiments
        experiments = discovery.discover_experiments(temp_scripts_dir)
        assert len(experiments) >= 1

        exp_schema = experiments[0]

        # 2. Run experiment
        result_dict = runner.run_experiment(
            exp_schema.name, {"param1": 5.0}, temp_scripts_dir
        )
        assert result_dict["status"] == "success"

        # 3. Store result
        now = datetime.now(timezone.utc)
        exp_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{exp_schema.name}"

        exp_result = ExperimentResult(
            id=exp_id,
            type=exp_schema.name,
            timestamp=now.isoformat().replace("+00:00", "Z"),
            status=result_dict["status"],
            params={"param1": 5.0},
            results=result_dict.get("data", {}),
        )
        storage.save_experiment(exp_result, temp_data_dir)

        # 4. Load and verify
        loaded = storage.load_experiment(exp_id, temp_data_dir)
        assert loaded is not None
        assert loaded.type == exp_schema.name
        assert loaded.status == "success"

    def test_lab_tool_full_workflow(self, temp_scripts_dir, temp_data_dir):
        """Test lab tool through full workflow."""
        from tools.lab_tool import lab, run_experiment as run_exp_tool

        with patch("tools.lab_tool.SCRIPTS_DIR", temp_scripts_dir):
            with patch("tools.lab_tool.DATA_DIR", temp_data_dir):
                # 1. Get info
                info = lab.invoke({"action": "info"})
                assert "experiments" in info

                # 2. Get schema
                exp_name = info["experiments"][0]["name"]
                schema = lab.invoke({"action": "schema", "experiment_name": exp_name})
                assert schema["name"] == exp_name

                # 3. Run experiment
                run_result = run_exp_tool.invoke(
                    {"experiment_name": exp_name, "params": {"param1": 5.0}}
                )
                assert run_result["status"] == "success"
                exp_id = run_result["id"]

                # 4. List history
                history = lab.invoke({"action": "history_list"})
                assert history["count"] >= 1

                # 5. Show experiment
                details = lab.invoke(
                    {"action": "history_show", "experiment_id": exp_id}
                )
                assert details["id"] == exp_id
