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

"""Storage functions for QCA using HDF5 and SQLite."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

import h5py
import numpy as np

from .models import ExperimentResult


def _init_db(data_dir: Path) -> None:
    """Initialize SQLite database with schema if it doesn't exist.

    Args:
        data_dir: Root data directory
    """
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            target TEXT,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            params TEXT,
            results TEXT,
            notes TEXT,
            file_path TEXT NOT NULL
        )
    """
    )

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON experiments(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON experiments(timestamp)")

    conn.commit()
    conn.close()


def save_experiment(result: ExperimentResult, data_dir: Path) -> None:
    """Save experiment result to HDF5 file and update SQLite index.

    Args:
        result: Experiment result to save
        data_dir: Root data directory
    """
    # Parse timestamp to create directory structure
    dt = datetime.fromisoformat(result.timestamp.replace("Z", "+00:00"))

    # Create directory structure: data/experiments/YYYY/MM/DD/
    exp_dir = (
        data_dir
        / "experiments"
        / f"{dt.year:04d}"
        / f"{dt.month:02d}"
        / f"{dt.day:02d}"
    )
    exp_dir.mkdir(parents=True, exist_ok=True)

    # Create HDF5 file: HHMMSS_type.h5
    filename = f"{dt.hour:02d}{dt.minute:02d}{dt.second:02d}_{result.type}.h5"
    file_path = exp_dir / filename

    # Write HDF5 file
    with h5py.File(file_path, "w") as f:
        # Store metadata as attributes on root group
        f.attrs["id"] = result.id
        f.attrs["type"] = result.type
        f.attrs["timestamp"] = result.timestamp
        f.attrs["status"] = result.status
        f.attrs["target"] = result.target if result.target else ""
        f.attrs["params"] = json.dumps(result.params)
        f.attrs["results"] = json.dumps(result.results)
        f.attrs["notes"] = result.notes

        # Store arrays
        if result.arrays:
            arrays_group = f.create_group("arrays")
            for name, data in result.arrays.items():
                arrays_group.create_dataset(name, data=np.array(data))

        # Store plots
        if result.plots:
            plots_group = f.create_group("plots")
            for plot in result.plots:
                plot_name = plot["name"]
                plot_format = plot["format"]
                plot_data = plot["data"]

                # Convert data to bytes if needed
                if isinstance(plot_data, str):
                    # Base64 or JSON string
                    data_bytes = plot_data.encode("utf-8")
                elif isinstance(plot_data, dict):
                    # Plotly JSON
                    data_bytes = json.dumps(plot_data).encode("utf-8")
                else:
                    data_bytes = plot_data

                dataset = plots_group.create_dataset(
                    plot_name, data=np.frombuffer(data_bytes, dtype=np.uint8)
                )
                dataset.attrs["format"] = plot_format

    # Update SQLite index
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO experiments
        (id, type, target, timestamp, status, params, results, notes, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            result.id,
            result.type,
            result.target,
            result.timestamp,
            result.status,
            json.dumps(result.params),
            json.dumps(result.results),
            result.notes,
            str(file_path),
        ),
    )

    conn.commit()
    conn.close()


def load_experiment(experiment_id: str, data_dir: Path) -> Optional[ExperimentResult]:
    """Load experiment result from HDF5 file.

    Args:
        experiment_id: Experiment ID to load
        data_dir: Root data directory

    Returns:
        ExperimentResult if found, None otherwise
    """
    # Query SQLite for file path
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM experiments WHERE id = ?", (experiment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    file_path = Path(row[0])
    if not file_path.exists():
        return None

    # Read HDF5 file
    with h5py.File(file_path, "r") as f:
        # Read attributes
        exp_id = f.attrs["id"]
        exp_type = f.attrs["type"]
        timestamp = f.attrs["timestamp"]
        status = f.attrs["status"]
        target = f.attrs["target"] if f.attrs["target"] else None
        params = json.loads(f.attrs["params"])
        results = json.loads(f.attrs["results"])
        notes = f.attrs["notes"]

        # Read arrays
        arrays = {}
        if "arrays" in f:
            for name in f["arrays"].keys():
                arrays[name] = f["arrays"][name][:].tolist()

        # Read plots
        plots = []
        if "plots" in f:
            for name in f["plots"].keys():
                plot_data = f["plots"][name][:]
                plot_format = f["plots"][name].attrs["format"]

                # Convert bytes back to appropriate format
                data_bytes = plot_data.tobytes()
                if plot_format == "plotly":
                    data = json.loads(data_bytes.decode("utf-8"))
                else:
                    # Base64 or other format - keep as string
                    data = data_bytes.decode("utf-8")

                plots.append({"name": name, "format": plot_format, "data": data})

        return ExperimentResult(
            id=exp_id,
            type=exp_type,
            timestamp=timestamp,
            status=status,
            target=target,
            params=params,
            results=results,
            arrays=arrays,
            plots=plots,
            notes=notes,
            file_path=str(file_path),
        )


