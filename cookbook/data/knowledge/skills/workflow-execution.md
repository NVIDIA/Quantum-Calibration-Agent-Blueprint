# Workflow Execution

Execute a planned workflow node by node, tracking progress and handling failures.

## Overview

You execute workflows by:
1. Reading the workflow state and plan
2. For each node, running the experiment directly using `run_experiment`
3. Analyzing results with `vlm_inspect` when visual verification is needed
4. Updating workflow state using `workflow(action="update", ...)`
5. Logging events using `workflow(action="log", ...)`
6. Making decisions on failures (or pausing for human input)

## Safe State Updates

**Use the workflow tool for all state changes.** Never edit workflow.json directly.

### Update Action

Updates workflow state with automatic validation:

```python
workflow(
    action="update",
    workflow_id="calibrate_q0",
    data={
        "status": "running",
        "nodes.node_1.state": "success",
        "nodes.node_1.extracted": {"resonator_frequency": 5.823},
        "context.resonator_frequency": 5.823
    }
)
```

**Features:**
- Validates before writing (reverts on failure)
- Supports dot notation for nested updates
- Creates intermediate objects as needed
- Atomically updates multiple fields

**Dot notation examples:**
- `"status": "running"` - Simple field
- `"context.resonator_freq": 5.823` - Nested path
- `"nodes.node_1.state": "success"` - Node by ID
- `"nodes.node_1.experiment_id": "20240315_..."` - Link node to experiment
- `"nodes.node_1.extracted": {...}` - Node nested field

### Log Action

Appends events to history.jsonl with auto-timestamp:

```python
workflow(
    action="log",
    workflow_id="calibrate_q0",
    event="node_completed",
    node="node_1",
    state="success",
    extracted={"resonator_frequency": 5.823}
)
```

The timestamp is added automatically.

## Storage Structure

```
data/workflows/{workflow_id}/
├── workflow.json      # Current state (updated via workflow tool)
├── plan.md            # Planning document (read-only during execution)
└── history.jsonl      # Event log (appended via workflow tool)
```

## Workflow State

**workflow.json** during execution:
```json
{
  "id": "calibrate_q0",
  "name": "Calibrate Qubit Q0",
  "status": "running",
  "current_node": "node_2",
  "started_at": "2024-03-15T10:30:00Z",
  "nodes": [
    {
      "id": "node_1",
      "name": "Resonator Spectroscopy",
      "dependencies": [],
      "state": "success",
      "run_count": 1,
      "completed_at": "2024-03-15T10:32:00Z",
      "experiment_id": "20240315_103015_resonator_spectroscopy",
      "extracted": {"resonator_frequency": 5.823}
    },
    {
      "id": "node_2",
      "name": "Qubit Spectroscopy",
      "dependencies": ["node_1"],
      "state": "running",
      "run_count": 1,
      "started_at": "2024-03-15T10:32:15Z"
    },
    {
      "id": "node_3",
      "name": "Rabi Oscillations",
      "dependencies": ["node_2"],
      "state": "pending"
    }
  ],
  "context": {
    "resonator_frequency": 5.823
  }
}
```

**Status values**: `created` → `running` → `paused` / `completed` / `failed`

**Node states**: `pending` → `running` → `success` / `failed` / `skipped`

## Execution Steps

### Step 1: Load State

Read workflow.json using `workflow(action="status", workflow_id="...")`:
- Current workflow status
- Which nodes are complete (and their extracted values)
- Which node to execute next

### Step 2: Find Next Node

Find a node where:
- `state` is `pending`
- All `dependencies` have `state: success`

If no such node exists:
- All nodes complete → mark workflow `completed`
- Some nodes failed/skipped with no path forward → mark workflow `failed`

### Step 3: Execute Node

1. **Mark node as running**:
   ```python
   workflow(
       action="update",
       workflow_id="calibrate_q0",
       data={
           "current_node": "node_1",
           "nodes.node_1.state": "running",
           "nodes.node_1.run_count": 1,
           "nodes.node_1.started_at": "2024-03-15T10:30:00Z"
       }
   )
   ```

2. **Log to history**:
   ```python
   workflow(action="log", workflow_id="calibrate_q0", event="node_started", node="node_1", run=1)
   ```

