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

"""Data models for QCA."""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class ParameterSpec:
    """Specification for an experiment parameter.

    Attributes:
        name: Parameter name
        type: Parameter type (int, float, str, bool, list)
        default: Default value (None if required)
        range: Tuple of (min, max) for numeric types
        required: Whether parameter is required
    """

    name: str
    type: str
    default: Optional[Any] = None
    range: Optional[tuple[float, float]] = None
    required: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ParameterSpec":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ExperimentSchema:
    """Schema for an experiment.

    Attributes:
        name: Experiment name
        description: Description from docstring
        parameters: List of parameter specifications
        module_path: Path to the module file
    """

    name: str
    description: str
    parameters: list[ParameterSpec]
    module_path: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [p.to_dict() for p in self.parameters],
            "module_path": self.module_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentSchema":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            parameters=[ParameterSpec.from_dict(p) for p in data["parameters"]],
            module_path=data["module_path"],
        )


@dataclass
class ExperimentResult:
    """Result of an experiment execution.

    Attributes:
        id: Experiment ID (YYYYMMDD_HHMMSS_type)
        type: Experiment type (function name)
        timestamp: ISO 8601 timestamp (UTC)
        status: Status (success or failed)
        target: Target from params (e.g., qubit_0)
        params: Input parameters (dict)
        results: Result scalars (dict)
        arrays: Result arrays (dict of lists/arrays)
        plots: Plot data (list of {name, format, data})
        notes: User notes
        file_path: Path to HDF5 file
    """

    id: str
    type: str
    timestamp: str
    status: str
    target: Optional[str] = None
    params: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    arrays: dict[str, Any] = field(default_factory=dict)
    plots: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    file_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentResult":
        """Create from dictionary."""
        return cls(**data)
