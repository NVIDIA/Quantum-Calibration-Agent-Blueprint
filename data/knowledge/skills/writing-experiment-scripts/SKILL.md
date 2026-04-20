---
name: writing-experiment-scripts
description: Author new experiment scripts that are compatible with the lab system's auto-discovery. Use when the user asks to create a new experiment type, add a custom measurement, or write a Python script that should be discoverable via the `lab` and `run_experiment` tools. Covers required function signatures, type hints, docstrings, and return formats.
---

# Writing Experiment Scripts

How to create experiment scripts compatible with the lab system.

## Quick Reference

| Requirement | Details |
|-------------|---------|
| Location | Scripts directory (see system prompt) |
| Function | ONE public function per file (no `_` prefix) |
| Type hints | Required with `Annotated` bounds |
| Docstring | Google-style with Args/Returns |
| Return | Dict with `status`, `results`, `arrays`, `plots` |

## Function Signature

```python
from typing import Annotated

def experiment_name(
    param1: Annotated[float, (min, max)] = default,
    param2: Annotated[int, (min, max)] = default,
    target: str = "qubit_0",
) -> dict:
    """Short description of the experiment.

    Args:
        param1: Description with units
        param2: Description with units
        target: Target qubit identifier

    Returns:
        Measurement results with data and plots
    """
    # Implementation
    return {...}
```

## Return Format

### Success
```python
{
    "status": "success",
    "results": {
        "peak_frequency": 5042.3,    # Scalar results
        "linewidth_mhz": 1.2,
    },
    "arrays": {
        "frequencies": [4900.0, 4902.0, ...],  # Array data
        "amplitudes": [0.01, 0.02, ...],
    },
    "plots": [
        {"name": "spectrum", "format": "png", "data": "base64..."},
    ],
    "metadata": {
        "target": "qubit_0",
        "experiment_type": "qubit_spectroscopy",
    },
}
```

### Failure
```python
{
    "status": "failed",
    "error": "No peak found in frequency range"
}
```

## Parameter Types

### Supported Types
- `float` - Floating point numbers
- `int` - Integers
- `str` - Strings (no range validation)
- `bool` - Boolean flags
- `list` - Lists (no range validation)

### Range Constraints
```python
from typing import Annotated

# Float with range [0.0, 100.0]
amplitude: Annotated[float, (0.0, 100.0)] = 50.0

# Int with range [1, 10000]
num_averages: Annotated[int, (1, 10000)] = 1000
```

**Important:** Parameters without defaults are required. Parameters with defaults are optional.

## Complete Example

```python
"""Simulated qubit spectroscopy experiment."""
from typing import Annotated
import numpy as np
import base64
import io


def qubit_spectroscopy(
    start: Annotated[float, (3000.0, 8000.0)] = 4900.0,
    stop: Annotated[float, (3000.0, 8000.0)] = 5100.0,
    step: Annotated[float, (0.1, 100.0)] = 2.0,
    num_avs: Annotated[int, (1, 10000)] = 1000,
    target: str = "qubit_0",
) -> dict:
    """Qubit spectroscopy frequency sweep.

    Performs a frequency sweep to find the qubit resonance frequency.

    Args:
        start: Start frequency in MHz
        stop: Stop frequency in MHz
        step: Frequency step in MHz
        num_avs: Number of averages
        target: Target qubit identifier

    Returns:
        Measurement results with frequency estimate and data
    """
    # Generate frequency array
    frequencies = np.arange(start, stop + step, step)

    # Simulate measurement (replace with real hardware calls)
    center_freq = (start + stop) / 2
    linewidth = 3.0
    signal = 1.0 / (1.0 + ((frequencies - center_freq) / linewidth) ** 2)
    noise = np.random.normal(0, 0.05, len(frequencies))
    magnitude = signal + noise

    # Find peak
    peak_idx = np.argmax(magnitude)
    frequency_guess = float(frequencies[peak_idx])

    # Generate plot (optional)
    plots = []
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(frequencies, magnitude, 'b-')
        ax.axvline(frequency_guess, color='r', linestyle='--')
        ax.set_xlabel('Frequency (MHz)')
        ax.set_ylabel('Magnitude')
        ax.set_title(f'Spectroscopy - {target}')

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plots.append({
            "name": "spectroscopy",
            "format": "png",
            "data": base64.b64encode(buf.read()).decode('ascii')
        })
        plt.close(fig)
    except ImportError:
        pass

    return {
        "status": "success",
        "results": {
            "frequency_guess": frequency_guess,
            "linewidth_mhz": linewidth,
        },
        "arrays": {
            "frequencies": frequencies.tolist(),
            "magnitude": magnitude.tolist(),
        },
        "plots": plots,
        "metadata": {
            "target": target,
            "experiment_type": "qubit_spectroscopy",
        },
    }
```

