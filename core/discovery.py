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

"""Experiment discovery via AST parsing."""

import ast
from pathlib import Path
from typing import Optional

from .models import ExperimentSchema, ParameterSpec


def discover_experiments(scripts_dir: Path) -> list[ExperimentSchema]:
    """Discover experiments from Python scripts using AST parsing.

    Scans the scripts directory for Python files and extracts experiment
    schemas without executing any code.

    Args:
        scripts_dir: Directory containing experiment scripts

    Returns:
        List of experiment schemas
    """
    experiments = []

    if not scripts_dir.exists() or not scripts_dir.is_dir():
        return experiments

    for script_path in scripts_dir.glob("*.py"):
        # Skip private files
        if script_path.name.startswith("_"):
            continue

        schema = _extract_schema_from_file(script_path)
        if schema:
            experiments.append(schema)

    return experiments


def get_experiment_schema(name: str, scripts_dir: Path) -> Optional[ExperimentSchema]:
    """Get schema for a specific experiment by name.

    Args:
        name: Experiment name (function name)
        scripts_dir: Directory containing experiment scripts

    Returns:
        Experiment schema or None if not found
    """
    experiments = discover_experiments(scripts_dir)
    for exp in experiments:
        if exp.name == name:
            return exp
    return None


def _extract_schema_from_file(script_path: Path) -> Optional[ExperimentSchema]:
    """Extract experiment schema from a single Python file.

    Args:
        script_path: Path to Python script

    Returns:
        ExperimentSchema or None if no valid experiment found
    """
    try:
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return None

    # Find first public top-level function
    func_def = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                func_def = node
                break

    if func_def is None:
        return None

    # Check return type annotation - must be dict
    if func_def.returns:
        return_type = _get_type_name(func_def.returns)
        if return_type != "dict":
            return None
    else:
        # No return type annotation - skip
        return None

    # Extract function details
    func_name = func_def.name
    func_doc = ast.get_docstring(func_def) or ""
    description = func_doc.split("\n")[0] if func_doc else ""

    # Parse parameters
    parameters = _parse_function_parameters(func_def)

    # Skip if no parameters have type hints
    if not any(p for p in parameters):
        return None

    return ExperimentSchema(
        name=func_name,
        description=description,
        parameters=parameters,
        module_path=str(script_path),
    )


def _parse_function_parameters(func_def: ast.FunctionDef) -> list[ParameterSpec]:
    """Parse function parameters from AST.

    Args:
        func_def: AST FunctionDef node

    Returns:
        List of parameter specifications
    """
    parameters = []

    # Get all positional and positional-only args
    all_args = list(getattr(func_def.args, "posonlyargs", []) or []) + list(
        func_def.args.args
    )

    # Get defaults (aligned from the end)
    num_defaults = len(func_def.args.defaults)
    num_args = len(all_args)
    default_offset = num_args - num_defaults

    for i, arg in enumerate(all_args):
        # Skip if no type annotation
        if not arg.annotation:
            continue

        param_name = arg.arg
        type_info = _parse_annotation(arg.annotation)

        # Determine if required based on default value
        has_default = i >= default_offset
        default_value = None
        if has_default:
            default_node = func_def.args.defaults[i - default_offset]
            default_value = _eval_literal(default_node)

        parameters.append(
            ParameterSpec(
                name=param_name,
                type=type_info["type"],
                default=default_value,
                range=type_info["range"],
                required=not has_default,
            )
        )

    # Handle keyword-only args
    for kwarg, kw_default in zip(func_def.args.kwonlyargs, func_def.args.kw_defaults):
        if not kwarg.annotation:
            continue

        type_info = _parse_annotation(kwarg.annotation)
        default_value = None if kw_default is None else _eval_literal(kw_default)

        parameters.append(
            ParameterSpec(
                name=kwarg.arg,
                type=type_info["type"],
                default=default_value,
                range=type_info["range"],
                required=kw_default is None,
            )
        )

    return parameters


def _parse_annotation(annotation: ast.expr) -> dict:
    """Parse type annotation to extract type and range.

    Args:
        annotation: AST annotation node

    Returns:
        Dict with 'type' and 'range' keys
    """
    result = {"type": "str", "range": None}

    # Handle Annotated[type, (min, max)]
    if isinstance(annotation, ast.Subscript):
        base_name = _get_type_name(annotation.value)

        if base_name == "Annotated":
            return _parse_annotated(annotation)
        elif base_name:
            result["type"] = base_name

    # Handle simple types
    elif isinstance(annotation, ast.Name):
        type_map = {
            "float": "float",
            "int": "int",
            "str": "str",
            "bool": "bool",
            "list": "list",
        }
        result["type"] = type_map.get(annotation.id, "str")

    return result


