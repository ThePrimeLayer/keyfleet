# AGENTS.md — keyfleet

Instructions for any coding agent working in this repository (Codex, Cursor, Copilot, Cline/Kilo, Claude Code via `CLAUDE.md`). Explicit instructions from the user override this file. This file is the single source of truth for **how to work here**; `keyfleet-BRIEF.md` is the source of truth for **what to build**. If they conflict on scope, the brief wins; on process, this file wins.

## 1. What this project is

`keyfleet` is a local-first Python CLI that keeps a YAML ledger of hardware security keys ↔ accounts ↔ credential types and reports coverage gaps, lost-key impact, capacity, and advisories. It stores **no secrets** and makes **no network calls**. Full specification: `keyfleet-BRIEF.md` — read it completely before your first change, then consult it by section (§7 data model, §8 CLI, §9 logic, §15 open decisions).

## 2. Session start (every session, every harness)

1. If `PLAN.md` exists, read it first: milestones, open questions, and the session log tell you where the last agent stopped. If it does not exist, read the brief and create `PLAN.md` per brief §16.
2. Run `git status` and `git log --oneline -15` to orient.
3. Work in small steps. Before ending, append a session-log line to `PLAN.md` (format in §9).

## 3. Commands

| Task | Command |
|---|---|
| Set up environment | `uv sync --all-extras --dev` |
| Run the CLI | `uv run keyfleet --help` |
| Tests (all / one file) | `uv run pytest -q` / `uv run pytest tests/test_checks.py -q` |
| Lint + format | `uv run ruff check . && uv run ruff format .` |
| All hooks | `uv run pre-commit run --all-files` |
| Build wheel | `uv build` |

Always prefix with `uv run`. Never `pip install` into a global/system Python. Commands are identical in PowerShell on Windows; write cross-platform code (`pathlib`, no shell one-liners in library code).

## 4. Repository map

```
src/keyfleet/          cli.py (typer) · model.py (pydantic) · checks.py, impact.py (pure functions) · report.py (rich/markdown/json) · crypto.py (optional age decryption) · data/{models,services,advisories}.yaml
schema/                keyfleet.schema.json (generated from the pydantic models; regenerate when model.py changes)
tests/                 fixtures/*.yaml · one test module per check · data-integrity tests
docs/                  ASSUMPTIONS.md (unverified facts) · DECISIONS.md (choices + rationale) · SERVICES.md (generated)
keyfleet.example.yaml  fictional example ledger; the only ledger ever committed
PLAN.md                milestones, open questions, session log
CHANGELOG.md           Keep a Changelog format; add to "Unreleased" as you go
```

## 5. Code conventions

- Python 3.12+, full type hints, `pydantic` v2 models in `model.py`, `typer` CLI in `cli.py`, `rich` for terminal output, `yaml.safe_load` only.
- `checks.py` and `impact.py` are **pure**: they take the loaded ledger model and return findings; no file or terminal I/O inside them.
- Exit codes: `0` clean, `1` findings at FAIL level, `2` tool/usage error. Every finding carries an actionable message and, where possible, a link from `services.yaml`.
- Errors for bad ledgers must say *which file, which key/account id, which field* and how to fix it.
- Use `logging`, not `print`, outside the report layer. No global mutable state.
- Keep modules under ~400 lines; split by responsibility, not by size.
- Do not add a dependency without a line in `docs/DECISIONS.md` (what, why, alternative considered).

## 6. Data files (`src/keyfleet/data/*.yaml`)

- Every entry has `source_url` and `verified: YYYY-MM-DD`. If a fact cannot be verified on the vendor's or service's own page, write `null` — never guess.
- `models.yaml`: capabilities, interfaces, discoverable-credential capacity per model/firmware.
- `services.yaml`: security-settings URL, max keys allowed, discoverable-credential support. Keep entries alphabetical by id.
- `advisories.yaml`: vendor advisories with `affects` rules (firmware ranges). Summaries in your own words; link the advisory.
- Data-integrity tests must pass after any edit (unique ids, valid URL syntax, ints or null for capacities). Regenerate `docs/SERVICES.md` when `services.yaml` changes.

