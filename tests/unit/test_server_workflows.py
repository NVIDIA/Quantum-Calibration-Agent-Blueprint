# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Regression tests for defensive workflow reads in the Web API."""

import json

import pytest

import server


@pytest.fixture
def malformed_workflow(tmp_path, monkeypatch):
    workflows_dir = tmp_path / "workflows"
    workflow_dir = workflows_dir / "bad_node"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "workflow.json").write_text(
        json.dumps({"id": "bad_node", "name": "Bad", "nodes": ["node"]})
    )
    monkeypatch.setattr(server, "WORKFLOWS_DIR", workflows_dir)
    return workflows_dir


@pytest.mark.asyncio
async def test_get_workflow_reports_non_object_node(malformed_workflow):
    result = await server.get_workflow("bad_node")

    assert result["error"] == "Invalid workflow data"
    assert "must be an object" in result["details"]


@pytest.mark.asyncio
async def test_list_workflows_reports_non_object_node(malformed_workflow):
    result = await server.list_workflows()

    assert result["workflows"][0]["workflow_id"] == "bad_node"
    assert "must be an object" in result["workflows"][0]["error"]
