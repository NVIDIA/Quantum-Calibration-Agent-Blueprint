# Rabi Oscillations

## Overview

Rabi oscillations demonstrate the coherent rotation of a qubit state on the Bloch sphere. This experiment is used to calibrate the $\pi$ and $\pi/2$ pulse amplitudes.

## Theory

When a qubit is driven at its resonance frequency, the state oscillates between $|0\rangle$ and $|1\rangle$ at the Rabi frequency:

$$\Omega_R = \frac{d \cdot E_0}{\hbar}$$

where $d$ is the dipole moment and $E_0$ is the drive amplitude.

## Procedure

1. **Initialize**: Prepare the qubit in the ground state $|0\rangle$
2. **Drive**: Apply a microwave pulse with varying amplitude or duration
3. **Readout**: Measure the qubit population
4. **Fit**: Extract the Rabi frequency and optimal pulse parameters

## Types of Rabi Experiments

### Amplitude Rabi
- Fixed pulse duration
- Sweep drive amplitude
- Used to find $\pi$ pulse amplitude

### Time Rabi
- Fixed drive amplitude
- Sweep pulse duration
- Used to verify pulse calibration

## Parameters

| Parameter | Typical Range | Description |
|-----------|---------------|-------------|
| `drive_freq` | Qubit $f_{01}$ | Drive frequency (from spectroscopy) |
| `amp_start` | 0.0 | Starting amplitude |
| `amp_stop` | 1.0 | Maximum amplitude |
| `pulse_duration` | 20-100 ns | Fixed pulse length |
| `num_avs` | 500-5000 | Number of averages |

## Analysis

The measured data should show sinusoidal oscillations. Fit to:

$$P_1(A) = \frac{1}{2}(1 - \cos(\pi \cdot A / A_\pi))$$

where $A_\pi$ is the $\pi$ pulse amplitude.

## Related Experiments

- [Qubit Spectroscopy](qubit-spectroscopy.md)
- [DRAG Calibration](drag-calibration.md)
