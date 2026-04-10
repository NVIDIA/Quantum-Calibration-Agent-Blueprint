# Quantum Calibration Agent — Tutorial

This guide walks you through five paths — from installation to a full automated calibration workflow. Each path builds on the previous one, so start from the top if this is your first time.

---

## What the Agent Can Do

| Capability | Description |
|---|---|
| **Experiment discovery** | Browse available experiments and inspect every parameter — name, type, valid range, and units — without touching a script |
| **Natural-language execution** | Describe your intent; the agent selects the right experiment, validates parameters against defined ranges, and rejects invalid values before running |
| **Intelligent result analysis** | A reasoning agent reads numerical outputs; a vision-language model reads the plots — you get a physics-level explanation, not a data dump |
| **Workflow orchestration** | Describe a calibration sequence in plain English; the agent builds a dependency graph (DAG), runs each step, and passes outputs between experiments automatically |
| **Persistent knowledge base** | The agent loads calibration notes, domain knowledge, and reusable analysis scripts from `cookbook/data/knowledge/` and references them across sessions |
| **Custom experiment integration** | Drop any Python script following the interface pattern into `scripts/` — the agent discovers it automatically, no configuration required |

### Agent Tools

The agent has five tools it can call during a conversation:

| Tool | Purpose |
|---|---|
| `lab` | Query experiment info, schemas, history, and stored data |
| `run_experiment` | Execute a calibration experiment with validated parameters |
| `vlm_inspect` | Send experiment plots to a Vision Language Model for visual analysis |
| `workflow` | List, validate, and inspect multi-step calibration workflows |
| `find` | Search for files and directories in the project |

---

## Path 1 — Install & Configure

Get QCA running on your machine with a working LLM backend.

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm 9+ (for web UI only)

### Install

```bash
git clone <repo-url>
cd qca
python -m venv .venv
source .venv/bin/activate
pip install -e .
qca --version   # verify
```

### Configure the LLM

Create a `.env` file in the project root. Pick one provider:

**NVIDIA NIM (cloud)**
```bash
QCA_MODEL=nvidia:nvidia/nemotron-3-nano-30b-a3b
NVIDIA_API_KEY=nvapi-...
```

**Anthropic**
```bash
QCA_MODEL=anthropic:claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...
```

**OpenAI**
```bash
QCA_MODEL=openai:gpt-4o
OPENAI_API_KEY=sk-...
```

**Local vLLM** (e.g., Qwen 3.5 fine-tune)
```bash
QCA_MODEL=openai:<full-model-path>
OPENAI_BASE_URL=http://localhost:18006/v1
OPENAI_API_KEY=dummy
```

> **vLLM requirement:** The server must be launched with `--enable-auto-tool-choice --tool-call-parser qwen3_coder` for tool calling to work. See [vLLM setup guide](vllm-local-model-setup.md) for full details.

### Point to Your Experiments

By default the agent discovers scripts in `scripts/`. Override with:

```bash
export QCAL_SCRIPTS_DIR=/path/to/your/scripts
```

### Launch

| Interface | Command |
|-----------|---------|
| Interactive TUI | `qca` |
| Single prompt | `qca -n "your prompt"` |
| Resume session | `qca -r <thread-id>` |
| Web UI backend | `qca serve` |
| Web UI frontend | `cd ui && npm install && npm run dev` |

The web UI runs on **http://localhost:3000** (gateway proxy). The backend API runs on port 8000.

### Verify

```
qca -n "What experiments can I run?"
```

If you see a list of experiments, everything is working. Continue to Path 2.

---

## Path 2 — Discover & Run Your First Experiment

This path takes you from browsing the experiment catalogue to running a measurement and seeing results — all through natural language.

### Step 1 — List available experiments

```
What experiments can I run?
```

The agent calls `lab` with action `info`, which AST-parses every Python script in `scripts/` without executing any code. On a fresh install it finds:

| Experiment | Script | What it measures |
|---|---|---|
| `qubit_spectroscopy` | `qubit_spectroscopy.py` | Qubit transition frequency |
| `rabi_oscillation` | `rabi_oscillation.py` | Pi-pulse amplitude calibration |
| `ramsey_measurement` | `ramsey_measurement.py` | T2* dephasing time |
| `resonator_spectroscopy` | `resonator_spectroscopy.py` | Readout resonator frequency |
| `t1_measurement` | `t1_measurement.py` | T1 energy relaxation time |

