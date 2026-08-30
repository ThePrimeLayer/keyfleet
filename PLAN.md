# keyfleet — PLAN

Working plan for v0.1.0. Scope source of truth: `keyfleet-BRIEF.md`; process: `AGENTS.md`.
Do not rewrite milestones without owner agreement (AGENTS.md §9) — propose in chat first.

## Milestones

### M0 — Scaffold (brief §11)

- [ ] Repo scaffold: git init, pyproject (uv, hatchling, src layout), `.gitignore`, LICENSE (Apache-2.0 pending Q1), `CHANGELOG.md`, README stub, `.python-version`
- [ ] Tooling: `.pre-commit-config.yaml` (ruff v0.16.5 + gitleaks v8.30.1, exact pins), GitHub Actions CI on ubuntu/windows/macos
- [ ] Ledger schema in `model.py` (pydantic v2, `extra="forbid"`) + loader with which-file/which-id/which-field errors
- [ ] Secret rejection: field names (`secret`, `seed`, `pin`, `otp`, `code(s)`, …) and value shapes (`otpauth://`, long base32, digit-group codes)
- [ ] `schema/keyfleet.schema.json` generated from the models + sync test
- [ ] `keyfleet validate` (exit 0 valid / 1 invalid / 2 missing file or usage)
- [ ] `keyfleet check [--json]` with min-keys rule (distinct active|spare keys vs `policy.min_keys[tier]`); exit 1 on FAIL findings
- [ ] `keyfleet.example.yaml` (fictional; one deliberate T1 gap to demo a FAIL)
- [ ] Tests: model + fixtures, checks, CLI exit codes, no-network grep of `src/`, schema sync, non-ASCII label
- [ ] Batch §15 questions to owner (one message, defaults proposed)

### M1 — Core (brief §11)

- [ ] Remaining checks: lost/retired-key hygiene (FAIL), weak factors per tier (WARN), unregistered spare (WARN), discoverable-credential capacity vs `models.yaml` (INFO), missing recovery-code pointer (INFO)
- [ ] `keyfleet lost KEY_ID [--md]` — impact + ordered de-registration checklist with `services.yaml` links and registration nicknames
- [ ] `keyfleet report [--md|--json]` — coverage matrix, per-tier summary, key utilization
- [ ] `keyfleet advisories` — semantic firmware compare; unknown firmware → INFO
- [ ] `keyfleet services [--search NAME]` and `keyfleet init`
- [ ] Bundled data: `models.yaml`, `services.yaml` (≥30 services, verified `source_url` + `verified` dates, alphabetical), `advisories.yaml` (seed list) + data-integrity tests
- [ ] Generated `docs/SERVICES.md` from `services.yaml`
- [ ] Optional encrypted ledger: read `keyfleet.yaml.age` via `age` CLI, decrypt to memory only; test skipped when `age` absent
- [ ] Golden files for `check`/`report` output
- [ ] Cross-file validation note: warn (don't fail) when `account.service` is not in `services.yaml`

### M2 — Release (brief §11)

- [ ] README: hook, discoverable-vs-non-discoverable "aha" paragraph, install (`uvx keyfleet check`, `pipx install keyfleet`), badges, roadmap
- [ ] Demo GIF (`check` → FAIL → `lost yk-old` → checklist)
- [ ] `CONTRIBUTING.md` ("how to add a service") + `SECURITY.md`
- [ ] JSON schema published (add `$id` once repo URL is final)
- [ ] CI green on 3 OSes; README quick start executed literally from a clean clone
- [ ] `uv build` wheel OK; CHANGELOG release section; tag `v0.1.0`; PyPI publish

## Open questions (owner — brief §15)

1. **License**: Apache-2.0 (recommended) or MIT? *Proceeding with Apache-2.0.*
2. **Default policy numbers** `T0: 3, T1: 2, T2: 1` — keep? *Proceeding as proposed; they are schema defaults, overridable per ledger.*
3. **Name**: PyPI `keyfleet` is **free** (checked 2026-08-29, 404 on pypi.org/pypi/keyfleet/json). GitHub **org** `keyfleet` is taken (private/empty org, checked 2026-08-29) — fine if the repo lives under the owner's account; alternatives (`keyfleet-cli`, `key-fleet`) only needed if a dedicated org is wanted.

## Session log

<!-- - YYYY-MM-DD · harness · what changed · next: … · open: … -->
