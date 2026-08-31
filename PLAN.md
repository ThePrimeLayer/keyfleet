# keyfleet — PLAN

Working plan for v0.1.0. Scope source of truth: `keyfleet-BRIEF.md`; process: `AGENTS.md`.
Do not rewrite milestones without owner agreement (AGENTS.md §9) — propose in chat first.

## Milestones

### M0 — Scaffold (brief §11) — **done 2026-08-29**

- [x] Repo scaffold: git init, pyproject (uv, hatchling, src layout), `.gitignore`, LICENSE (Apache-2.0 pending Q1), `CHANGELOG.md`, README stub, `.python-version`
- [x] Tooling: `.pre-commit-config.yaml` (ruff v0.16.5 + gitleaks v8.30.1, exact pins; all hooks run green), GitHub Actions CI on ubuntu/windows/macos (not yet exercised — no remote)
- [x] Ledger schema in `model.py` (pydantic v2, `extra="forbid"`) + loader with which-file/which-id/which-field errors
- [x] Secret rejection: field names (`secret`, `seed`, `pin`, `otp`, `code(s)`, …) and value shapes (`otpauth://`, long base32, digit-group codes)
- [x] `schema/keyfleet.schema.json` generated from the models + sync test
- [x] `keyfleet validate` (exit 0 valid / 1 invalid / 2 missing file or usage)
- [x] `keyfleet check [--json]` with min-keys rule (distinct active|spare keys vs `policy.min_keys[tier]`); exit 1 on FAIL findings
- [x] `keyfleet.example.yaml` (fictional; one deliberate T1 gap to demo a FAIL)
- [x] Tests: model + fixtures, checks, CLI exit codes, no-network grep of `src/`, schema sync, non-ASCII label (44 passing)
- [x] Batch §15 questions to owner (one message, defaults proposed — see Open questions)

### M1 — Core (brief §11) — **done 2026-08-29**

- [x] Remaining checks: lost/retired-key hygiene (FAIL), weak factors per tier (WARN), unregistered spare (WARN), discoverable-credential capacity vs `models.yaml` (INFO ≥50% / WARN ≥90%), missing recovery-code pointer (INFO)
- [x] `keyfleet lost KEY_ID [--md]` — impact + ordered de-registration checklist with `services.yaml` links and registration nicknames
- [x] `keyfleet report [--md|--json]` — coverage matrix, per-tier summary, key utilization
- [x] `keyfleet advisories` — firmware range compare; unknown firmware → set-firmware prompt
- [x] `keyfleet services [--search NAME]` and `keyfleet init`
- [x] Bundled data: `models.yaml` (4 families), `services.yaml` (32 services, verified `source_url` + `verified` dates, alphabetical), `advisories.yaml` (3 Yubico advisories) + data-integrity tests
- [x] Generated `docs/SERVICES.md` from `services.yaml` (+ freshness test)
- [x] Optional encrypted ledger: read `keyfleet.yaml.age` via `age` CLI, decrypt to memory only; round-trip tests skip when `age` absent (CI ubuntu installs it)
- [x] Golden files for `check` (terminal + JSON), `report --md`, `lost --md`
- [x] Cross-file check: WARN when `account.service` is not in `services.yaml` ("other" exempt)
- Coverage on `checks.py` + `impact.py`: 100% (target ≥85%)

### M2 — Release (brief §11) — **code-complete 2026-08-30; publish steps await the owner's remote/credentials**

- [x] README: hook, discoverable-vs-non-discoverable "aha" paragraph, install (`uvx`/`pipx`), badges (OWNER placeholder), roadmap
- [x] Demo GIF (`check` → FAIL → `lost yk-old` → checklist) — real output rendered by `scripts/gen_demo_gif.py`
- [x] `CONTRIBUTING.md` ("the ten-minute service PR") + `SECURITY.md`
- [x] JSON schema shipped in repo + sdist — `$id` still pending the final repo URL (owner)
- [x] CI green on 3 OSes (2026-08-30, run 33301094202; ubuntu ran the age round-trip: 142 passed, 0 skipped)
- [x] README quick start executed literally from a clean clone (2026-08-30: sync, check, lost, full test suite)
- [x] `uv build` wheel + sdist OK (data files packaged; wheel smoke-tested via `uvx --from`); CHANGELOG 0.1.0 section; tag `v0.1.0` (local — push after CI is green)
- [x] PyPI publish — 2026-08-30 via trusted publishing (release.yml run on tag push, attestations uploaded); `uvx --from keyfleet==0.1.0` verified from a fresh env; GitHub release created

## Open questions (owner — brief §15)