## Common Patterns

### Sweep Experiment
```python
def frequency_sweep(
    start: Annotated[float, (1000.0, 10000.0)] = 4000.0,
    stop: Annotated[float, (1000.0, 10000.0)] = 6000.0,
    step: Annotated[float, (0.1, 100.0)] = 1.0,
) -> dict:
```

### Time-Domain Measurement
```python
def t1_measurement(
    delay_start: Annotated[float, (0.0, 1000.0)] = 0.0,
    delay_stop: Annotated[float, (0.0, 1000.0)] = 100.0,
    num_points: Annotated[int, (10, 500)] = 50,
    num_averages: Annotated[int, (100, 50000)] = 1000,
) -> dict:
```

### Amplitude Calibration
```python
def rabi_amplitude(
    amp_start: Annotated[float, (0.0, 1.0)] = 0.0,
    amp_stop: Annotated[float, (0.0, 1.0)] = 1.0,
    num_points: Annotated[int, (10, 200)] = 50,
    drive_frequency: Annotated[float, (3000.0, 8000.0)] = 5000.0,
) -> dict:
```

## Validation

After creating or modifying an experiment script, **always validate it** using the CLI tool:

```bash
qca experiments validate <path-to-script> --human
```

This command checks:
- File exists and is a valid Python file
- Contains a public function (no underscore prefix)
- Function has `-> dict` return type annotation
- Parameters have type hints (ideally with `Annotated` ranges)
- Syntax is valid

**Example output (valid script):**
```
Validation Result: VALID
File: scripts/my_experiment.py

┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check                  ┃ Status   ┃ Details                                 ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ file_exists            │ ✓ PASS   │ File exists                             │
│ python_file            │ ✓ PASS   │ File has .py extension                  │
│ not_private            │ ✓ PASS   │ File is public (no underscore prefix)   │
│ syntax_valid           │ ✓ PASS   │ Python syntax is valid                  │
│ has_public_function    │ ✓ PASS   │ Found public function: my_experiment    │
│ return_type_dict       │ ✓ PASS   │ Return type is dict                     │
│ has_docstring          │ ✓ PASS   │ Function has docstring                  │
│ has_typed_parameters   │ ✓ PASS   │ Found 3 typed parameter(s)              │
│ has_annotated_ranges   │ ✓ PASS   │ 3 parameter(s) have range constraints   │
│ optional_parameters    │ ✓ PASS   │ 3 optional parameter(s) with defaults   │
└────────────────────────┴──────────┴─────────────────────────────────────────┘

Experiment Schema:
  Name: my_experiment
  Description: My experiment description.
  Module Path: /path/to/scripts/my_experiment.py

Parameters:
┏━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Name          ┃ Type  ┃ Required ┃ Default ┃ Range        ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ amplitude     │ float │ No       │ 0.5     │ 0.0 to 1.0   │
│ num_points    │ int   │ No       │ 51      │ 10 to 200    │
│ target        │ str   │ No       │ qubit_0 │ -            │
└───────────────┴───────┴──────────┴─────────┴──────────────┘
```

**Example output (invalid script):**
```
Validation Result: INVALID
File: scripts/bad_experiment.py

┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Check                  ┃ Status   ┃ Details                         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ file_exists            │ ✓ PASS   │ File exists                     │
│ python_file            │ ✓ PASS   │ File has .py extension          │
│ not_private            │ ✓ PASS   │ File is public                  │
│ syntax_valid           │ ✓ PASS   │ Python syntax is valid          │
│ has_public_function    │ ✓ PASS   │ Found public function: my_func  │
│ return_type_dict       │ ✗ FAIL   │ No return type annotation       │
└────────────────────────┴──────────┴─────────────────────────────────┘

Errors:
  • Function must have return type annotation '-> dict'
```

After validation passes, verify the experiment appears in the list:
```bash
qca experiments list --human
```

## Checklist

Before running your script:

- [ ] File is in the scripts directory
- [ ] Only ONE public function (no `_` prefix)
- [ ] All parameters have type hints with `Annotated`
- [ ] All parameters have default values (or are intentionally required)
- [ ] Function has Google-style docstring
- [ ] Returns dict with `status` key
- [ ] Arrays are converted to lists (`.tolist()`)
- [ ] Plots are base64-encoded PNG or Plotly JSON
- [ ] **Run `qca experiments validate <path> --human` to verify**
- [ ] **Run `qca experiments list --human` to confirm discovery**