> **Adding your own:** Create a Python file in `scripts/` whose public function uses `Annotated` type hints for parameter ranges and returns a dict with `status`, `data`, and `plots` keys. The agent discovers it automatically on the next query.

### Step 2 — Inspect parameters

```
What parameters does qubit spectroscopy take?
```

The agent calls `lab` with action `schema` for `qubit_spectroscopy` and returns:

| Parameter | Range | Default | Unit |
|---|---|---|---|
| `center_freq` | 4.0 – 5.5 | 4.8 | GHz |
| `span` | 0.05 – 0.5 | 0.2 | GHz |
| `num_points` | 51 – 201 | 101 | — |
| `drive_amplitude` | 0.01 – 1.0 | 0.1 | a.u. |
| `num_averages` | 500 – 20,000 | 5,000 | — |

All ranges come from the `Annotated` type hints in the script. The agent will reject values outside these bounds before execution.

### Step 3 — Run an experiment

```
Run qubit spectroscopy with center_freq=4.85 and span=0.5.
```

The agent calls `run_experiment` for `qubit_spectroscopy` with your parameters. The bundled simulation has a true qubit frequency of 4.85 GHz, so sweeping 4.6–5.1 GHz puts the resonance peak in range. The agent returns:

- `qubit_freq` — fitted transition frequency (GHz)
- `linewidth` and `snr` — measurement quality metrics
- An interactive Plotly chart rendered inline

> **Tip:** The default `center_freq=4.8` with `span=0.2` already covers the true frequency. Widening the span as above just makes the peak more dramatic.

---

## Path 3 — Analyze Results

Continue from the experiment you just ran. This path shows how the agent interprets data — both visually and numerically — and chains experiments together.

### Step 1 — Visual plot inspection

```
Look at the spectroscopy plot and tell me what you see.
```

The agent calls `vlm_inspect` with the experiment ID from the previous run. The Vision Language Model reads the rendered plot and gives a qualitative assessment: whether a clear peak is visible above the noise floor, how sharp the resonance is, and whether the baseline looks clean. This is distinct from the fitted numbers — the VLM interprets visual structure.

> **Requires:** A VLM provider configured in `config.yaml` under the `vlm` section (default: NVIDIA Nemotron Super 49B).

### Step 2 — Numerical analysis

```
Analyze the last experiment — what did it tell us about the qubit?
```

The agent retrieves the completed experiment from session history and reads the numerical outputs. It explains what the fitted frequency means, whether the SNR is sufficient to trust the fit, and what the result implies for the next calibration step.

### Step 3 — Chain to the next experiment

```
Run a Rabi oscillation using the qubit frequency we just found.
```

The agent reads `qubit_freq` from the spectroscopy result in conversation history and passes it to the next experiment. The `rabi_oscillation` script sweeps drive amplitude to calibrate the pi-pulse and returns:

| Output | Description |
|---|---|
| `pi_amplitude` | Calibrated pi-pulse amplitude |
| `amplitudes` | Array of drive amplitudes swept |
| `excited_population` | Measured population vs. amplitude |

The same chaining pattern works for any two experiments where one produces an output the other accepts as input — just describe the intent.

---

## Path 4 — Use the Knowledge Base

The agent loads documents from `cookbook/data/knowledge/` at the start of every session. This path shows how to leverage stored knowledge and save new findings.

### How knowledge is organized

```
cookbook/data/knowledge/
├── documents/     # Calibration notes, device specs, physics references
├── skills/        # Reusable analysis scripts and execution guides
├── memory/        # Workflow preferences and agent behavior notes
└── system-prompt.md  # Agent personality and behavior configuration
```

The agent automatically references these files when answering questions or planning experiments. No explicit "search" is needed.

### Step 1 — Ask a domain question

```
What is a Rabi oscillation and why do we measure it?
```

The agent draws on both its training knowledge and the documents in `cookbook/data/knowledge/documents/` (e.g., `rabi-oscillations.md`). It explains that Rabi oscillations are driven transitions between qubit states, and that measuring them calibrates the pulse amplitude for pi and pi/2 rotations.

### Step 2 — Save a finding

```
Save what we learned about this qubit's pi-pulse amplitude so we can reference it later.
```

The agent writes a structured note to `cookbook/data/knowledge/memory/` linking the pi-amplitude value to the experiment that produced it. This persists across sessions.

### Step 3 — Retrieve stored knowledge

```
What do you know about previous calibration results?
```

