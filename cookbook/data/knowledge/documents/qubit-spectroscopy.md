# Qubit Spectroscopy

## Overview

Qubit spectroscopy is a fundamental calibration technique used to determine the transition frequency of a qubit. This is typically the first experiment run when bringing up a new qubit.

## Theory

The qubit transition frequency $f_{01}$ corresponds to the energy difference between the ground state $|0\rangle$ and the first excited state $|1\rangle$:

$$f_{01} = \frac{E_1 - E_0}{h}$$

For transmon qubits, this frequency is typically in the range of 4-6 GHz.

## Procedure

1. **Sweep Setup**: Configure a frequency sweep around the expected qubit frequency
2. **Drive Application**: Apply a microwave drive at each frequency point
3. **Readout**: Measure the qubit state after the drive pulse
4. **Analysis**: Identify the resonance peak in the measured signal

## Parameters

| Parameter | Typical Range | Description |
|-----------|---------------|-------------|
| `start` | 4.5 GHz | Start frequency of sweep |
| `stop` | 5.5 GHz | Stop frequency of sweep |
| `step` | 1-10 MHz | Frequency step size |
| `num_avs` | 100-10000 | Number of averages per point |
| `drive_amplitude` | 0.01-0.5 | Drive pulse amplitude |

## Best Practices

- Start with a wide frequency range and coarse step size
- Once the peak is located, narrow the range and decrease step size
- Increase averaging if the signal-to-noise ratio is poor
- The optimal drive amplitude depends on the qubit coherence

## Related Experiments

- [Rabi Oscillations](rabi-oscillations.md)
- [T1 Measurement](t1-measurement.md)
- [Ramsey Experiment](ramsey-experiment.md)
