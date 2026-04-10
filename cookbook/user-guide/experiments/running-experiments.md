# Running Experiments

This guide covers how to run experiments in QCA using both the CLI and agent tools.

```{figure} /_static/images/usage/experiment-details.png
:alt: Experiments Dashboard
:width: 100%

The Experiments Dashboard showing experiment history and results.
```

## Using the CLI

The `qca experiments` commands provide direct access to the experiment system.

### Listing Available Experiments

```bash
qca experiments list
```

Example output:
```
Available experiments:
  qubit_spectroscopy
    Perform qubit spectroscopy measurement.
    Parameters: center_freq, span, num_points, drive_amplitude, num_averages

  rabi_amplitude
    Perform Rabi amplitude sweep.
    Parameters: frequency, min_amp, max_amp, num_points, averages
```

### Viewing Experiment Schema

Before running an experiment, check its parameters:

```bash
qca experiments schema qubit_spectroscopy
```

Example output:
```json
{
  "name": "qubit_spectroscopy",
  "description": "Perform qubit spectroscopy measurement.",
  "parameters": [
    {
      "name": "center_freq",
      "type": "float",
      "required": false,
      "default": 4.8,
      "range": [4.0, 5.5]
    },
    {
      "name": "span",
      "type": "float",
      "required": false,
      "default": 0.2,
      "range": [0.05, 0.5]
    },
    {
      "name": "num_points",
      "type": "int",
      "required": false,
      "default": 101,
      "range": [51, 201]
    }
  ]
}
```

Key information:
- **name**: Function name in the script
- **type**: Parameter type (int, float, str, bool, list)
- **required**: Whether the parameter must be provided
- **default**: Default value if not provided
- **range**: Valid range for numeric parameters (from `Annotated` hints)

### Running an Experiment

```bash
qca experiments run <experiment-name> [--param key=value]
```

Examples:

**Using defaults:**
```bash
qca experiments run qubit_spectroscopy
```

**Overriding parameters:**
```bash
qca experiments run qubit_spectroscopy \
  --param center_freq=4.85 \
  --param span=0.3 \
  --param num_points=151
```

**All parameters specified:**
```bash
qca experiments run qubit_spectroscopy \
  --param center_freq=4.9 \
  --param span=0.2 \
  --param num_points=101 \
  --param drive_amplitude=0.15 \
  --param num_averages=10000
```

### Parameter Format

Parameters are specified as `--param key=value` where:
- **Integers**: `--param num_points=101`
- **Floats**: `--param center_freq=4.85`
- **Strings**: `--param target=qubit_0`
- **Booleans**: `--param verbose=true` or `--param verbose=false`
- **Lists**: `--param amplitudes=[0.1,0.2,0.3]`

### Parameter Validation

QCA validates parameters before execution:

**Type checking:**
```bash
# Error: center_freq must be float
qca experiments run qubit_spectroscopy --param center_freq="4.85"
```

**Range validation:**
```bash
# Error: center_freq out of range [4.0, 5.5]
qca experiments run qubit_spectroscopy --param center_freq=6.0
```

**Required parameters:**
```bash
# Error: Missing required parameter
qca experiments run some_experiment
```

If validation fails, you'll see a clear error message indicating what needs to be fixed.

### Understanding Results

When an experiment completes, you'll see:

```
Experiment completed successfully
ID: exp_20260323_143052_qubit_spectroscopy
Status: success
Results:
  qubit_freq: 4.8500 GHz
  snr: 42.3
Data saved to: data/experiments/2026/03/23/143052_qubit_spectroscopy.h5
```

Key fields:
- **ID**: Unique identifier for querying later
- **Status**: `success` or `failed`
- **Results**: Scalar values extracted from the data
- **File path**: Location of HDF5 file with full data

### Viewing Experiment Output

Experiments can produce detailed progress output on stderr:

```
===========================================================
QUBIT SPECTROSCOPY - Starting measurement
===========================================================
  Center frequency: 4.8000 GHz
  Span: 0.200 GHz
  Number of points: 101
  Drive amplitude: 0.100
  Averages: 5000
-----------------------------------------------------------
  Estimated execution time: 45.0 seconds
-----------------------------------------------------------
  [14:30:52] Initializing qubit control...
  [14:30:53] Calibrating readout...
  [14:30:54] Configuring pulse sequence...
  [14:30:54] Acquiring data...
      Progress: 20% (1000/5000 averages)
      Progress: 40% (2000/5000 averages)
      ...
  [14:31:15] Analyzing spectrum...
-----------------------------------------------------------
  Qubit frequency: 4.850000 GHz
  Peak population: 0.785
  SNR: 42.3
  Qubit in search range: True
===========================================================
QUBIT SPECTROSCOPY - Complete
===========================================================
```