3. **Gather context** from completed nodes and plan.md

4. **Run the experiment** using `run_experiment`:
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

5. **Analyze results** using `vlm_inspect` when visual verification is needed:
   ```python
   vlm_inspect(
     experiment_id="20240315_103015_resonator",
     prompt="Is there a clear dip? What is the resonator frequency?"
   )
   ```

6. **Evaluate success criteria**:
   - Check returned values (SNR, frequency, etc.)
   - Use VLM analysis for visual criteria
   - If criteria not met, retry with adjusted parameters (up to max attempts)

7. **Proceed to Step 4** with the result

### Step 4: Evaluate Result

**On success**:
1. Extract values as specified in plan.md
2. Update state (**always include `experiment_id`** from the `run_experiment` result's `id` field — this links the node to its plot in the UI):
   ```python
   workflow(
       action="update",
       workflow_id="calibrate_q0",
       data={
           "nodes.node_1.state": "success",
           "nodes.node_1.completed_at": "2024-03-15T10:32:00Z",
           "nodes.node_1.experiment_id": "20240315_103015_resonator_spectroscopy",
           "nodes.node_1.extracted": {"resonator_frequency": 5.823},
           "context.resonator_frequency": 5.823
       }
   )
   ```
3. Log completion:
   ```python
   workflow(
       action="log",
       workflow_id="calibrate_q0",
       event="node_completed",
       node="node_1",
       state="success",
       extracted={"resonator_frequency": 5.823}
   )
   ```
4. Go to Step 2 (next node)

**On failure** (after max attempts):
1. Update state:
   ```python
   workflow(
       action="update",
       workflow_id="calibrate_q0",
       data={
           "nodes.node_2.state": "failed",
           "nodes.node_2.completed_at": "2024-03-15T10:33:00Z",
           "nodes.node_2.observations": "No peak found after 3 attempts"
       }
   )
   ```
2. Log failure:
   ```python
   workflow(
       action="log",
       workflow_id="calibrate_q0",
       event="node_completed",
       node="node_2",
       state="failed",
       observations="No peak found after 3 attempts"
   )
   ```
3. Go to Step 5 (decide next action)

### Step 5: Handle Failure

Review the failure and history. Decide:

**If clear what to do** (based on your analysis):

- **Backtrack**: A previous node's result may be invalid
  ```python
  # Reset nodes
  workflow(
      action="update",
      workflow_id="calibrate_q0",
      data={
          "nodes.node_1.state": "pending",
          "nodes.node_2.state": "pending"
      }
  )
  # Log backtrack
  workflow(action="log", workflow_id="calibrate_q0", event="backtrack", from_node="node_2", to_node="node_1", reason="Resonator may have drifted")
  ```

- **Skip**: Node is optional, continue without it
  ```python
  workflow(
      action="update",
      workflow_id="calibrate_q0",
      data={"nodes.node_2.state": "skipped"}
  )
  workflow(action="log", workflow_id="calibrate_q0", event="node_skipped", node="node_2", reason="Optional measurement")
  ```

**If unclear, pause for human**:

1. Update workflow status:
   ```python
   workflow(
       action="update",
       workflow_id="calibrate_q0",
       data={
           "status": "paused",
           "paused_at": "2024-03-15T10:34:00Z",
           "paused_reason": "Qubit spectroscopy failed after 3 attempts",
           "suggestions": [
               {"action": "backtrack", "target": "node_1", "reason": "Resonator frequency may have drifted"},
               {"action": "retry", "reason": "Try with wider frequency range"},
               {"action": "skip", "reason": "Continue without qubit frequency"},
               {"action": "abort", "reason": "Stop workflow, investigate hardware"}
           ]
       }
   )
   ```

2. Log pause:
   ```python
   workflow(action="log", workflow_id="calibrate_q0", event="workflow_paused", reason="Qubit spectroscopy failed")
   ```

3. Inform user and wait for decision

## Resuming a Paused Workflow

When user provides a decision:

1. Log the decision:
   ```python
   workflow(action="log", workflow_id="calibrate_q0", event="human_decision", decision="backtrack", target="node_1")
   ```

2. Execute the decision:
   - **backtrack**: Reset nodes and continue from target
   - **retry**: Re-run current node with new approach
   - **skip**: Mark node skipped, continue
   - **abort**: Mark workflow `failed`, stop

3. Update status:
   ```python
   workflow(action="update", workflow_id="calibrate_q0", data={"status": "running"})
   ```

4. Continue execution from Step 2

## Resuming After Interruption

If workflow shows `status: running` but was interrupted:

1. Check `current_node` - this node was interrupted
2. Treat it as a fresh start for that node (reset to `pending`)
3. Continue execution normally

## Checking Status

Use the workflow tool:
```python
workflow(action="status", workflow_id="calibrate_q0")
```

Shows:
- Current status and progress
- Node states
- Recent history
- Suggestions (if paused)

## Example Execution Session

```
User: Execute workflow calibrate_q0

Agent: Starting workflow "Calibrate Qubit Q0"...

[Calls: workflow(action="status", workflow_id="calibrate_q0")]

Executing node_1: Resonator Spectroscopy...

[Calls: workflow(action="update", ..., data={"current_node": "node_1", "nodes.node_1.state": "running", ...})]
[Calls: workflow(action="log", ..., event="node_started", node="node_1")]

> Running experiment with center_freq=6.0 GHz, span=0.2 GHz
> Experiment complete: 20240315_103015_resonator
> Analyzing plot with vlm_inspect...
> VLM: "Clear dip visible at 5.823 GHz. SNR ~12."

Node_1 SUCCESS
- Extracted: resonator_frequency = 5.823 GHz

[Calls: workflow(action="update", ..., data={"nodes.node_1.state": "success", "nodes.node_1.extracted": {...}, "context.resonator_frequency": 5.823})]
[Calls: workflow(action="log", ..., event="node_completed", state="success")]

Moving to next node...

Executing node_2: Qubit Spectroscopy...

> Using resonator_frequency = 5.823 GHz from context
> Attempt 1: center=4.5 GHz, span=0.2 GHz
> Analyzing plot... No clear peak found
> Attempt 2: Expanding range to span=0.4 GHz
> Analyzing plot... Still no peak visible
> Attempt 3: Expanding range to span=0.6 GHz
> Analyzing plot... No peak found

Node_2 FAILED after 3 attempts
- Observations: No peak found with increasing range

[Calls: workflow(action="update", ..., data={"nodes.node_2.state": "failed", "status": "paused", ...})]
[Calls: workflow(action="log", ..., event="node_completed", state="failed")]
[Calls: workflow(action="log", ..., event="workflow_paused")]

Pausing workflow for human decision.

Suggestions:
1. Backtrack to node_1: Resonator frequency may have drifted
2. Retry with different center frequency
3. Skip this node (will affect downstream calibration)
4. Abort workflow

Please advise which action to take.

User: Try backtracking to node_1

Agent: Backtracking to node_1...

[Calls: workflow(action="log", ..., event="human_decision", decision="backtrack")]
[Calls: workflow(action="update", ..., data={"nodes.node_1.state": "pending", "nodes.node_2.state": "pending", "status": "running"})]

Executing node_1: Resonator Spectroscopy (run 2)...

> Running experiment...
> Found dip at 5.819 GHz (shifted from 5.823)

Node_1 SUCCESS
- Extracted: resonator_frequency = 5.819 GHz

[Updates state, continues to node_2...]
```

## Best Practices

1. **Execute experiments directly** - Use `run_experiment` and `vlm_inspect` tools
2. **Use workflow tool for state changes** - Never edit workflow.json directly
3. **Log key events** - Record node start, experiment completion, node completion
4. **Use context from previous nodes** - Pass extracted values to subsequent experiments
5. **Be conservative with failures** - When unsure, pause and ask the user

## Workflow Tool Actions Reference

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `list` | List all workflows | - |
| `status` | Show workflow progress | `workflow_id` |
| `history` | Show event history | `workflow_id`, optional `last_n` |
| `validate` | Validate workflow structure | `workflow_id` |
| `update` | Update workflow state | `workflow_id`, `data` |
| `log` | Append event to history | `workflow_id`, `event`, any additional fields |
