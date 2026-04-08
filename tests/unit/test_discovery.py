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

"""Unit tests for core/discovery.py."""

import pytest
from pathlib import Path
from core.discovery import (
    discover_experiments,
    get_experiment_schema,
    validate_script,
    _extract_schema_from_file,
    _parse_function_parameters,
)


class TestDiscoverExperiments:
    """Tests for discover_experiments function."""

    def test_discover_from_scripts_dir(self, temp_scripts_dir):
        """Discover experiments from scripts directory."""
        experiments = discover_experiments(temp_scripts_dir)
        assert len(experiments) >= 1
        assert experiments[0].name == "test_experiment"

    def test_discover_empty_dir(self, tmp_path):
        """Empty directory returns empty list."""
        experiments = discover_experiments(tmp_path)
        assert experiments == []

    def test_discover_nonexistent_dir(self, tmp_path):
        """Nonexistent directory returns empty list."""
        experiments = discover_experiments(tmp_path / "nonexistent")
        assert experiments == []

    def test_skip_private_files(self, tmp_path):
        """Private files (underscore prefix) are skipped."""
        (tmp_path / "_private.py").write_text("def _private() -> dict: pass")
        experiments = discover_experiments(tmp_path)
        assert len(experiments) == 0

    def test_discover_multiple_scripts(self, tmp_path):
        """Discover multiple experiment scripts."""
        (tmp_path / "exp1.py").write_text(
            '''
from typing import Annotated

def exp1(param: Annotated[float, (0.0, 10.0)] = 1.0) -> dict:
    """First experiment."""
    return {"status": "success"}
'''
        )
        (tmp_path / "exp2.py").write_text(
            '''
from typing import Annotated

def exp2(param: Annotated[int, (0, 100)] = 50) -> dict:
    """Second experiment."""
    return {"status": "success"}
'''
        )
        experiments = discover_experiments(tmp_path)
        assert len(experiments) == 2
        names = {exp.name for exp in experiments}
        assert names == {"exp1", "exp2"}

    def test_skip_syntax_error_scripts(self, tmp_path):
        """Scripts with syntax errors are skipped."""
        (tmp_path / "valid.py").write_text(
            '''
def valid(x: float = 1.0) -> dict:
    """Valid script."""
    return {"status": "success"}
'''
        )
        (tmp_path / "invalid.py").write_text("def broken(:\n    pass")
        experiments = discover_experiments(tmp_path)
        assert len(experiments) == 1
        assert experiments[0].name == "valid"


class TestGetExperimentSchema:
    """Tests for get_experiment_schema function."""

    def test_get_existing_schema(self, temp_scripts_dir):
        """Get schema for existing experiment."""
        schema = get_experiment_schema("test_experiment", temp_scripts_dir)
        assert schema is not None
        assert schema.name == "test_experiment"
        assert len(schema.parameters) >= 1

    def test_get_nonexistent_schema(self, temp_scripts_dir):
        """Get schema for nonexistent experiment returns None."""
        schema = get_experiment_schema("nonexistent", temp_scripts_dir)
        assert schema is None

    def test_schema_has_parameters(self, temp_scripts_dir):
        """Schema includes parameter specifications."""
        schema = get_experiment_schema("test_experiment", temp_scripts_dir)
        assert schema is not None
        param = schema.parameters[0]
        assert param.name == "param1"
        assert param.type == "float"
        assert param.default == 5.0
        assert param.range == (0.0, 10.0)