## Using the lab Tool (Agent Mode)

When working in agent mode (`qca` TUI or `qca -n "prompt"`), the agent uses the `lab` tool to run experiments.

### Available Actions

The lab tool provides these actions:
- `list` - List available experiments
- `schema` - Get experiment schema
- `run_experiment` - Execute an experiment
- `history_list` - List past experiments
- `history_show` - Show experiment details
- `list_arrays` - List arrays in an experiment
- `get_array` - Retrieve array data
- `get_stats` - Get array statistics

### Example Agent Workflow

**User prompt:**
```
"Run a qubit spectroscopy sweep from 4.7 to 5.0 GHz with 151 points"
```

**Agent reasoning:**
1. Use `lab.list` to discover available experiments
2. Use `lab.schema` to get parameter schema for `qubit_spectroscopy`
3. Calculate parameters: `center_freq=4.85`, `span=0.3`, `num_points=151`
4. Use `lab.run_experiment` to execute
5. Report results to user

**Agent response:**
```
I've completed the qubit spectroscopy measurement. Here are the results:

- Qubit frequency: 4.852 GHz
- Signal-to-noise ratio: 38.5
- Peak population: 0.78

The qubit resonance was found at 4.852 GHz with a strong signal.
The full data has been saved with ID: exp_20260323_143052_qubit_spectroscopy
```

### Accessing Results via Agent

The agent can query stored data:

**User:** "What was the SNR from the last experiment?"

**Agent uses:** `lab.history_list` to find recent experiments, then `lab.history_show` to get details.

**User:** "Show me the frequency sweep data"

**Agent uses:** `lab.list_arrays` to find arrays, then `lab.get_array` to retrieve `frequencies` and `excited_population` arrays.

## Viewing Plots

Experiments can include plot data in their results. Plots are stored in the HDF5 file.

### Plot Formats

QCA supports two plot formats:
- **plotly**: Interactive Plotly JSON (recommended)
- **png**: Base64-encoded PNG images

### Accessing Plots via CLI

```bash
# List plots in an experiment
qca data plots <experiment-id>

# Extract a specific plot
qca data plot <experiment-id> <plot-name>
```

For Plotly plots, the JSON can be rendered in a Jupyter notebook:

```python
import json
import plotly.graph_objects as go

# Get plot data
plot_data = ...  # from qca data plot command

# Render
fig = go.Figure(plot_data)
fig.show()
```

### Accessing Plots via Agent

The agent can retrieve plot data using:

```python
lab.get_plot(experiment_id="exp_...", plot_name="Qubit spectroscopy response")
```

For Plotly plots, the agent receives the full JSON and can describe trends or extract specific values.

## Tips and Best Practices

### Timeout Handling

Long experiments may exceed the default 300s timeout:

```bash
# Not directly configurable via CLI, but can be set in .env
QCAL_TIMEOUT=600  # 10 minutes
```

Or modify the runner directly for one-off cases.

### Parameter Exploration

Use the schema to understand valid ranges:

```bash
qca experiments schema <experiment-name> | jq '.parameters[] | {name, type, range, default}'
```

### Experiment Discovery

Experiments are discovered from:
- `scripts/` directory by default
- `$QCAL_SCRIPTS_DIR` if set in environment

Add new experiments by creating Python files in this directory. See [Writing Scripts](writing-scripts.md).

### Validation Before Running

Validate a script before adding it to the scripts directory:

```bash
qca experiments validate path/to/my_experiment.py
```

This checks:
- Python syntax
- Function signature (must return `-> dict`)
- Type annotations
- Parameter structure
- Docstring presence

## Error Handling

### Common Errors

**Experiment not found:**
```
Error: Experiment not found: qubit_spec
```
Solution: Check spelling, run `qca experiments list` to see available names.

**Parameter validation failed:**
```
Error: Parameter validation failed: Parameter center_freq out of range.
Expected [4.0, 5.5], got 6.0
```
Solution: Adjust parameter to be within the valid range.

**Subprocess failed:**
```
Error: Experiment subprocess failed: ModuleNotFoundError: No module named 'numpy'
```
Solution: Install missing dependencies in the Python environment.

**Timeout:**
```
Error: Experiment timed out after 300 seconds
```
Solution: Increase timeout or optimize experiment code.

### Debugging Failed Experiments

Check the experiment history for details:

```bash
qca history show <experiment-id>
```

Failed experiments include an `error` field with the traceback.

## Next Steps

- **[Writing Scripts](writing-scripts.md)** - Create custom experiments
- **[Experiment Storage](experiment-storage.md)** - Deep dive into HDF5/SQLite storage
