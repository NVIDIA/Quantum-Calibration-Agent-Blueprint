# QCA Lite backend upstream-plugin migration plan

**Status:** complete; implemented, validated, and delivered in GitLab MR !4

**Authoritative source:** `git@github.com:NVIDIA/Quantum-Calibration-Agent-Blueprint.git`, branch
`main`

**Delivery repository:**
`ssh://git@gitlab-master.nvidia.com:12051/quantum-calibration-ai/quantum-calibration-agent-blueprint.git`

## Objective

Migrate the small QuTiP digital twin onto the current official QCA without replacing, forking, or
patching QCA's TUI and core. Official GitHub is read-only. Its `main` branch is mirrored to the
GitLab branch `github-main`; GitLab `main` remains independent and untouched. Development happens
on `extended-backend`, and the GitLab merge request targets `github-main`.

The deliverable is a standalone backend plugin plus thin experiment adapters that the existing QCA
TUI can discover and call. It must retain real QuTiP dynamics, seeded or explicitly configured
immutable hidden truth, CPU operation, and verified CUDA activation when a compatible GPU exists.

## Branch contract

```text
Official GitHub main (read-only authority)
NVIDIA/Quantum-Calibration-Agent-Blueprint
                  |
                  | exact mirror; push only to GitLab
                  v
GitLab github-main
                  |
                  +-- extended-backend
                         |
                         +-- GitLab MR -> github-main

GitLab main -------------------------------- preserved for other development
```

The names of local remotes are not evidence of authority. Repository identity must be checked
before every mirror or delivery action:

- `upstream` must resolve to `NVIDIA/Quantum-Calibration-Agent-Blueprint` on GitHub;
- `origin` must resolve to the NVIDIA GitLab delivery repository;
- all pushes must name `origin` explicitly;
- no command may push to `upstream`, `github`, or `fork`.

## Current state requiring migration

At plan creation:

- official GitHub `main` is `d8d37bc4de28d2347d8e21405903b29a2891f793`;
- GitLab `main` is `b5c86f1210d0f20ee1209733a8e72f5a486d133c` and must not move;
- GitLab `extended-backend` is `5f966e581b71a43f5c052353d04a1d9918e0115f`;
- MR !3 incorrectly targets GitLab `main`;
- the current implementation modifies the headless fork's `cli.py`, `core/state/*`, and root
  packaging, so it must not be cherry-picked wholesale onto official QCA.

These hashes are an audit snapshot, not permanent expected values. Re-read live refs immediately
before migration and use the newly observed official GitHub `main` as the mirror source.

## Non-negotiable invariants

1. GitLab `main` is never reset, merged, rebased, or used as the MR target.
2. GitLab `github-main` exactly matches the selected official GitHub `main` commit before plugin
   development begins.
3. GitHub is read-only. The migration makes no GitHub branches, tags, commits, pull requests, or
   pushes.
4. `extended-backend` is based on GitLab `github-main`, and its MR targets `github-main`.
5. The plugin does not alter QCA's TUI, agent, tools, discovery, runner, storage, workflow engine,
   server, or root dependency set.
6. The backend remains separately testable and installable. QCA-facing files are thin adapters,
   not a second simulation implementation.
7. Hidden truth is immutable after session creation and is exposed only by a digest in both seeded
   and explicit configuration modes.
8. CUDA is selected only after a real QuTiP/cuQuantum solver probe succeeds. `auto` may fall back
   to CPU with a recorded reason; explicit `cuda` fails closed.
9. Migration work occurs in a clean linked worktree so unrelated files in the existing worktree
   are never staged, moved, stashed, deleted, or committed.

## Target plugin boundary

Official QCA has no general backend-plugin registry. Its supported extension seam is experiment
discovery: the native TUI's lab tool scans top-level `scripts/*.py`, and the runner executes those
functions in subprocesses. The migration therefore uses a separately packaged backend with
drop-in experiment adapters:

```text
plugins/qca-lite-qutip-twin/
  pyproject.toml
  src/qca_lite_twin/
    __init__.py
    __main__.py
    app.py
    model.py
    simulator.py
  tests/

scripts/
  _lite_twin_client.py
  lite_resonator_spectroscopy.py
  lite_qubit_spectroscopy.py
  lite_rabi_amplitude.py
  lite_ramsey_frequency.py
  lite_t1.py
```

The five runtime modules retain the deliberately small engine. The private adapter helper owns the
HTTP contract. Each public `lite_*` function follows official QCA's documented function signature
and result grammar (`status`, typed `data`, arrays, and plots). The plugin is installed into the
same environment as QCA so experiment subprocesses can import its dependencies. The root QCA
`pyproject.toml` does not gain QuTiP or CUDA dependencies.

