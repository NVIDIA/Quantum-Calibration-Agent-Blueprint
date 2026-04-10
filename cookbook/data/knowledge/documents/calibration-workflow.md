# Calibration Workflow

## Overview

This document describes the standard workflow for bringing up and calibrating a superconducting qubit.

## Calibration Sequence

### 1. Resonator Characterization
- Find readout resonator frequency
- Measure resonator linewidth (κ)
- Optimize readout power

### 2. Qubit Spectroscopy
- Locate qubit transition frequency
- Verify qubit is coupled to resonator
- Check for spurious modes

### 3. Pulse Calibration
- **Rabi oscillations**: Find π pulse amplitude
- **DRAG calibration**: Minimize leakage to |2⟩
- **Frequency calibration**: Correct for AC Stark shift

### 4. Coherence Measurements
- **T1**: Energy relaxation time
- **T2***: Ramsey dephasing time
- **T2 Echo**: Refocused dephasing time

### 5. Gate Calibration
- Single-qubit gate tomography
- Randomized benchmarking
- Gate set tomography (optional)

## Iteration

Calibration is iterative. Changes to one parameter may affect others:

```
Spectroscopy → Rabi → Coherence → ...
     ↑___________________________|
```

## Automation

The QCA agent can automate this workflow:

1. Analyze current calibration state
2. Recommend next experiment
3. Execute experiment
4. Update calibration parameters
5. Repeat until convergence

## Best Practices

- Always check coherence after major changes
- Log all calibration data for tracking drift
- Recalibrate after thermal cycles
- Monitor fridge temperature and pressure
