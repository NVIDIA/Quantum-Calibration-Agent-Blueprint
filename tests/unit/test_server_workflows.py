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


@pytest.fixture
def sentinel_workflows(tmp_path, monkeypatch):
    """Persisted workflows that a None-returning loader cannot tell apart."""
    workflows_dir = tmp_path / "workflows"
    for name, content in [
        ("null_wf", "null"),
        ("corrupt_wf", "{not valid json"),
        ("good_wf", json.dumps({"id": "good_wf", "name": "Good", "nodes": []})),
    ]:
        (workflows_dir / name).mkdir(parents=True)
        (workflows_dir / name / "workflow.json").write_text(content)
    monkeypatch.setattr(server, "WORKFLOWS_DIR", workflows_dir)
    return workflows_dir


@pytest.mark.asyncio
async def test_persisted_null_is_invalid_not_missing(sentinel_workflows):
    """A workflow.json holding the literal null is malformed, not absent.

    json.loads returns None for it, which collided with the loader's
    missing-file sentinel and hid the structural error behind a 404.
    """
    result = await server.get_workflow("null_wf")

    assert result["error"] == "Invalid workflow data"
    assert "details" in result


@pytest.mark.asyncio
async def test_unparseable_workflow_is_invalid_not_missing(sentinel_workflows):
    """A corrupt workflow.json is reported as invalid rather than absent."""
    result = await server.get_workflow("corrupt_wf")

    assert result["error"] == "Invalid workflow data"
    assert "details" in result


@pytest.mark.asyncio
async def test_absent_workflow_is_still_reported_missing(sentinel_workflows):
    """The two conditions stay distinguishable in the other direction."""
    result = await server.get_workflow("no_such_workflow")

    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_malformed_workflows_are_listed_with_their_error(sentinel_workflows):
    """Malformed workflows appear in the list, flagged, rather than vanishing."""
    result = await server.list_workflows()

    by_id = {w["workflow_id"]: w for w in result["workflows"]}
    assert set(by_id) == {"null_wf", "corrupt_wf", "good_wf"}
    assert "error" in by_id["null_wf"]
    assert "error" in by_id["corrupt_wf"]
    assert "error" not in by_id["good_wf"]
