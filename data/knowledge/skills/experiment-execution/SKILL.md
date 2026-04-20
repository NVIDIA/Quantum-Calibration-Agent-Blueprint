---
name: experiment-execution
description: Reference guide for running individual quantum calibration experiments and interpreting their results. Use when the user asks to run a single experiment (e.g. resonator spectroscopy, qubit spectroscopy, T1, T2), inspect experiment plots with the VLM, or query experiment history and schemas via the lab tool.
---

# Experiment Execution Guide

Reference guide for running and analyzing quantum calibration experiments.

## Tools Available

### run_experiment
Execute a quantum calibration experiment.
```python
run_experiment(
    experiment_name="resonator_spectroscopy",
    params={
        "center_freq": 6.0,
        "span": 0.2,
        "num_points": 101,
        "power": -20,
        "num_averages": 2000
    }
)
```
Returns: `{"id": "...", "status": "success", "results": {...}, "plots": [...]}`

### vlm_inspect
AI-powered visual analysis of experiment plots.
```python
vlm_inspect(
    experiment_id="20240315_103015_resonator",
    prompt="Is there a clear dip? What is the resonator frequency and estimated SNR?"
)
```
Returns: Text analysis of the plot.

### lab
Query experiment information and history.
```python
lab(action="schema", experiment_name="resonator_spectroscopy")  # Get parameter schema
lab(action="history_show", experiment_id="...")                  # Get experiment details
lab(action="get_stats", experiment_id="...", array_name="...")  # Get array statistics
```

## ⚠️ Data Analysis Rules

**NEVER copy raw experiment arrays into shell commands.** Large arrays will be truncated and cause syntax errors.

**DO use these approaches:**
1. **VLM analysis**: `vlm_inspect(experiment_id=..., prompt="...")` - visual plot analysis
2. **Returned scalars**: `run_experiment` returns fitted values like `resonator_freq`, `t2_star`, etc.
3. **Lab stats**: `lab(action="get_stats", experiment_id=..., array_name="...")` for array statistics

**DON'T do this:**
```python
# BAD - will fail with syntax errors
execute("python3 -c 'data = [0.1, 0.2, 0.3, ...]'")  # Arrays too long!
```

## Standard Execution Flow

1. **Run experiment** with appropriate parameters
2. **Get experiment_id** from result
3. **Display results** - ALWAYS include this tag in your response:
   `<experiment experiment-id="THE_EXPERIMENT_ID" />`
   (Replace THE_EXPERIMENT_ID with the actual ID. This shows the interactive viewer with plots.)
4. **Analyze plots** with vlm_inspect - ask about peaks, dips, resonances, SNR
5. **Extract values** from VLM analysis (frequency, linewidth, SNR)
6. **Verify success criteria** if defined
7. **If failed, adjust and retry** (up to max attempts)

## Verifying Success Criteria

After running an experiment, verify results against success criteria when applicable.

### When to Verify
- **DO verify** when success criteria are defined in the workflow plan
- **DO verify** when numeric thresholds need checking (SNR, linewidth, depth, etc.)
- **SKIP verification** if user has already seen the plot and confirmed success
- **SKIP verification** if no specific success criteria were provided

### Verification Methods

**Visual (VLM):** Use `vlm_inspect` to analyze plots
- Ask specific questions matching the criteria
- Example: "Is there a single clear peak? What is the SNR? Is it greater than 5?"
- Example: "Is there a visible dip with depth > 3 dB?"

**Programmatic:** Check returned data values directly
- Extract values from experiment results (e.g., `snr`, `peak_frequency`, `linewidth`)
- Compare against thresholds in success criteria

## Typical Parameter Ranges

| Experiment | Parameter | Typical Range |
|------------|-----------|---------------|
| qubit_spectroscopy | start/stop | 4500-5500 MHz |
| qubit_spectroscopy | step | 0.5-10 MHz |
| qubit_spectroscopy | num_avs | 500-5000 |
| resonator_spectroscopy | start/stop | 6000-8000 MHz |
| resonator_spectroscopy | step | 0.1-1 MHz |

## Success/Failure Indicators

### Good Data (Success)
- Clear single peak or dip visible
- SNR >= 5 (ideally >= 8)
- Peak width reasonable (5-50 MHz for qubit)
- Smooth baseline, low noise

### Bad Data (Retry Needed)
- No visible peak/dip
- Multiple peaks (ambiguous)
- SNR < 3
- High noise floor
- Saturation or clipping

## Retry Strategies

If experiment fails, try these adjustments:

1. **No peak found**: Expand frequency range (1.5x wider)
2. **Low SNR**: Increase num_avs (2x more averaging)
3. **Multiple peaks**: Narrow range around strongest peak
4. **High noise**: Increase num_avs, check for interference

## Example Execution

```
Task: Run resonator spectroscopy centered at 6.0 GHz

Attempt 1:
> run_experiment(experiment_name="resonator_spectroscopy",
                 params={"center_freq": 6.0, "span": 0.2, "num_points": 101, "num_averages": 2000})
> Result: experiment_id = "20240315_103015_resonator"
> Include in response: <experiment experiment-id="20240315_103015_resonator" />
> vlm_inspect(experiment_id="20240315_103015_resonator",
              prompt="Is there a clear dip? What is the frequency and SNR?")
> VLM: "Clear dip visible at 5.823 GHz. Estimated SNR ~12. Clean baseline."

Success! Extracted: resonator_frequency = 5.823 GHz
```
