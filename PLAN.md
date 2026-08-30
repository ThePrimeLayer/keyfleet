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
- [ ] CI green on 3 OSes — workflow ready; runs on first push to GitHub
- [x] README quick start executed literally from a clean clone (2026-08-30: sync, check, lost, full test suite)
- [x] `uv build` wheel + sdist OK (data files packaged; wheel smoke-tested via `uvx --from`); CHANGELOG 0.1.0 section; tag `v0.1.0` (local — push after CI is green)
- [ ] PyPI publish (owner credentials / trusted publishing)

## Open questions (owner — brief §15)

1. **License**: Apache-2.0 (recommended) or MIT? *Proceeding with Apache-2.0.*
2. **Default policy numbers** `T0: 3, T1: 2, T2: 1` — keep? *Proceeding as proposed; they are schema defaults, overridable per ledger.*
3. **Name**: PyPI `keyfleet` is **free** (checked 2026-08-29, 404 on pypi.org/pypi/keyfleet/json). GitHub **org** `keyfleet` is taken (private/empty org, checked 2026-08-29) — fine if the repo lives under the owner's account; alternatives (`keyfleet-cli`, `key-fleet`) only needed if a dedicated org is wanted.

## Session log

<!-- - YYYY-MM-DD · harness · what changed · next: … · open: … -->
- 2026-08-29 · claude-code · M0 complete: scaffold (uv/hatchling/CI/pre-commit), pydantic schema + secret rejection + JSON schema, `validate` + `check` (min-keys), example ledger, 44 tests green · next: M1 (remaining checks, `lost`/`report`/`advisories`/`services`/`init`, bundled data files, `.age`) · open: §15 license / policy defaults / name (defaults in use; PyPI free, GitHub org taken)
- 2026-08-29 · claude-code · M1 complete: all 7 checks, `lost`/`report`/`advisories`/`services`/`init`, verified data files (32 services / 4 model families / 3 advisories), `.age` support, goldens, 138 tests + 4 age-skips, 100% cov on checks/impact · next: M2 (README + demo GIF, CONTRIBUTING/SECURITY, PyPI, tag v0.1.0) · open: none (owner confirmed §15 defaults)
- 2026-08-30 · claude-code · M2 code-complete: README + aha paragraph + demo.gif (generated from real output), CONTRIBUTING/SECURITY, v0.1.0 version + changelog, wheel built and smoke-tested from isolation, quick start verified from a clean clone, tag v0.1.0 local · next: owner creates GitHub repo + pushes (CI must go green), then PyPI publish + push tag · open: GitHub owner/repo for badges + schema $id; PyPI publish method