def search_experiments(
    data_dir: Path,
    type: Optional[str] = None,
    target: Optional[str] = None,
    last: Optional[int] = None,
) -> list[dict]:
    """Search experiments using SQLite index.

    Args:
        data_dir: Root data directory
        type: Filter by experiment type
        target: Filter by target
        last: Limit to last N experiments

    Returns:
        List of experiment metadata dictionaries
    """
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Build query
    query = "SELECT * FROM experiments WHERE 1=1"
    params = []

    if type:
        query += " AND type = ?"
        params.append(type)

    if target:
        query += " AND target = ?"
        params.append(target)

    query += " ORDER BY timestamp DESC"

    if last:
        query += " LIMIT ?"
        params.append(last)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Convert rows to dictionaries
    results = []
    for row in rows:
        results.append(
            {
                "id": row["id"],
                "type": row["type"],
                "target": row["target"],
                "timestamp": row["timestamp"],
                "status": row["status"],
                "params": json.loads(row["params"]) if row["params"] else {},
                "results": json.loads(row["results"]) if row["results"] else {},
                "notes": row["notes"],
                "file_path": row["file_path"],
            }
        )

    return results


def reindex(data_dir: Path) -> None:
    """Rebuild SQLite index from HDF5 files.

    Args:
        data_dir: Root data directory
    """
    _init_db(data_dir)
    db_path = data_dir / "index.db"

    # Clear existing index
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM experiments")
    conn.commit()
    conn.close()

    # Scan all HDF5 files
    exp_dir = data_dir / "experiments"
    if not exp_dir.exists():
        return

    for h5_file in exp_dir.rglob("*.h5"):
        try:
            with h5py.File(h5_file, "r") as f:
                # Read metadata
                exp_id = f.attrs["id"]
                exp_type = f.attrs["type"]
                timestamp = f.attrs["timestamp"]
                status = f.attrs["status"]
                target = f.attrs["target"] if f.attrs["target"] else None
                params = f.attrs["params"]
                results = f.attrs["results"]
                notes = f.attrs["notes"]

                # Insert into database
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO experiments
                    (id, type, target, timestamp, status, params, results, notes, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        exp_id,
                        exp_type,
                        target,
                        timestamp,
                        status,
                        params,
                        results,
                        notes,
                        str(h5_file),
                    ),
                )
                conn.commit()
                conn.close()
        except Exception:
            # Skip corrupted files
            continue


def delete_experiment(experiment_id: str, data_dir: Path) -> None:
    """Delete experiment HDF5 file and index entry.

    Args:
        experiment_id: Experiment ID to delete
        data_dir: Root data directory
    """
    # Query SQLite for file path
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM experiments WHERE id = ?", (experiment_id,))
    row = cursor.fetchone()

    if row:
        file_path = Path(row[0])

        # Delete HDF5 file
        if file_path.exists():
            file_path.unlink()

        # Delete index entry
        cursor.execute("DELETE FROM experiments WHERE id = ?", (experiment_id,))
        conn.commit()

    conn.close()


