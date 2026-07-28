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


@pytest.fixture
def partial_node_workflow(tmp_path, monkeypatch):
    """A workflow whose node is an object but is missing required fields."""
    workflows_dir = tmp_path / "workflows"
    workflow_dir = workflows_dir / "partial"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "workflow.json").write_text(
        json.dumps(
            {
                "id": "partial",
                "name": "Partial",
                "nodes": [{"state": "success"}],
            }
        )
    )
    monkeypatch.setattr(server, "WORKFLOWS_DIR", workflows_dir)
    return workflows_dir


@pytest.mark.asyncio
async def test_get_workflow_survives_node_missing_fields(partial_node_workflow):
    """A node missing 'id'/'name' must not raise KeyError from the endpoint."""
    result = await server.get_workflow("partial")

    assert "error" not in result
    assert result["nodes"][0]["id"] is None
    assert result["nodes"][0]["name"] is None


@pytest.mark.asyncio
async def test_list_workflows_survives_node_missing_fields(partial_node_workflow):
    """The list endpoint must not raise on nodes missing required fields."""
    result = await server.list_workflows()

    assert result["workflows"][0]["workflow_id"] == "partial"
    assert "error" not in result["workflows"][0]


@pytest.fixture
def falsy_workflow(tmp_path, monkeypatch):
    """A persisted workflow whose JSON value is falsy but present."""
    workflows_dir = tmp_path / "workflows"
    workflow_dir = workflows_dir / "empty"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "workflow.json").write_text("[]")
    monkeypatch.setattr(server, "WORKFLOWS_DIR", workflows_dir)
    return workflows_dir


@pytest.mark.asyncio
async def test_falsy_workflow_is_invalid_not_missing(falsy_workflow):
    """A malformed persisted workflow is a validation error, not a 404.

    The falsy check treated a persisted [] or {} as an
    absent workflow, so the structural error was never reported.
    """
    result = await server.get_workflow("empty")

    assert result["error"] == "Invalid workflow data"
    assert "must be an object" in result["details"]


@pytest.mark.asyncio
async def test_falsy_workflow_is_listed_with_its_error(falsy_workflow):
    result = await server.list_workflows()

    assert result["workflows"][0]["workflow_id"] == "empty"
    assert "error" in result["workflows"][0]