def _parse_annotated(subscript: ast.Subscript) -> dict:
    """Parse Annotated[type, (min, max)] annotation.

    Args:
        subscript: AST Subscript node

    Returns:
        Dict with 'type' and 'range' keys
    """
    result = {"type": "str", "range": None}

    # Handle Python 3.8's ast.Index wrapper
    slice_node = subscript.slice
    if hasattr(ast, "Index") and isinstance(slice_node, ast.Index):
        slice_node = slice_node.value

    if not isinstance(slice_node, ast.Tuple):
        return result

    elements = slice_node.elts
    if len(elements) < 2:
        return result

    # First element is the type
    type_node = elements[0]
    if isinstance(type_node, ast.Name):
        type_map = {
            "float": "float",
            "int": "int",
            "str": "str",
            "bool": "bool",
        }
        result["type"] = type_map.get(type_node.id, "str")

    # Second element is the constraint tuple
    constraint_node = elements[1]
    if hasattr(ast, "Index") and isinstance(constraint_node, ast.Index):
        constraint_node = constraint_node.value

    if isinstance(constraint_node, ast.Tuple):
        values = [_eval_literal(el) for el in constraint_node.elts]
        values = [v for v in values if v is not None]

        if len(values) >= 2 and all(isinstance(v, (int, float)) for v in values):
            result["range"] = (values[0], values[1])

    return result


def _get_type_name(node: ast.expr) -> Optional[str]:
    """Get the type name from an annotation node.

    Args:
        node: AST expression node

    Returns:
        Type name as string or None
    """
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return node.attr
    elif isinstance(node, ast.Subscript):
        return _get_type_name(node.value)
    return None


def _eval_literal(node: ast.expr) -> Optional[any]:
    """Safely evaluate AST literal to Python value.

    Args:
        node: AST expression node

    Returns:
        Python value or None if cannot evaluate
    """
    if node is None:
        return None

    # Python 3.8+ uses ast.Constant for all literals
    if isinstance(node, ast.Constant):
        return node.value

    # Handle negative numbers
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _eval_literal(node.operand)
        if operand is not None:
            return -operand
        return None

    # Handle positive numbers
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _eval_literal(node.operand)

    # Handle lists
    if isinstance(node, ast.List):
        values = [_eval_literal(el) for el in node.elts]
        if None in values:
            return None
        return values

    # Handle tuples
    if isinstance(node, ast.Tuple):
        values = [_eval_literal(el) for el in node.elts]
        if None in values:
            return None
        return tuple(values)

    # Handle Name for constants
    if isinstance(node, ast.Name):
        if node.id == "True":
            return True
        elif node.id == "False":
            return False
        elif node.id == "None":
            return None

    return None


