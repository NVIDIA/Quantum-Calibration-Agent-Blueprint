# User Stories

User stories describing how users interact with QCA (NVIDIA Quantum Calibration Agent).

## Personas

See [personas.md](personas.md) for detailed persona definitions.

| Persona | Description |
|---------|-------------|
| Quantum Researcher | Primary user running calibration experiments |
| Lab Technician | Operator executing routine calibration workflows |
| System Administrator | Manages deployment and configuration |

## Epics

| # | Epic | File |
|---|------|------|
| 1 | [Experiment Execution](01-experiment-execution.md) | Discovering and running calibration experiments |
| 2 | [Data Analysis](02-data-analysis.md) | Querying history and analyzing results |
| 3 | [Workflow Management](03-workflow-management.md) | Creating and managing multi-step workflows |
| 4 | [Agent Interaction](04-agent-interaction.md) | Conversational assistance and guidance |
| 5 | [System Setup](05-system-setup.md) | Configuration and deployment |

## Story Format

Each story follows this format:

```
### EPIC-### Story Title

**As a** [persona],
**I want to** [action],
**So that** [benefit].

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
```

## Story Status Legend

- `Draft` - Initial story, needs refinement
- `Ready` - Refined and ready for implementation
- `Done` - Implemented and verified
