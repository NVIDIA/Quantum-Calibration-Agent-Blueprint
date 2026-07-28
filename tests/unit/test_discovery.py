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

import ast
import json

import pytest
from pathlib import Path
from core.discovery import (
    discover_experiments,
    get_experiment_schema,
    validate_script,
    _eval_default,
    _extract_schema_from_file,
    _parse_function_parameters,
)


def _default_of(expression: str):
    """Evaluate a default expression the way discovery sees it in a signature."""
    return _eval_default(ast.parse(expression, mode="eval").body)


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


NON_FINITE_DEFAULTS = [
    "1e1000",
    "-1e1000",
    "[1e1000, 2]",
    "{'a': 1e1000}",
    "[[1e1000]]",
    "{'a': {'b': -1e1000}}",
]


class TestEvalDefault:
    """Tests for _eval_default, which decides whether a default is portable JSON."""

    @pytest.mark.parametrize(
        "expression,expected",
        [
            ("1.5", 1.5),
            ("1", 1),
            ("True", True),
            ("'x'", "x"),
            ("[1, 2]", [1, 2]),
            ("{'a': 1}", {"a": 1}),
            ("None", None),
        ],
    )
    def test_portable_defaults_resolve(self, expression, expected):
        """Values that survive JSON unchanged are resolved."""
        resolved, value = _default_of(expression)
        assert resolved is True
        assert value == expected

    def test_bool_is_not_collapsed_to_int(self):
        """A bool default stays a bool rather than becoming 1."""
        _, true_value = _default_of("True")
        _, one_value = _default_of("1")
        assert isinstance(true_value, bool)
        assert isinstance(one_value, bool) is False

    @pytest.mark.parametrize("expression", NON_FINITE_DEFAULTS)
    def test_non_finite_defaults_are_unresolved(self, expression):
        """Infinity and NaN are not standard JSON, so they must not resolve.

        json.dumps emits the bare token Infinity by default, which strict
        parsers and non-Python consumers reject.
        """
        assert _default_of(expression) == (False, None)

    def test_nan_default_is_unresolved(self):
        """NaN never compares equal to itself, but must be rejected explicitly."""
        assert _default_of("float('nan')") == (False, None)

    @pytest.mark.parametrize(
        "expression",
        [
            "(1, 2)",
            "{1: 'a'}",
            "{None: 'a'}",
        ],
    )
    def test_round_trip_rejections_are_retained(self, expression):
        """Tuple coercion and non-string dict keys must still be rejected.

        Strict encoding alone does not catch these: a tuple round-trips to a
        list and an int key round-trips to a string key. Only comparing the
        decoded value against the original catches them.
        """
        assert _default_of(expression) == (False, None)


class TestNonFinitePersistence:
    """Non-finite defaults must not escape into any JSON surface."""

    @pytest.fixture
    def non_finite_scripts_dir(self, tmp_path):
        """Experiment whose signature carries non-finite and unportable defaults."""
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "__init__.py").write_text("")
        (scripts_dir / "edge_defaults.py").write_text(
            '''
from typing import Annotated

def edge_defaults(
    finite: Annotated[float, (0.0, 10.0)] = 5.0,
    positive_infinity: float = 1e1000,
    negative_infinity: float = -1e1000,
    nested_infinity: list = [1e1000, 2],
    mapped_infinity: dict = {"a": 1e1000},
) -> dict:
    """Experiment with defaults that are not portable JSON."""
    return {"status": "success", "data": {"result": finite}}
'''
        )
        return scripts_dir

    def test_non_finite_defaults_are_not_resolved(self, non_finite_scripts_dir):
        """Discovery marks every non-finite default unresolved."""
        schema = get_experiment_schema("edge_defaults", non_finite_scripts_dir)
        assert schema is not None
        by_name = {p.name: p for p in schema.parameters}

        assert by_name["finite"].default_resolved is True
        assert by_name["finite"].default == 5.0

        for name in (
            "positive_infinity",
            "negative_infinity",
            "nested_infinity",
            "mapped_infinity",
        ):
            assert by_name[name].default_resolved is False, name
            assert by_name[name].default is None, name

    def test_schema_encodes_under_strict_json(self, non_finite_scripts_dir):
        """The schema the CLI prints must be parseable by a strict JSON reader."""
        schema = get_experiment_schema("edge_defaults", non_finite_scripts_dir)
        assert schema is not None

        encoded = json.dumps(schema.to_dict(), allow_nan=False)
        assert "Infinity" not in encoded
        assert "NaN" not in encoded
        # A strict reader rejects the non-standard tokens outright.
        json.loads(encoded, parse_constant=_reject_constant)

    def test_non_finite_annotated_bound_becomes_open(self, tmp_path):
        """A range bound also reaches schema JSON, so it must be finite too.

        Fixing the defaults left Annotated ranges able to
        carry infinity into the same output. The non-finite bound becomes
        None, meaning open on that side, so the bound that was finite keeps
        being enforced.
        """
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "__init__.py").write_text("")
        (scripts_dir / "bad_range.py").write_text(
            '''
from typing import Annotated

def bad_range(
    unbounded: Annotated[float, (0.0, 1e1000)] = 1.0,
    bounded: Annotated[float, (0.0, 10.0)] = 1.0,
) -> dict:
    """Experiment with an unbounded range."""
    return {"status": "success", "data": {}}
'''
        )
        schema = get_experiment_schema("bad_range", scripts_dir)
        assert schema is not None
        by_name = {p.name: p for p in schema.parameters}

        assert by_name["unbounded"].range == (0.0, None)
        assert by_name["bounded"].range == (0.0, 10.0)

        encoded = json.dumps(schema.to_dict(), allow_nan=False)
        assert "Infinity" not in encoded

        # The finite bound is still enforced; only the open side is skipped.
        from core.runner import validate_params

        assert validate_params({"unbounded": -5.0}, schema) != []
        assert validate_params({"unbounded": 1e6}, schema) == []

    def test_validate_script_output_encodes_under_strict_json(
        self, non_finite_scripts_dir
    ):
        """validate_script embeds the schema, so it needs the same guarantee."""
        result = validate_script(non_finite_scripts_dir / "edge_defaults.py")

        assert result["valid"] is True
        encoded = json.dumps(result, allow_nan=False)
        assert "Infinity" not in encoded
        json.loads(encoded, parse_constant=_reject_constant)

    def test_unresolved_defaults_are_omitted_from_effective_params(
        self, non_finite_scripts_dir
    ):
        """Unresolved defaults are left out so Python applies the real value."""
        from core.runner import resolve_params

        schema = get_experiment_schema("edge_defaults", non_finite_scripts_dir)
        assert schema is not None

        effective = resolve_params({}, schema)
        assert effective == {"finite": 5.0}
        json.dumps(effective, allow_nan=False)


def _reject_constant(name):
    raise AssertionError(f"non-standard JSON constant present: {name}")
