# Epic 3: Workflow Management

Creating and managing multi-step calibration workflows.

## Stories

### WF-001 List Available Workflows

**As a** Lab Technician,
**I want to** see all defined workflows,
**So that** I know what calibration sequences are available.

**Acceptance Criteria:**
- [ ] Can list via CLI (`qca workflow list`)
- [ ] Shows workflow ID, name, and status
- [ ] Indicates which workflows are in progress

**Status:** Draft

---

### WF-002 View Workflow Definition

**As a** Lab Technician,
**I want to** see the steps in a workflow,
**So that** I understand what will be executed.

**Acceptance Criteria:**
- [ ] Can view via CLI (`qca workflow show <id>`)
- [ ] Shows all nodes/steps with their experiments
- [ ] Shows dependencies between steps

**Status:** Draft

---

### WF-003 Start Workflow Execution

**As a** Lab Technician,
**I want to** start a workflow,
**So that** I can run a full calibration sequence.

**Acceptance Criteria:**
- [ ] Can start via CLI (`qca workflow start <id>`)
- [ ] Can ask agent "start the daily calibration workflow"
- [ ] Workflow status changes to "running"
- [ ] First step begins execution

**Status:** Draft

---

### WF-004 Monitor Workflow Progress

**As a** Lab Technician,
**I want to** see the current status of a running workflow,
**So that** I know which step is executing and overall progress.

**Acceptance Criteria:**
- [ ] Can check status via CLI (`qca workflow status <id>`)
- [ ] Shows status of each node (pending/running/success/failed)
- [ ] Shows overall completion percentage
- [ ] Web UI provides visual progress indicator

**Status:** Draft

---

### WF-005 Pause Running Workflow

**As a** Lab Technician,
**I want to** pause a running workflow,
**So that** I can address issues without losing progress.

**Acceptance Criteria:**
- [ ] Can pause via CLI or agent
- [ ] Current step completes before pausing
- [ ] Status changes to "paused"
- [ ] No new steps start

**Status:** Draft

---

### WF-006 Resume Paused Workflow

**As a** Lab Technician,
**I want to** resume a paused workflow,
**So that** I can continue from where it stopped.

**Acceptance Criteria:**
- [ ] Can resume via CLI or agent
- [ ] Execution continues from next pending step
- [ ] Completed steps are not re-run
- [ ] Status changes back to "running"

**Status:** Draft

---

### WF-007 Cancel Workflow

**As a** Lab Technician,
**I want to** cancel a workflow that's not going well,
**So that** I can stop wasting resources on failed calibration.

**Acceptance Criteria:**
- [ ] Can cancel via CLI or agent
- [ ] Running step is terminated
- [ ] Status changes to "cancelled"
- [ ] Partial results are preserved

**Status:** Draft

---

### WF-008 Create New Workflow

**As a** Quantum Researcher,
**I want to** define a new calibration workflow,
**So that** I can automate multi-step procedures.

**Acceptance Criteria:**
- [ ] Can create workflow via JSON file
- [ ] Can describe workflow to agent in natural language
- [ ] Workflow is validated before saving
- [ ] Dependencies are checked for cycles

**Status:** Draft

---

### WF-009 Modify Existing Workflow

**As a** Quantum Researcher,
**I want to** edit an existing workflow definition,
**So that** I can adjust steps or parameters.

**Acceptance Criteria:**
- [ ] Can edit workflow JSON directly
- [ ] Can ask agent to modify workflow
- [ ] Changes validated before saving
- [ ] Cannot modify running workflows

**Status:** Draft

---

### WF-010 Handle Workflow Step Failure

**As a** Lab Technician,
**I want to** be notified when a workflow step fails,
**So that** I can decide how to proceed.

**Acceptance Criteria:**
- [ ] Failure is clearly indicated in status
- [ ] Error message from failed experiment is shown
- [ ] Options to retry, skip, or abort are available
- [ ] Can ask agent for troubleshooting advice

**Status:** Draft

---

### WF-011 Retry Failed Workflow Step

**As a** Lab Technician,
**I want to** retry a failed step in a workflow,
**So that** I can recover from transient failures.

**Acceptance Criteria:**
- [ ] Can retry specific step
- [ ] Can optionally modify parameters for retry
- [ ] Workflow continues if retry succeeds

**Status:** Draft

---

### WF-012 Skip Failed Workflow Step

**As a** Lab Technician,
**I want to** skip a failed step and continue the workflow,
**So that** I can complete partial calibration.

**Acceptance Criteria:**
- [ ] Can mark step as skipped
- [ ] Dependent steps are also skipped
- [ ] Non-dependent steps continue
- [ ] Final status reflects skipped steps

**Status:** Draft
