---
name: workflow-planning
description: Plan a new calibration workflow by discussing experiment sequences, success/failure criteria, and extracted parameters with the user before any files are created. Use when the user asks to plan, design, or create a new calibration sequence, or to build a multi-step workflow for a qubit or device. Requires explicit user confirmation before writing workflow files.
---

# Workflow Planning

Create calibration workflows through discussion with the user. A workflow defines a sequence of operations with dependencies.

## Before Planning

**Always check memory first:**
1. Read `memory/workflow-preferences.md` if it exists
2. Look for past conventions, preferred experiment sequences, success criteria patterns
3. Apply any user preferences to your proposal

## Planning Process

### Step 1: Understand the Goal

Ask the user:
- What is the calibration objective?
- Which qubits/targets are involved?
- Any specific constraints or requirements?

### Step 2: Propose the Sequence

Based on the goal, propose a sequence of nodes. For each node, discuss:

1. **Experiment type** - Which experiment to run
2. **Success criteria** - How to know it worked
3. **Failure criteria** - How to know it failed
4. **What to extract** - Parameters to carry forward

Example discussion:
```
For Node 1 (Resonator Spectroscopy), I suggest:
- Success: Clear dip with depth > 3 dB
- Failure: No dip visible or multiple dips
- Extract: resonator_frequency

Does this match your expectations? Any adjustments?
```

### Step 3: Wait for Confirmation

**Do NOT create the workflow until the user confirms.**

Wait for explicit confirmation like:
- "go ahead"
- "create it"
- "looks good, proceed"
- "confirmed"

If the user says "don't ask, just do it" for future workflows, note this in memory.

### Step 4: Remember Corrections

If the user corrects your decisions:
1. Apply the correction to the current workflow
2. **Update memory** with the preference for future workflows

Example corrections to remember:
- "Always use SNR > 10, not SNR > 5"
- "For T1 measurements, extract t1_time in microseconds"
- "Start resonator sweeps at 5.5 GHz for this device"

Write to `memory/workflow-preferences.md`:
```markdown
## Success Criteria Preferences
- Resonator spectroscopy: depth > 3 dB, SNR > 10
- Qubit spectroscopy: SNR > 10 (not 5)

## Parameter Conventions
- T1 times in microseconds
- Frequencies in GHz

## Device-Specific
- Resonator range: 5.5 - 6.5 GHz
```

## Creating the Workflow

After confirmation, create the workflow files.

### Storage Structure

```
data/workflows/
└── {workflow_id}/
    ├── workflow.json      # DAG structure
    └── plan.md            # Detailed planning document
```

### Step 1: Create Folder

```bash
mkdir -p data/workflows/{workflow_id}
```

Use a descriptive ID like `calibrate_q0_20240315`.

**IMPORTANT: Always use relative paths** when creating workflow files. Use `data/workflows/{workflow_id}/workflow.json`, NOT absolute paths like `/home/.../data/workflows/...`. Absolute paths will fail due to virtual filesystem mode.

### Step 2: Write workflow.json

```json
{
  "id": "calibrate_q0",
  "name": "Calibrate Qubit Q0",
  "objective": "Full calibration sequence for Q0",
  "status": "created",
  "nodes": [
    {
      "id": "node_1",
      "name": "Resonator Spectroscopy",
      "dependencies": []
    },
    {
      "id": "node_2",
      "name": "Qubit Spectroscopy",
      "dependencies": ["node_1"]
    }
  ]
}
```

**Required fields:**
- `id`: Must match folder name
- `name`: Human-readable name
- `nodes`: Array with `id`, `name`, `dependencies`

**Status values:** `created`, `running`, `completed`, `failed`

### Step 3: Write plan.md

Include all discussed details:

```markdown
# Calibration Plan: Calibrate Qubit Q0

## Objective
Full calibration sequence for qubit Q0.

## Node 1: Resonator Spectroscopy

**Experiment type**: ResonatorSpectroscopy

**Parameters**:
- Start frequency: 5.5 GHz
- Stop frequency: 6.5 GHz
- Number of points: 101

**Success criteria**:
- Clear dip visible
- Depth > 3 dB
- SNR > 10

**Failure criteria**:
- No dip visible
- Multiple dips (mode crossing)

**Extract**: `resonator_frequency`

---

## Node 2: Qubit Spectroscopy

**Experiment type**: QubitSpectroscopyFrequency

**Parameters**:
- Center: Use expected qubit frequency
- Span: 200 MHz

**Success criteria**:
- Single clear peak
- SNR > 10

**Failure criteria**:
- No peak visible
- Multiple peaks

**Extract**: `qubit_frequency`
```

### Step 4: Validate (REQUIRED)

**You MUST call validate after creating the workflow files:**

```python
workflow(action="validate", workflow_id="calibrate_q0")
```

The validation returns detailed checks:
- `valid`: Whether the workflow is valid
- `checks`: List of individual validation checks with pass/fail status
- `errors`: Critical issues that must be fixed
- `warnings`: Non-critical issues to consider
- `workflow_info`: Summary of the workflow

**If validation fails:**
1. Review the `errors` list
2. Fix each error in workflow.json
3. Re-run validate until `valid: true`

**Do NOT consider the workflow creation complete until validation passes.**

## Dependencies

Nodes execute in dependency order:

```
node_1 ──→ node_2 ──→ node_3
              │
              └──→ node_4
```

In JSON:
```json
{
  "nodes": [
    {"id": "node_1", "name": "First", "dependencies": []},
    {"id": "node_2", "name": "Second", "dependencies": ["node_1"]},
    {"id": "node_3", "name": "Third A", "dependencies": ["node_2"]},
    {"id": "node_4", "name": "Third B", "dependencies": ["node_2"]}
  ]
}
```

## Listing Workflows

```python
workflow(action="list")
```

## Modifying a Workflow

1. Read the current `workflow.json`
2. Edit using the Edit tool
3. **Re-validate (REQUIRED):**
   ```python
   workflow(action="validate", workflow_id="your_workflow_id")
   ```
4. Fix any errors and re-validate until `valid: true`

**You MUST validate after ANY modification to workflow.json.**