class TestValidateScript:
    """Tests for validate_script function."""

    def test_validate_valid_script(self, temp_scripts_dir):
        """Validate a valid experiment script."""
        script_path = temp_scripts_dir / "test_experiment.py"
        result = validate_script(script_path)
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["schema"] is not None
        assert result["schema"]["name"] == "test_experiment"

    def test_validate_nonexistent_file(self, tmp_path):
        """Validate nonexistent file."""
        result = validate_script(tmp_path / "nonexistent.py")
        assert result["valid"] is False
        assert any(
            "not found" in str(e).lower() or "does not exist" in str(e).lower()
            for e in result["errors"]
        )

    def test_validate_non_python_file(self, tmp_path):
        """Validate non-Python file."""
        txt_file = tmp_path / "script.txt"
        txt_file.write_text("hello")
        result = validate_script(txt_file)
        assert result["valid"] is False
        assert any(".py" in str(e) for e in result["errors"])

    def test_validate_syntax_error(self, tmp_path):
        """Validate script with syntax error."""
        bad_script = tmp_path / "bad.py"
        bad_script.write_text("def broken(:\n    pass")
        result = validate_script(bad_script)
        assert result["valid"] is False
        assert any(
            "syntax" in c["check"].lower() for c in result["checks"] if not c["passed"]
        )

    def test_validate_no_return_type(self, tmp_path):
        """Script without return type annotation fails."""
        script = tmp_path / "no_return.py"
        script.write_text("def experiment(x: float = 1.0):\n    return {}")
        result = validate_script(script)
        assert result["valid"] is False
        assert any("return type" in str(e).lower() for e in result["errors"])

    def test_validate_wrong_return_type(self, tmp_path):
        """Script with wrong return type fails."""
        script = tmp_path / "wrong_return.py"
        script.write_text("def experiment(x: float = 1.0) -> list:\n    return []")
        result = validate_script(script)
        assert result["valid"] is False
        assert any("dict" in str(e) for e in result["errors"])

    def test_validate_private_file(self, tmp_path):
        """Private files (starting with underscore) fail validation."""
        script = tmp_path / "_private.py"
        script.write_text(
            '''
def experiment(x: float = 1.0) -> dict:
    """Private experiment."""
    return {"status": "success"}
'''
        )
        result = validate_script(script)
        assert result["valid"] is False
        assert any(
            "underscore" in str(e).lower() or "private" in str(e).lower()
            for e in result["errors"]
        )

    def test_validate_no_public_function(self, tmp_path):
        """Script without public function fails."""
        script = tmp_path / "no_public.py"
        script.write_text(
            '''
def _private() -> dict:
    """Private function."""
    return {}
'''
        )
        result = validate_script(script)
        assert result["valid"] is False
        assert any("public function" in str(e).lower() for e in result["errors"])

    def test_validate_no_typed_parameters(self, tmp_path):
        """Script without typed parameters fails."""
        script = tmp_path / "no_types.py"
        script.write_text(
            '''
def experiment(x, y) -> dict:
    """No type annotations."""
    return {}
'''
        )
        result = validate_script(script)
        assert result["valid"] is False
        assert any("type annotation" in str(e).lower() for e in result["errors"])

    def test_validate_checks_structure(self, temp_scripts_dir):
        """Validate returns proper checks structure."""
        script_path = temp_scripts_dir / "test_experiment.py"
        result = validate_script(script_path)

        assert "checks" in result
        assert isinstance(result["checks"], list)
        assert all(
            "check" in c and "passed" in c and "message" in c for c in result["checks"]
        )

        # Verify expected checks are present
        check_names = {c["check"] for c in result["checks"]}
        expected = {
            "file_exists",
            "python_file",
            "not_private",
            "syntax_valid",
            "has_public_function",
            "return_type_dict",
            "has_typed_parameters",
        }
        assert expected.issubset(check_names)

    def test_validate_warnings_for_multiple_functions(self, tmp_path):
        """Warns when multiple public functions are present."""
        script = tmp_path / "multi_func.py"
        script.write_text(
            '''
from typing import Annotated

def first_experiment(x: Annotated[float, (0.0, 10.0)] = 1.0) -> dict:
    """First function."""
    return {"status": "success"}

def second_experiment(y: Annotated[int, (0, 100)] = 50) -> dict:
    """Second function."""
    return {"status": "success"}
'''
        )
        result = validate_script(script)
        assert result["valid"] is True
        assert any("multiple" in str(w).lower() for w in result["warnings"])
        # Should use the first function
        assert result["schema"]["name"] == "first_experiment"

    def test_validate_annotated_ranges(self, tmp_path):
        """Validates Annotated range constraints properly."""
        script = tmp_path / "with_ranges.py"
        script.write_text(
            '''
from typing import Annotated

def experiment(
    freq: Annotated[float, (4.0, 6.0)] = 5.0,
    count: Annotated[int, (1, 1000)] = 100
) -> dict:
    """Experiment with ranges."""
    return {"status": "success"}
'''
        )
        result = validate_script(script)
        assert result["valid"] is True

        # Check that parameters have ranges
        params = result["schema"]["parameters"]
        assert len(params) == 2

        freq_param = next(p for p in params if p["name"] == "freq")
        assert freq_param["range"] == [4.0, 6.0]

        count_param = next(p for p in params if p["name"] == "count")
        assert count_param["range"] == [1, 1000]

    def test_validate_mixed_required_optional(self, tmp_path):
        """Validates scripts with mixed required and optional parameters."""
        script = tmp_path / "mixed_params.py"
        script.write_text(
            '''
from typing import Annotated

def experiment(
    required_param: Annotated[float, (0.0, 10.0)],
    optional_param: Annotated[int, (0, 100)] = 50
) -> dict:
    """Mixed parameters."""
    return {"status": "success"}
'''
        )
        result = validate_script(script)
        assert result["valid"] is True

        params = result["schema"]["parameters"]
        assert len(params) == 2

        required = next(p for p in params if p["name"] == "required_param")
        assert required["required"] is True
        assert required["default"] is None

        optional = next(p for p in params if p["name"] == "optional_param")
        assert optional["required"] is False
        assert optional["default"] == 50

    def test_validate_no_docstring_warning(self, tmp_path):
        """Warns when function lacks docstring."""
        script = tmp_path / "no_doc.py"
        script.write_text(
            """
from typing import Annotated

def experiment(x: Annotated[float, (0.0, 10.0)] = 1.0) -> dict:
    return {"status": "success"}
"""
        )
        result = validate_script(script)
        assert result["valid"] is True
        assert any("docstring" in str(w).lower() for w in result["warnings"])