## 7. Testing

- `pytest`; fixtures under `tests/fixtures/`; one module per check with positive and negative cases; golden files for `check`/`report` output.
- Tests never touch the network and never depend on the `age` binary (skip that test when it is absent).
- Must pass on Linux, macOS, and Windows (CI runs all three): use `tmp_path`, `pathlib`, UTF-8 explicitly.
- Add or update tests in the same commit as the behavior change. Target ≥85% coverage on `checks.py` and `impact.py`.

## 8. Security and privacy invariants (non-negotiable)

1. **No network calls in runtime code.** A test greps `src/` for `httpx`, `requests`, `urllib`, `socket`, `aiohttp` and fails on any import.
2. **No secrets in the ledger.** Validation rejects fields or values that look like recovery codes, TOTP seeds, PINs, or OTP secrets, with a clear message. Tests cover this.
3. **Never commit a real ledger.** `keyfleet.yaml` and `*.age` decrypted output are gitignored; only `keyfleet.example.yaml` (fictional) is committed.
4. **No telemetry, ever.**
5. **Supply chain:** `.pre-commit-config.yaml` pins `ruff` and `gitleaks` to exact versions; do not change pins except in a dedicated `chore(deps):` commit.
6. If a request would violate any of the above, stop and say so instead of complying.

## 9. Workflow and git

- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`. One logical change per commit; run `ruff` and `pytest` before committing.
- Small changes go directly on `main`. Anything that changes the ledger schema, a data-file format, or the CLI surface goes on a `feat/<topic>` branch with a short PR description (even if the owner merges it alone).
- Never force-push `main` or rewrite published history.
- `CHANGELOG.md`: add a bullet under **Unreleased** in the same commit as a user-visible change.
- `docs/ASSUMPTIONS.md`: record every external fact you relied on but could not verify (vendor capacities, service limits, API details) with a date and a link.
- `docs/DECISIONS.md`: one short entry per non-obvious choice (dependency, schema shape, threshold): context → decision → alternatives.
- **No churn.** Do not reformat, rename, or reorganize files that the task does not require. Do not rewrite `PLAN.md` milestones or the brief; propose changes in chat and edit only after agreement.
- Session log (append to the end of `PLAN.md`):
  `- 2026-08-29 · <harness> · <what changed, 1 line> · next: <1 line> · open: <question or "none">`

## 10. Decisions that require the owner

From brief §15: license (Apache-2.0 recommended), default policy numbers (`T0: 3, T1: 2, T2: 1`), and the package/repo name if `keyfleet` is taken on PyPI/GitHub. Ask these **once, in a single batched message**, propose a default for each, and continue with the recommended default on anything non-blocking. Record the answers in `docs/DECISIONS.md`. Do not ask questions the brief or this file already answers.

## 11. Definition of done for v0.1.0

Everything in brief §4 shipped; CI green on all three OSes; the README quick start executed literally from a clean clone; `CHANGELOG.md` entry; git tag `v0.1.0`; `uv build` succeeds. When a milestone or the release is complete, report: what shipped, what is assumed (link `docs/ASSUMPTIONS.md`), what is next.

## 12. Harness notes

- **Claude Code** reads `CLAUDE.md`, which imports this file. Put shared rules here, not there.
- **Codex** reads this file directly (keep it under the 32 KiB cap; no `AGENTS.override.md` is used in this repo).
- **Cursor** reads `AGENTS.md` natively; add `.cursor/rules/*.mdc` only for glob-scoped extras, never for rules that belong here.
- **GitHub Copilot** reads `AGENTS.md`; no separate `copilot-instructions.md` is maintained.
- **Other harnesses** that do not discover `AGENTS.md`: point their rules file at this one (a one-line "Read and follow AGENTS.md" is enough). Do not fork the content.
