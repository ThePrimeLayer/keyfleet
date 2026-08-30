# keyfleet — Claude Code

@AGENTS.md

Shared rules live in `AGENTS.md` (imported above). This file adds only what is specific to working with Claude Code. Keep it under 60 lines; if a rule applies to every harness, move it to `AGENTS.md`.

## Orientation

- Start from `PLAN.md`. If it is missing, read `keyfleet-BRIEF.md` in full and create `PLAN.md` per the brief's §16 before touching code.
- The brief is deliberately **not** imported here: imports load on every launch, and the brief is only needed when a task touches something it specifies (schema, CLI surface, a check's logic, data files). Open the relevant section at that point.

## Working style

- When a decision needs the owner, present it as a short numbered fork with a recommended default, batch all such questions into one message, and keep working on unblocked tasks. No "shall I continue?" check-ins; end the turn when the requested slice is done or you are blocked.
- Push back plainly when the brief, `PLAN.md`, or a request is wrong or would breach an invariant in `AGENTS.md` §8 — before doing it, not after.
- Use plan mode (or a ≤10-line plan in chat) for anything that changes the ledger schema, a data-file format, or the CLI surface. Skip the plan for single-check or single-test changes.
- Do not rewrite `PLAN.md` milestones or the brief on your own; propose in chat, edit after agreement.

## Tooling

- `uv run …` for every Python invocation; never call `pip`, `python -m pip`, or a global interpreter.
- The owner works on both Windows (PowerShell) and macOS: prefer commands that are identical on both; use `pathlib` in code and in test helpers.
- When you need a fact about a key vendor, a service's security-key settings, or an advisory, read the vendor's/service's own page and record the URL and date in the data file (`source_url`, `verified`) or in `docs/ASSUMPTIONS.md`. Never fill a data entry from memory.

## Finishing a task or milestone

1. `uv run ruff check . && uv run ruff format . && uv run pytest -q`
2. Update `CHANGELOG.md` (Unreleased) for user-visible changes and append the session-log line to `PLAN.md`.
3. Summarize: shipped / assumed / next.

## Don'ts

- Don't add dependencies silently, touch the `gitleaks` or `ruff` pins outside a `chore(deps):` commit, add network calls, or commit `keyfleet.yaml`.
- Don't reformat or reorganize files the task doesn't require.