def validate_script(script_path: Path) -> dict:
    """Validate a Python script as a lab experiment.

    Performs comprehensive validation and returns detailed results
    including what is correct, what is missing, and parsed schema info.

    Args:
        script_path: Path to Python script to validate

    Returns:
        Dict with validation results:
        - valid: bool - Whether script is a valid experiment
        - checks: list - List of validation checks with status
        - schema: dict - Parsed schema if valid (name, description, parameters)
        - errors: list - List of error messages
        - warnings: list - List of warning messages
    """
    result = {
        "valid": False,
        "checks": [],
        "schema": None,
        "errors": [],
        "warnings": [],
    }

    # Check 1: File exists
    if not script_path.exists():
        result["checks"].append(
            {"check": "file_exists", "passed": False, "message": "File does not exist"}
        )
        result["errors"].append(f"File not found: {script_path}")
        return result
    result["checks"].append(
        {"check": "file_exists", "passed": True, "message": "File exists"}
    )

    # Check 2: File is Python
    if script_path.suffix != ".py":
        result["checks"].append(
            {
                "check": "python_file",
                "passed": False,
                "message": "File is not a .py file",
            }
        )
        result["errors"].append(
            f"File must have .py extension, got: {script_path.suffix}"
        )
        return result
    result["checks"].append(
        {"check": "python_file", "passed": True, "message": "File has .py extension"}
    )

    # Check 3: File is not private
    if script_path.name.startswith("_"):
        result["checks"].append(
            {
                "check": "not_private",
                "passed": False,
                "message": "File name starts with underscore",
            }
        )
        result["errors"].append(
            "File name must not start with underscore (private files are ignored)"
        )
        return result
    result["checks"].append(
        {
            "check": "not_private",
            "passed": True,
            "message": "File is public (no underscore prefix)",
        }
    )

    # Check 4: Parse Python syntax
    try:
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except UnicodeDecodeError as e:
        result["checks"].append(
            {
                "check": "syntax_valid",
                "passed": False,
                "message": f"Encoding error: {e}",
            }
        )
        result["errors"].append(f"Cannot read file: {e}")
        return result
    except SyntaxError as e:
        result["checks"].append(
            {
                "check": "syntax_valid",
                "passed": False,
                "message": f"Syntax error at line {e.lineno}: {e.msg}",
            }
        )
        result["errors"].append(f"Syntax error at line {e.lineno}: {e.msg}")
        return result
    result["checks"].append(
        {"check": "syntax_valid", "passed": True, "message": "Python syntax is valid"}
    )

    # Check 5: Find public function
    func_def = None
    public_functions = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                public_functions.append(node.name)
                if func_def is None:
                    func_def = node

    if not public_functions:
        result["checks"].append(
            {
                "check": "has_public_function",
                "passed": False,
                "message": "No public function found",
            }
        )
        result["errors"].append(
            "Script must contain at least one public function (without underscore prefix)"
        )
        return result

    if len(public_functions) > 1:
        result["warnings"].append(
            f"Multiple public functions found: {public_functions}. Only the first one '{public_functions[0]}' will be used."
        )

    result["checks"].append(
        {
            "check": "has_public_function",
            "passed": True,
            "message": f"Found public function: {func_def.name}",
        }
    )

    # Check 6: Return type annotation
    if func_def.returns:
        return_type = _get_type_name(func_def.returns)
        if return_type != "dict":
            result["checks"].append(
                {
                    "check": "return_type_dict",
                    "passed": False,
                    "message": f"Return type is '{return_type}', must be 'dict'",
                }
            )
            result["errors"].append(
                f"Function must return 'dict', but has return type '{return_type}'"
            )
            return result
        result["checks"].append(
            {
                "check": "return_type_dict",
                "passed": True,
                "message": "Return type is dict",
            }
        )
    else:
        result["checks"].append(
            {
                "check": "return_type_dict",
                "passed": False,
                "message": "No return type annotation",
            }
        )
        result["errors"].append("Function must have return type annotation '-> dict'")
        return result

    # Check 7: Has docstring
    func_doc = ast.get_docstring(func_def) or ""
    if func_doc:
        result["checks"].append(
            {
                "check": "has_docstring",
                "passed": True,
                "message": "Function has docstring",
            }
        )
    else:
        result["checks"].append(
            {"check": "has_docstring", "passed": False, "message": "No docstring found"}
        )
        result["warnings"].append(
            "Function should have a docstring describing the experiment"
        )

    # Check 8: Parse parameters
    parameters = _parse_function_parameters(func_def)

    if not parameters:
        result["checks"].append(
            {
                "check": "has_typed_parameters",
                "passed": False,
                "message": "No typed parameters found",
            }
        )
        result["errors"].append(
            "Function must have at least one parameter with type annotation"
        )
        return result
    result["checks"].append(
        {
            "check": "has_typed_parameters",
            "passed": True,
            "message": f"Found {len(parameters)} typed parameter(s)",
        }
    )

    # Check 9: Parameters with Annotated ranges
    params_with_ranges = [p for p in parameters if p.range is not None]
    params_without_ranges = [
        p for p in parameters if p.range is None and p.type in ("int", "float")
    ]

    if params_with_ranges:
        result["checks"].append(
            {
                "check": "has_annotated_ranges",
                "passed": True,
                "message": f"{len(params_with_ranges)} parameter(s) have range constraints",
            }
        )
    else:
        result["checks"].append(
            {
                "check": "has_annotated_ranges",
                "passed": False,
                "message": "No parameters have Annotated range constraints",
            }
        )
        if params_without_ranges:
            result["warnings"].append(
                f"Numeric parameters without ranges: {[p.name for p in params_without_ranges]}. Consider using Annotated[type, (min, max)]"
            )

    # Check 10: Required vs optional parameters
    required_params = [p for p in parameters if p.required]
    optional_params = [p for p in parameters if not p.required]

    if required_params:
        result["checks"].append(
            {
                "check": "required_parameters",
                "passed": True,
                "message": f"{len(required_params)} required parameter(s)",
            }
        )
    if optional_params:
        result["checks"].append(
            {
                "check": "optional_parameters",
                "passed": True,
                "message": f"{len(optional_params)} optional parameter(s) with defaults",
            }
        )

    # Build schema
    description = func_doc.split("\n")[0] if func_doc else ""

    schema = {
        "name": func_def.name,
        "description": description,
        "module_path": str(script_path.resolve()),
        "parameters": [
            {
                "name": p.name,
                "type": p.type,
                "required": p.required,
                "default": p.default,
                "range": list(p.range) if p.range else None,
            }
            for p in parameters
        ],
    }

    result["schema"] = schema
    result["valid"] = True

    return result
