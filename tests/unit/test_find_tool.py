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

"""Tests for tools/find_tool.py."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from tools.find_tool import find


@pytest.fixture
def populated_tmp(tmp_path):
    """Create a temp directory with files and subdirectories."""
    (tmp_path / "hello.py").write_text("print('hello')")
    (tmp_path / "world.py").write_text("print('world')")
    (tmp_path / "readme.txt").write_text("readme")
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.py").write_text("pass")
    (subdir / "data.csv").write_text("a,b")
    return tmp_path


class TestFindFiles:
    """Test basic file finding in a real directory."""

    def test_find_all_entries(self, populated_tmp):
        result = find.invoke({"path": str(populated_tmp)})
        assert "matches" in result
        assert "count" in result
        assert result["count"] > 0
        # Should include the root directory itself plus files and subdir
        assert any("hello.py" in m for m in result["matches"])
        assert any("subdir" in m for m in result["matches"])

    def test_find_with_name_pattern(self, populated_tmp):
        result = find.invoke({"path": str(populated_tmp), "name": "*.py"})
        assert "matches" in result
        # hello.py, world.py, nested.py
        assert result["count"] == 3
        for match in result["matches"]:
            assert match.endswith(".py")

    def test_find_type_file(self, populated_tmp):
        result = find.invoke({"path": str(populated_tmp), "type": "f"})
        assert "matches" in result
        # All entries should be files, not directories
        for match in result["matches"]:
            assert not match.endswith("subdir")
        # 5 files total: hello.py, world.py, readme.txt, nested.py, data.csv
        assert result["count"] == 5

    def test_find_type_directory(self, populated_tmp):
        result = find.invoke({"path": str(populated_tmp), "type": "d"})
        assert "matches" in result
        # root dir + subdir
        assert result["count"] == 2

    def test_find_with_maxdepth(self, populated_tmp):
        result = find.invoke(
            {"path": str(populated_tmp), "name": "*.py", "maxdepth": 1}
        )
        assert "matches" in result
        # Only top-level .py files: hello.py, world.py (not nested.py)
        assert result["count"] == 2


class TestFindErrors:
    """Test error handling."""

    def test_nonexistent_directory(self):
        result = find.invoke({"path": "/nonexistent/path/that/does/not/exist"})
        assert "error" in result

    @patch("tools.find_tool.subprocess.run")
    def test_timeout_handling(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="find", timeout=30)
        result = find.invoke({"path": "/tmp"})
        assert result == {"error": "Find command timed out after 30 seconds"}

    @patch("tools.find_tool.subprocess.run")
    def test_general_exception(self, mock_run):
        mock_run.side_effect = OSError("Permission denied")
        result = find.invoke({"path": "/tmp"})
        assert result == {"error": "Permission denied"}

    @patch("tools.find_tool.subprocess.run")
    def test_nonzero_return_code(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="find: some error occurred",
            stdout="",
        )
        result = find.invoke({"path": "/tmp"})
        assert result == {"error": "find: some error occurred"}

    @patch("tools.find_tool.subprocess.run")
    def test_nonzero_return_code_empty_stderr(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="",
            stdout="",
        )
        result = find.invoke({"path": "/tmp"})
        assert result == {"error": "Find command failed"}
