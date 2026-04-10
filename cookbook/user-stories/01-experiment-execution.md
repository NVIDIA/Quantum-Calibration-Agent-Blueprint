# Epic 1: Experiment Execution

Discovering and running quantum calibration experiments.

## Stories

### EXP-001 List Available Experiments

**As a** Quantum Researcher,
**I want to** see all available calibration experiments,
**So that** I know what experiments I can run.

**Acceptance Criteria:**
- [ ] Can list experiments via CLI (`qca experiments list`)
- [ ] Can ask agent "what experiments are available?"
- [ ] Each experiment shows name and brief description

**Status:** Draft

---

### EXP-002 View Experiment Schema

**As a** Quantum Researcher,
**I want to** see the parameters and their types for an experiment,
**So that** I know what inputs are required and their valid ranges.

**Acceptance Criteria:**
- [ ] Can view schema via CLI (`qca experiments schema <name>`)
- [ ] Shows parameter name, type, default value, and range
- [ ] Indicates which parameters are required vs optional

**Status:** Draft

---

### EXP-003 Run Experiment with Defaults

**As a** Quantum Researcher,
**I want to** run an experiment using default parameters,
**So that** I can quickly get baseline results.

**Acceptance Criteria:**
- [ ] Can run via CLI (`qca experiments run <name>`)
- [ ] Can ask agent "run a qubit spectroscopy"
- [ ] Experiment executes and returns results
- [ ] Results are automatically stored

**Status:** Draft

---

### EXP-004 Run Experiment with Custom Parameters

**As a** Quantum Researcher,
**I want to** specify custom parameter values when running an experiment,
**So that** I can explore different calibration settings.

**Acceptance Criteria:**
- [ ] Can pass parameters via CLI flags
- [ ] Can specify parameters in natural language to agent
- [ ] Invalid parameters are rejected with helpful error messages
- [ ] Out-of-range values show warning with valid range

**Status:** Draft

---

### EXP-005 View Real-time Experiment Progress

**As a** Quantum Researcher,
**I want to** see progress while an experiment runs,
**So that** I know it's working and can estimate completion.

**Acceptance Criteria:**
- [x] Progress output written to log file in real-time (`cookbook/data/experiments/{id}/output.log`)
- [x] Web UI can poll `/history/{id}/logs` endpoint for progress updates
- [x] Can see which step/iteration is currently running via log content
- [x] Experiment scripts use unbuffered output (`PYTHONUNBUFFERED=1`) for immediate flushing

**Implementation Notes:**
- Experiment ID is generated before execution starts, enabling log access during run
- Log file is flushed immediately as progress is written
- API endpoint returns last N lines for efficient polling

**Status:** Implemented

---

### EXP-006 Run Experiment on Specific Target

**As a** Quantum Researcher,
**I want to** specify which qubit or resonator to calibrate,
**So that** I can target specific components of my device.

**Acceptance Criteria:**
- [ ] Can specify target (e.g., `qubit_0`, `resonator_1`)
- [ ] Target is recorded in experiment metadata
- [ ] Can filter history by target

**Status:** Draft

---

### EXP-007 Cancel Running Experiment

**As a** Quantum Researcher,
**I want to** cancel an experiment that's taking too long or showing bad data,
**So that** I don't waste time on faulty runs.

**Acceptance Criteria:**
- [ ] Can cancel via keyboard interrupt (Ctrl+C)
- [ ] Partial results are saved if available
- [ ] Status is marked as "cancelled" not "failed"

**Status:** Draft

---

### EXP-008 Re-run Previous Experiment

**As a** Quantum Researcher,
**I want to** re-run a previous experiment with the same parameters,
**So that** I can verify reproducibility.

**Acceptance Criteria:**
- [ ] Can reference previous experiment by ID
- [ ] Can ask agent "run that again" or "repeat last experiment"
- [ ] Original parameters are reused exactly

**Status:** Draft