def list_arrays(experiment_id: str, data_dir: Path) -> Optional[list[dict]]:
    """List all arrays in an experiment's HDF5 file.

    Args:
        experiment_id: Experiment ID
        data_dir: Root data directory

    Returns:
        List of array metadata (name, shape, dtype) or None if experiment not found
    """
    # Query SQLite for file path
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM experiments WHERE id = ?", (experiment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    file_path = Path(row[0])
    if not file_path.exists():
        return None

    # Read HDF5 file
    arrays = []
    with h5py.File(file_path, "r") as f:
        if "arrays" in f:
            for name in f["arrays"].keys():
                dataset = f["arrays"][name]
                arrays.append(
                    {
                        "name": name,
                        "shape": list(dataset.shape),
                        "dtype": str(dataset.dtype),
                    }
                )

    return arrays


def get_array(
    experiment_id: str,
    array_name: str,
    data_dir: Path,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> Optional[list]:
    """Get array data with optional slicing.

    Args:
        experiment_id: Experiment ID
        array_name: Array name
        data_dir: Root data directory
        start: Start index for slicing (inclusive)
        end: End index for slicing (exclusive)

    Returns:
        Array data as list or None if not found
    """
    # Query SQLite for file path
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM experiments WHERE id = ?", (experiment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    file_path = Path(row[0])
    if not file_path.exists():
        return None

    # Read HDF5 file
    with h5py.File(file_path, "r") as f:
        if "arrays" not in f or array_name not in f["arrays"]:
            return None

        dataset = f["arrays"][array_name]

        # Apply slicing if specified
        if start is not None or end is not None:
            data = dataset[start:end]
        else:
            data = dataset[:]

        return data.tolist()


def get_array_stats(
    experiment_id: str, array_name: str, data_dir: Path
) -> Optional[dict]:
    """Get array statistics (min, max, mean, std).

    Args:
        experiment_id: Experiment ID
        array_name: Array name
        data_dir: Root data directory

    Returns:
        Dictionary with statistics or None if not found
    """
    # Query SQLite for file path
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM experiments WHERE id = ?", (experiment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    file_path = Path(row[0])
    if not file_path.exists():
        return None

    # Read HDF5 file
    with h5py.File(file_path, "r") as f:
        if "arrays" not in f or array_name not in f["arrays"]:
            return None

        data = f["arrays"][array_name][:]

        return {
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "mean": float(np.mean(data)),
            "std": float(np.std(data)),
            "count": int(len(data)),
        }


def list_plots(experiment_id: str, data_dir: Path) -> Optional[list[dict]]:
    """List all plots in an experiment.

    Args:
        experiment_id: Experiment ID
        data_dir: Root data directory

    Returns:
        List of plot metadata (name, format) or None if experiment not found
    """
    # Query SQLite for file path
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM experiments WHERE id = ?", (experiment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    file_path = Path(row[0])
    if not file_path.exists():
        return None

    # Read HDF5 file
    plots = []
    with h5py.File(file_path, "r") as f:
        if "plots" in f:
            for name in f["plots"].keys():
                plot_format = f["plots"][name].attrs["format"]
                plots.append({"name": name, "format": plot_format})

    return plots


def get_plot(experiment_id: str, plot_name: str, data_dir: Path) -> Optional[dict]:
    """Extract a plot (PNG or Plotly JSON).

    Args:
        experiment_id: Experiment ID
        plot_name: Plot name
        data_dir: Root data directory

    Returns:
        Dictionary with plot data and format or None if not found
    """
    # Query SQLite for file path
    _init_db(data_dir)
    db_path = data_dir / "index.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM experiments WHERE id = ?", (experiment_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    file_path = Path(row[0])
    if not file_path.exists():
        return None

    # Read HDF5 file
    with h5py.File(file_path, "r") as f:
        if "plots" not in f or plot_name not in f["plots"]:
            return None

        plot_data = f["plots"][plot_name][:]
        plot_format = f["plots"][plot_name].attrs["format"]

        # Convert bytes back to appropriate format
        data_bytes = plot_data.tobytes()
        if plot_format == "plotly":
            data = json.loads(data_bytes.decode("utf-8"))
        else:
            # Base64 or other format - keep as string
            data = data_bytes.decode("utf-8")

        return {"name": plot_name, "format": plot_format, "data": data}
