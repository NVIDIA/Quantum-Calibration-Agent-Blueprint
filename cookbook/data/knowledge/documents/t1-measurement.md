# T1 Measurement

## Overview

The T1 measurement determines the energy relaxation time of a qubit - how long the qubit can remain in the excited state before decaying to the ground state.

## Theory

After being excited to $|1\rangle$, the qubit population decays exponentially:

$$P_1(t) = e^{-t/T_1}$$

T1 sets a fundamental limit on qubit coherence and gate fidelity.

## Procedure

1. **Excite**: Apply a $\pi$ pulse to prepare $|1\rangle$
2. **Wait**: Variable delay time $t$
3. **Readout**: Measure the remaining excited state population
4. **Fit**: Extract T1 from exponential decay

## Parameters

| Parameter | Typical Range | Description |
|-----------|---------------|-------------|
| `delay_start` | 0 ns | Minimum delay |
| `delay_stop` | 5×T1 (expected) | Maximum delay |
| `num_points` | 50-200 | Number of delay points |
| `num_avs` | 1000-10000 | Averages per point |

## Typical Values

| Qubit Type | Typical T1 |
|------------|------------|
| Transmon (2D) | 20-100 μs |
| Transmon (3D) | 100-500 μs |
| Fluxonium | 100 μs - 1 ms |

## Factors Affecting T1

- **Purcell decay**: Coupling to readout resonator
- **Dielectric loss**: Substrate and interface losses
- **Quasiparticle tunneling**: Non-equilibrium quasiparticles
- **Radiation**: Infrared photons from warmer stages

## Related Experiments

- [T2 Ramsey](ramsey-experiment.md)
- [T2 Echo](echo-experiment.md)