The plugin service remains a separate process. The adapters reach it through one documented URL
environment variable. They never import QCA internals and QCA never administers hidden truth.

## What migrates and what does not

### Port and adapt

- the five-file `qca_lite_twin` runtime;
- seeded and explicit immutable-truth provisioning;
- real QuTiP pulse, delay, relaxation, and dephasing evolution;
- CUDA activation and provenance reporting;
- the five experiment algorithms and plots;
- focused physics, HTTP-contract, reproducibility, and GPU tests;
- concise operator documentation and the manual TUI validation record.

### Do not port

- changes to `cli.py`;
- changes to `core/state/doctor.py`, `core/state/evidence.py`, or `core/state/store.py`;
- changes to official QCA's root packaging or dependency list;
- the headless fork's profile/session/calibration-acceptance machinery;
- the old `scripts/_twin_client.py` as a shared-core modification;
- profile specifications and tests that only exercise the headless fork's state model.

Do not cherry-pick commit `5f966e5` as a unit. Copy or replay only reviewed plugin-owned files and
rewrite adapters against the official experiment contract.

## Migration procedure

### Phase 1 — verify and create the GitLab mirror branch

1. Confirm the repository root, current worktrees, worktree cleanliness, and all remote URLs.
2. Read the live official GitHub `main` hash and the live GitLab hashes for `main`, `github-main`,
   and `extended-backend`.
3. Record the GitLab `main` hash as a preservation invariant.
4. Fetch official GitHub `main` without merging it into any checked-out branch.
5. Create or fast-forward GitLab `github-main` from the fetched official commit using an explicit
   `origin` push.
6. Verify with `git ls-remote` that GitLab `github-main` and official GitHub `main` are byte-identical
   commit IDs and that GitLab `main` did not move.

Representative commands, with hashes re-resolved at execution time:

```bash
git remote get-url upstream
git remote get-url origin
git ls-remote upstream refs/heads/main
git ls-remote origin refs/heads/main refs/heads/github-main refs/heads/extended-backend
git fetch --no-tags upstream main
git push origin refs/remotes/upstream/main:refs/heads/github-main
git ls-remote upstream refs/heads/main
git ls-remote origin refs/heads/main refs/heads/github-main
```

If `github-main` already exists and cannot fast-forward to official GitHub `main`, stop. Do not
force it until the divergent GitLab-only commits have been identified and an explicit preservation
decision has been made.

### Phase 2 — build in an isolated worktree

1. Fetch `origin/github-main`.
2. Create a new linked worktree and a temporary local migration branch from that exact ref.
3. Verify that the worktree contains official QCA's native TUI and that bare `qca` is its documented
   interactive entry point.
4. Add the standalone plugin package and new top-level adapter scripts only.
5. Keep the existing dirty worktree and its unrelated files untouched.

Example shape:

```bash
git fetch --no-tags origin github-main
git worktree add -b migration/extended-backend-plugin \
  /tmp/qca-extended-backend-plugin origin/github-main
```

### Phase 3 — adapt the implementation

1. Move the five runtime modules under the plugin's own `src/` package.
2. Give the plugin its own installation metadata and `lite-twin`/CUDA dependency groups.
3. Replace reliance on the headless fork's shared twin client with `_lite_twin_client.py` owned by
   the adapter set.
4. Convert all five experiment return documents to official QCA's public result grammar.
5. Preserve plots and raw arrays so QCA history, HDF5 storage, and VLM inspection work unchanged.
6. Keep calibration state inside the backend session or explicit experiment parameters; do not add
   registry or acceptance APIs to QCA core.
7. Add a native QCA workflow definition only if the existing workflow format can express the five
   sequential runs without core changes. Otherwise demonstrate the sequence through the TUI agent
   and retain the five experiments as the stable plugin contract.

### Phase 4 — targeted validation

Use a fresh Python 3.11 or 3.12 environment based on official `github-main`:

1. Install official QCA editable from the migration worktree.
2. Install the backend plugin editable with CPU dependencies; install its CUDA extra only on a GPU
   host.
3. Run the plugin's focused physics, truth, HTTP, and provenance tests.
4. Start the plugin in CPU mode and validate/list all five scripts through official QCA.
5. Run each experiment through `qca experiments run`, then verify history, arrays, plots, fitted
   outputs, and backend provenance.
