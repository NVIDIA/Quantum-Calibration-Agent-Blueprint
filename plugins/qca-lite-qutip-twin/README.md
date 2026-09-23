# QCA Lite QuTiP twin plugin

This package provides the backend service used by the `lite_*` experiment adapters in the QCA
repository. It is installed separately so QuTiP and optional CUDA dependencies do not become QCA
core dependencies. The implementation is deliberately small: five runtime modules, a private QCA
HTTP adapter, and five discoverable experiment scripts. It does not patch QCA's TUI or core.

## Install and start

```bash
pip install -e plugins/qca-lite-qutip-twin
qca-lite-twin --data-layer auto --port 8090
```

For a CUDA installation, use `pip install -e 'plugins/qca-lite-qutip-twin[cuda]'`. The service
selects CUDA only after a real QuTiP/cuQuantum solver probe succeeds. `auto` records a CPU fallback
reason when that probe fails; explicit `--data-layer cuda` fails instead of silently using CPU.

## Provision hidden truth

Create one session before starting QCA. Seeded mode deterministically creates a hidden device:

```bash
curl -sS http://127.0.0.1:8090/sessions \
  -H 'content-type: application/json' \
  -d '{"truth_mode":"seeded","profile":"qca-lite-1q","seed":17}'
```

Explicit mode accepts the same physical fields documented by `model.validate_truth`; it is useful
for controlled fixtures. In both modes the service returns a `truth_digest`, never the truth
values, and truth is immutable for the lifetime of the session. Only public calibration config can
be patched.

Export the returned session ID and service URL in the shell that launches QCA:

```bash
export QCA_LITE_TWIN_URL=http://127.0.0.1:8090
export QCA_LITE_TWIN_SESSION_ID=<session-id>
qca experiments list --human
```

The intended calibration order is:

1. `lite_resonator_spectroscopy`
2. `lite_qubit_spectroscopy`
3. `lite_rabi_amplitude`
4. `lite_ramsey_frequency`
5. `lite_t1`

The first four apply passing fitted values to the same backend session. T1 is read-only. Every
result contains raw arrays, a Plotly plot, fit diagnostics, the public config version, and backend
provenance including the QuTiP data layer actually used.

## Focused verification

```bash
python -m pytest -q \
  plugins/qca-lite-qutip-twin/tests/test_lite_twin.py \
  plugins/qca-lite-qutip-twin/tests/test_qca_adapters.py
python -m pytest -q plugins/qca-lite-qutip-twin/tests/test_lite_twin_gpu.py -rs
```