1. **License**: Apache-2.0 (recommended) or MIT? *Proceeding with Apache-2.0.*
2. **Default policy numbers** `T0: 3, T1: 2, T2: 1` — keep? *Proceeding as proposed; they are schema defaults, overridable per ledger.*
3. **Name**: PyPI `keyfleet` is **free** (checked 2026-08-29, 404 on pypi.org/pypi/keyfleet/json). GitHub **org** `keyfleet` is taken (private/empty org, checked 2026-08-29) — fine if the repo lives under the owner's account; alternatives (`keyfleet-cli`, `key-fleet`) only needed if a dedicated org is wanted.

## Session log

<!-- - YYYY-MM-DD · harness · what changed · next: … · open: … -->
- 2026-08-29 · claude-code · M0 complete: scaffold (uv/hatchling/CI/pre-commit), pydantic schema + secret rejection + JSON schema, `validate` + `check` (min-keys), example ledger, 44 tests green · next: M1 (remaining checks, `lost`/`report`/`advisories`/`services`/`init`, bundled data files, `.age`) · open: §15 license / policy defaults / name (defaults in use; PyPI free, GitHub org taken)
- 2026-08-29 · claude-code · M1 complete: all 7 checks, `lost`/`report`/`advisories`/`services`/`init`, verified data files (32 services / 4 model families / 3 advisories), `.age` support, goldens, 138 tests + 4 age-skips, 100% cov on checks/impact · next: M2 (README + demo GIF, CONTRIBUTING/SECURITY, PyPI, tag v0.1.0) · open: none (owner confirmed §15 defaults)
- 2026-08-30 · claude-code · M2 code-complete: README + aha paragraph + demo.gif (generated from real output), CONTRIBUTING/SECURITY, v0.1.0 version + changelog, wheel built and smoke-tested from isolation, quick start verified from a clean clone, tag v0.1.0 local · next: owner creates GitHub repo + pushes (CI must go green), then PyPI publish + push tag · open: GitHub owner/repo for badges + schema $id; PyPI publish method
- 2026-08-30 · claude-code · Published: repo live at github.com/ThePrimeLayer/keyfleet, badges/$id/urls point there, release.yml (trusted publishing) added, setup-uv pinned v10.0.1 after a missing-floating-tag CI failure, CI green on all 3 OSes (age round-trip exercised) · next: owner logs into PyPI → register pending publisher → push v0.1.0 tag → verify on PyPI + GitHub release · open: PyPI login (browser tab waiting)
- 2026-08-30 · claude-code · v0.1.0 SHIPPED: PyPI pending publisher registered (owner logged in, form submitted in-browser), tag pushed, release workflow published wheel+sdist with attestations, installed+ran via uvx from PyPI, GitHub release created · next: v0.2 ideas (add key|account prompts, CSV import) when the owner wants them · open: none
- 2026-08-30 · claude-code · v0.1.1 SHIPPED: owner hit `uvx keyfleet init` traceback in C:\Windows\System32 — init now exits 2 with a cd hint and absolute paths in messages; fix verified from System32 against the published wheel; CI green, released via tag · next: v0.2 when wanted · open: none
- 2026-08-31 · claude-code · feat (owner picked v0.2 item 1): `keyfleet init [DIRECTORY]` — target dir created if missing, `~` expanded (PowerShell passes it literally), clean exit-2 message on unwritable target, cd hint in the Next line; +4 tests (148 green), README/CHANGELOG updated; on branch claude/project-status-next-steps-6z68p8 · next: owner merges, then release (v0.2.0) when wanted · open: none
- 2026-08-31 · claude-code · v0.2.0 staged: PR #1 merged after CI green on 3 OSes (feature + `chore: release v0.2.0` on main); session sandbox denied the `v0.2.0` tag push (403, branch-scoped credentials), so the tag/publish step passes to the owner · next: owner publishes GitHub release with new tag `v0.2.0` targeting main (creates the tag → release.yml → PyPI), then verify `uvx --from keyfleet==0.2.0` · open: none
- 2026-08-31 · claude-code · v0.2.0 SHIPPED: owner published the GitHub release → tag → release.yml run 33374864637 green (trusted publishing, wheel+sdist); PyPI serves 0.2.0 as latest, verified from a clean env via uvx (`init DIRECTORY` + `validate`) · next: v0.2/v0.3 ideas (add key|account prompts, CSV import) when wanted · open: none
- 2026-08-31 · claude-code · docs: owner got stuck post-init (bare `keyfleet` not on PATH under uvx; passed folder not file to `check`) — README quick start rewritten as a numbered nothing-to-first-report walkthrough (uvx prefix rule, PowerShell + POSIX blocks, file-not-folder, uvx cache gotcha) and init's closing hint is now uvx-aware; PR #2 rebase-merged after CI green on 3 OSes · next: init-hint fix ships with the next release; v0.2/v0.3 features when wanted · open: none
