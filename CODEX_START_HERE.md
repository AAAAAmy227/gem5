# Codex Start Here — Sumcheck NoC

This bundle is designed to be copied/extracted into the **root of the existing gem5/Garnet repository**.

## First Codex run

Ask Codex to execute only Phase 00:

```text
Work directly in the current repository and execute tasks/00_recon.md.
Read AGENTS.md and SUMCHECK_STATUS.md first, then follow the task exactly.
Do not begin Phase 01 implementation in this run.
Before finishing, update SUMCHECK_STATUS.md with exact commands, evidence, Git/checkpoint state, blockers, and the next action.
Do not commit or push unless I explicitly authorize it.
```

## Later implementation runs

After a phase passes, start a fresh Codex session with the next task, for example:

```text
Continue the Sumcheck NoC project in this repository.
Read AGENTS.md and SUMCHECK_STATUS.md first, then execute tasks/01_topology_fixed.md only.
Follow its acceptance gates and update SUMCHECK_STATUS.md before finishing.
Do not commit or push unless I explicitly authorize it.
```

Repeat for phases 02–05.

## Intended engineering workflow

```text
00 recon/API map
    ↓
01 topology + fixed routing
    ↓
phase acceptance gates
    ↓
review diff + status
    ↓
checkpoint commit/push if explicitly authorized
    ↓
02 adaptive + VC + CDG
    ↓
...
```

The important boundary is:

```text
phase implementation ≠ automatic commit
phase PASS ≠ automatic push
push ≠ Pull Request
PR ≠ merge
```

Each Git write action requires the authorization described in `AGENTS.md`.

## Recommended checkpoint workflow

When a phase is validated, first let Codex stop with:

```text
Phase status: PASS
Checkpoint state: READY FOR CHECKPOINT
```

Then review the diff yourself or with a separate reviewer.

If you want Codex to create the checkpoint commit, give a separate explicit instruction such as:

```text
The current phase has been reviewed. Create the phase checkpoint commit now.

Read AGENTS.md and SUMCHECK_STATUS.md first.
Re-run or confirm the phase-required tests if needed, inspect git status and the staged diff,
stage only files belonging to this phase, update SUMCHECK_STATUS.md, and create one coherent
checkpoint commit following the `sumcheck: ...` commit-message convention.

Do not push yet.
Do not amend, rebase, squash, or touch unrelated changes.
```

If you then want it pushed:

```text
Push the current validated Sumcheck checkpoint to the current feature branch.

Read AGENTS.md and SUMCHECK_STATUS.md first.
Verify the current branch, remotes, upstream state, and exact commit before pushing.
Never push main/master and never force-push.
If the intended remote/branch is ambiguous, do not guess; stop and report the state.
After a successful push, update SUMCHECK_STATUS.md with the pushed commit and upstream.
Do not create a Pull Request.
```

## Suggested phase checkpoint subjects

Use these as examples, not mandatory literal strings:

```text
sumcheck: add hierarchy topology and fixed routing
sumcheck: enforce adaptive U/D routing and VC allocation
sumcheck: add causal workload replay and aggregation
sumcheck: add baselines and experiment scripts
sumcheck: finalize regressions and evaluation evidence
```

For an explicitly requested partial checkpoint:

```text
sumcheck: checkpoint partial adaptive routing
```

Do not use a success-sounding message for work whose acceptance gates have not passed.

## Intended project flow

```text
00 recon/API map
    ↓
01 topology + fixed routing
    ↓
02 adaptive + VC + CDG
    ↓
03 causal workload
    ↓
04 baselines + experiments
    ↓
05 final audit/regression
```

`docs/sumcheck_spec.md` remains the complete canonical project specification. The short task files control what the agent should implement **in the current run**.
