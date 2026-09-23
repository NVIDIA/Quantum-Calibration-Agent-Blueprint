# QCA Lite QuTiP twin validation record

**Validation date:** 2026-09-22 (America/Los_Angeles; artifact timestamps are UTC)

**Official QCA baseline:** `d8d37bc4de28d2347d8e21405903b29a2891f793`

## Scope

This record validates the standalone plugin and thin `scripts/lite_*` adapters against the native
QCA TUI and CLI from official GitHub `main`. No QCA core, TUI, runner, storage, or root packaging
file was changed.

## Environment

The host had only about 170 MiB free, so a conventional clean dependency install failed with
`ENOSPC`. Validation used a Python 3.12 virtual environment created with
`--system-site-packages`, then installed the official QCA checkout and plugin editable. The QCA
packages whose versions differed from the host were installed at the exact upstream pins,
including `deepagents==0.5.3` and `deepagents-cli==0.0.40`.

The plugin resolved these runtime versions:

- QuTiP 5.3.1
- qutip-cuQuantum 0.3.1
- cuQuantum 26.6.0
- NumPy 2.5.2

## Automated checks

- Five focused physics, truth, HTTP, validation, and CPU fail-closed checks passed.
- The upstream-adapter integration check ran all five calibrations against a live local HTTP
  service; all passed, generated plots, used QuTiP, and advanced public config from version 0 to
  version 5.
- The live CUDA test passed a real QuTiP/cuQuantum solver call and asserted CUDA provenance.
- All five scripts passed `qca experiments validate` and appeared in official QCA discovery.
- Seeded truth with seed 17 reproduced digest
  `sha256:27615315082e809cfeac0908b0c8b1aa37857cebb76eda91a78f860cdef31ac0`.
- Repeated explicit truth reproduced digest
  `sha256:77f6779a97eb9cdd562b8fcc7aef45315cc5c75380e2315ed713d1a1b94fda19`.
  Session descriptors exposed only those digests, not physical truth fields.

Targeted commands:

```bash
python -m pytest -q \
  plugins/qca-lite-qutip-twin/tests/test_lite_twin.py \
  plugins/qca-lite-qutip-twin/tests/test_qca_adapters.py
# 6 passed

python -m pytest -q plugins/qca-lite-qutip-twin/tests/test_lite_twin_gpu.py -rs
# 1 passed; a cuQuantum ExternalStream deprecation warning was emitted
```

## Official CLI workflow

A seeded CPU session was run through five separate `qca experiments run` commands. All five
results were successful and persisted with four arrays and one Plotly plot each:

- `20260923_062623_lite_resonator_spectroscopy`
- `20260923_062623_lite_qubit_spectroscopy`
- `20260923_062624_lite_rabi_amplitude`
- `20260923_062625_lite_ramsey_frequency`
- `20260923_062625_lite_t1`

The first four stages advanced config to version 5; T1 left it unchanged. Every result reported
`engine_used=qutip` and `data_layer_used=cpu`.

For GPU proof, an `auto` service selected CUDA after its real probe. Official
`qca experiments run lite_rabi_amplitude` completed successfully with nine sweep points, fitted a
pi amplitude of `0.10002287850715988`, applied X/X90 config, and persisted provenance containing
`engine_used=qutip` and `data_layer_used=cuda`.

## Native TUI workflow

The native QCA TUI was launched in existing Byobu pane `%404`, in the clean upstream-based
worktree, with a fresh seeded session. Official QCA's default
`nvidia/nemotron-3-nano-30b-a3b` endpoint had reached end of life, so the run used the currently
available `nvidia:nemotron-3-ultra-550b-a55b` through the existing authorized NVIDIA provider.
No source change was made for this substitution.

The TUI called its own lab tools and completed:

1. resonator spectroscopy — config version 1;
2. qubit spectroscopy — config version 2;
3. Rabi amplitude — config version 4;
4. Ramsey frequency — config version 5;
5. T1 — read-only at config version 5.

The five TUI artifacts are:

- `20260923_064106_lite_resonator_spectroscopy`
- `20260923_064111_lite_qubit_spectroscopy`
- `20260923_064122_lite_rabi_amplitude`
- `20260923_064136_lite_ramsey_frequency`
- `20260923_064150_lite_t1`

Every artifact has status `success`, four persisted arrays, one Plotly plot, QuTiP/CPU provenance,
and the same hidden-truth digest
`sha256:d3d7d6123eca84a25e0e0b95ef979d5b79d1f444eb3b990cfbe464778f7aad33`.
The TUI concluded with `CALIBRATION CHAIN COMPLETE — ALL EXPERIMENTS PASS`.

One upstream limitation was observed: `tools/lab_tool.py` uses its repository `data/` path
directly, rather than the CLI's `QCAL_DATA_DIR` helper. The artifacts therefore landed in ignored
local runtime storage even though an isolated data directory was exported. This did not require or
produce a source change.