The agent reads from the knowledge directories and returns relevant stored findings, device parameters, and calibration notes.

> **To add your own reference material:** Drop Markdown files into `cookbook/data/knowledge/documents/` or `cookbook/data/knowledge/skills/`. The agent picks them up automatically on the next session.

---

## Path 5 — Build & Run a Calibration Workflow

Workflows chain multiple experiments into a dependency graph (DAG) that the agent executes step by step, passing results between nodes automatically.

### Step 1 — Plan collaboratively

```
I want to fully characterize a new superconducting qubit. What experiments should
I run, in what order, and how will I know when each step has succeeded?
```

The agent proposes a calibration sequence and success criteria for each step. This is a planning conversation — nothing executes yet. Use it to verify the agent understands your goals before committing to a long run.

### Step 2 — Generate and run the workflow

```
Create and run that as a calibration workflow.
```

The agent builds a DAG from the plan:

```
resonator_spectroscopy → qubit_spectroscopy → rabi_oscillation → ramsey_measurement
```

Each node's outputs feed the next node's inputs (e.g., `qubit_freq` from spectroscopy flows into the Rabi drive frequency). The workflow tracks state per node:

| State | Meaning |
|---|---|
| `pending` | Waiting for dependencies |
| `running` | Currently executing |
| `success` | Completed, results extracted |
| `failed` | Failed after retries |
| `skipped` | Intentionally skipped |

In the web UI, the calibration panel shows live node-by-node progress. In the CLI, use `qca workflow watch <id>` for real-time status.

### Inspect a workflow after the fact

```
qca workflow status <id>     # Detailed progress and suggestions
qca workflow history <id>    # Event log
qca workflow nodes <id>      # Node states
```

> **To describe your own sequence:** The agent builds the DAG from natural language. Try: *"Create a workflow that runs resonator_spectroscopy first, then qubit_spectroscopy using the resonator frequency it finds, then rabi_oscillation."*

---

## Quick Reference

| Task | Command |
|------|---------|
| Interactive TUI | `qca` |
| Single prompt | `qca -n "your prompt"` |
| Quiet mode (pipe-friendly) | `qca -n "prompt" -q` |
| Resume session | `qca -r <thread-id>` |
| Auto-approve tool calls | `qca -y` |
| List experiments | `qca experiments list` |
| Show experiment schema | `qca experiments schema <name>` |
| Run experiment (CLI) | `qca experiments run <name> --param key=value` |
| List past experiments | `qca history list` |
| Show experiment details | `qca history show <id>` |
| List workflows | `qca workflow list` |
| Watch workflow | `qca workflow watch <id>` |
| Web UI | `qca serve` + `cd ui && npm run dev` → http://localhost:3000 |

**Experiment data** is stored as HDF5 files in `cookbook/data/experiments/` organized by date (`YYYY/MM/DD/`). Override the base path with the `QCAL_DATA_DIR` environment variable.

**Knowledge base** persists in `cookbook/data/knowledge/` with subdirectories for `documents/`, `skills/`, and `memory/`. Add your own Markdown files to any subdirectory — the agent references them automatically.

---

## Adding Your Own Experiments

The agent has a built-in skill for writing experiment scripts (`cookbook/data/knowledge/skills/writing-experiment-scripts.md`). Just describe what you want to measure — the agent writes the script, places it in `scripts/`, and validates it for you.

### Ask the agent to create one

```
Write me an experiment script that sweeps laser detuning from -30 to 0 MHz
and measures atom number in a MOT. The default range should be -20 to -5 MHz
with 50 points.
```

The agent will:
1. Write a properly formatted script with `Annotated` type hints, docstring, and the correct return structure
2. Save it to `scripts/`
3. Run `qca experiments validate` to confirm it passes all checks
4. Verify it appears in `qca experiments list`

You can then run it immediately:

```
Run the new MOT detuning sweep with default parameters.
```

### Ask the agent to modify an existing one

```
Add a drive_duration parameter to the Rabi oscillation experiment, range 0.01 to 0.5 us,
default 0.1.
```

The agent reads the existing script, adds the parameter with the right type hints, and validates the result.

### Validate manually (optional)

If you prefer to write scripts by hand, validate them with:

```bash
qca experiments validate scripts/my_experiment.py --human
```

This checks that the script has a public function with `Annotated` type hints, a `-> dict` return type, and a Google-style docstring. See `cookbook/data/knowledge/skills/writing-experiment-scripts.md` for the full interface specification.