6. Start in `auto` mode on a GPU host and require a real CUDA probe plus run provenance reporting
   `data_layer_used=cuda`; otherwise record the bounded CPU fallback reason.
7. Recreate seeded and explicit truth sessions and verify stable digests without exposing truth.
8. Confirm the host diff contains no modifications to QCA core or TUI files.

Required direct checks include:

```bash
qca experiments validate scripts/lite_resonator_spectroscopy.py --human
qca experiments validate scripts/lite_qubit_spectroscopy.py --human
qca experiments validate scripts/lite_rabi_amplitude.py --human
qca experiments validate scripts/lite_ramsey_frequency.py --human
qca experiments validate scripts/lite_t1.py --human
qca experiments list --human
```

### Phase 5 — native TUI proof

Create a dedicated Byobu/tmux tab in the clean migration worktree. Export only the plugin URL,
isolated QCA data directory, model-provider configuration already authorized on the host, and
unbuffered logging. Start the plugin service in the background, confirm its health endpoint, and
launch official QCA directly:

```bash
qca -y -m "Discover the QCA Lite experiments. Inspect every schema, then manually run resonator \
spectroscopy, qubit spectroscopy, Rabi amplitude, Ramsey frequency, and T1 in physical dependency \
order. Inspect each stored result, arrays, and plot before continuing. Carry measured outputs into \
the next experiment, never request hidden truth, and finish with backend/CUDA provenance and a \
clear pass-or-fail report. Do not edit source files."
```

The proof passes only if the native QCA TUI itself discovers and calls the adapters, all five runs
complete through official QCA storage, the plots are inspectable, downstream inputs come from prior
measured outputs, and no QCA source patch is needed.

### Phase 6 — safely replace the incorrect branch and MR

Do not rewrite the published branch until the candidate passes Phases 3–5.

1. Push the candidate under a temporary GitLab branch for review.
2. Preserve the current incorrect `extended-backend` tip under an explicitly named archival branch
   if retention is desired; otherwise retain its exact commit ID in the migration record.
3. Re-read the live `extended-backend` hash and use `--force-with-lease` pinned to that hash when
   replacing it. Never use an unqualified force push.
4. Retarget MR !3 from `main` to `github-main`, or close it and create a fresh MR if GitLab cannot
   present a clean replacement diff.
5. Update the MR title and description to state that the change is a standalone QuTiP backend
   plugin for official QCA.
6. Verify that the MR base SHA is the mirrored official commit, its head is the validated plugin
   commit, it contains no QCA core/TUI modifications, and GitLab `main` is unchanged.
7. Remove the temporary candidate branch only after the final MR is verified.

The branch replacement is destructive external state and requires explicit authorization at
execution time. A representative guarded push is:

```bash
git push --force-with-lease=refs/heads/extended-backend:<observed-old-sha> \
  origin migration/extended-backend-plugin:refs/heads/extended-backend
```

## Execution record

The migration completed on 2026-09-22:

- official GitHub `main` and GitLab `github-main` both resolved to `d8d37bc4`;
- GitLab `main` remained at `b5c86f1`;
- the old headless `extended-backend` tip `5f966e5` was preserved at
  `archive/extended-backend-headless-20260922`;
- the validated upstream-based candidate replaced `extended-backend` with an exact
  `--force-with-lease`;
- MR !3 was retargeted, but GitLab retained stale conflict metadata despite an identical local
  merge tree, so it was documented and closed;
- clean replacement MR !4 targets `github-main` and GitLab reports it mergeable;
- no GitHub ref was mutated.

## Rollback

- If mirroring fails, leave GitLab `github-main` at its prior hash and do not touch other refs.
- If plugin validation fails, keep the candidate branch separate and leave MR !3 unchanged.
- If branch replacement succeeds but the final MR is wrong, restore the recorded old
  `extended-backend` commit with another hash-pinned `--force-with-lease`; GitLab `main` and
  `github-main` remain unaffected.
- Never use GitLab `main` as a recovery target.

## Completion criteria

Migration is complete only when all of the following are true:

- GitLab `main` is unchanged from its pre-migration hash;
- GitLab `github-main` exactly matches the selected official GitHub `main`;
- `extended-backend` descends from `github-main`;
- the MR targets `github-main` and shows only plugin, adapter, focused-test, and documentation
  changes;
- bare `qca` launches the official native TUI in the validation environment;
- the TUI discovers and completes the five-stage QuTiP workflow;
- CPU and available-GPU behavior are accurately reported;
- seeded and explicit hidden truth both work without truth disclosure;
- no push or other mutation occurred on GitHub.
