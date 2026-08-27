# Sumcheck NoC rules

Canonical spec: docs/sumcheck_spec.md
Current task: tasks/<phase>.md
State: SUMCHECK_STATUS.md

- Work only on the current phase.
- Inspect actual gem5 APIs; never guess from another version.
- Preserve existing Ring/Wormhole and unrelated changes.
- No destructive git operations.
- Do not commit, push, merge, rebase, amend, or force-push.
- Aggregation must eject → controller → reinject.
- Never weaken VC_U/VC_D enforcement to make tests pass.
- Never present reference/static results as measured gem5 results.
- Unsupported routing cases should assert/fatal rather than silently choose.
- Before finishing, run relevant tests and update SUMCHECK_STATUS.md.

TOKEN / OUTPUT DISCIPLINE:
- Do not read the full spec unless necessary; read only task-relevant sections.
- Do not cat large logs, stats, JSONL traces, or generated outputs.
- Redirect verbose build/test output to files.
- On success inspect exit code + concise summary.
- On failure inspect grep/tail or the smallest relevant excerpt.
- Avoid repeated full-repo searches once locations are known.