# Decisions

One short entry per non-obvious choice: context → decision → alternatives
considered (AGENTS.md §9). Newest at the bottom.

## 2026-08-29 — Runtime dependencies: typer, rich, pydantic v2, pyyaml

Mandated by brief §6; recorded here per AGENTS.md §5. Alternatives considered:
click/argparse (typer wraps click and adds type-hint ergonomics), plain
print/tabulate (rich gives tables + color + no-tty fallback), dataclasses +
jsonschema (pydantic v2 provides validation and JSON-schema generation in one),
ruamel.yaml (no round-trip editing need in v0.1; `yaml.safe_load` suffices).

## 2026-08-29 — Dev dependencies: pytest, ruff==0.16.5, pre-commit

Brief §6. ruff is pinned exactly and matched to the `.pre-commit-config.yaml`
rev (v0.16.5, latest on 2026-08-29) so `uv run ruff` and the hook can never
disagree about formatting; gitleaks hook pinned v8.30.1 (latest release).
pytest/pre-commit are floor-pinned; `uv.lock` holds the exact versions.

## 2026-08-29 — Build backend: hatchling

Context: need `uv build` wheels from a src layout. Decision: hatchling —
mature, minimal config, PEP 639 SPDX license support. Alternatives: uv_build
(younger, less documented), setuptools (more configuration for no gain).

## 2026-08-29 — Exit-code mapping for ledger load errors

AGENTS.md §5 fixes 0 = clean, 1 = FAIL findings, 2 = tool/usage error, but not
how load errors map per command. Decision:

- `validate`: invalid ledger content (YAML syntax, schema, integrity,
  secret-looking field) → **1** — judging the ledger is the command's job, so
  "invalid" is its FAIL result. Missing/unreadable file → **2**.
- every other command (`check`, later `lost`/`report`/…): any load failure →
  **2**, with a hint to run `keyfleet validate`. In `check`, exit 1 is reserved
  for FAIL findings on a valid ledger, so CI can tell "bad ledger" from
  "coverage gap".

## 2026-08-29 — Policy defaults live in the schema; partial min_keys merges

`policy` and all its fields are optional. Defaults are brief §7's proposal
(min_keys T0:3/T1:2/T2:1, recovery codes required for T0+T1, warn sms/email on
T0) — pending owner confirmation (§15 Q2). `min_keys` is a model with per-tier
defaults rather than a bare dict, so a partial override like `{T0: 5}` keeps
the defaults for T1/T2 instead of silently dropping their requirement.

## 2026-08-29 — Owner answers to brief §15 (confirmed)

The owner confirmed all recommended defaults in chat on 2026-08-29:
1. **License: Apache-2.0** (over MIT).
2. **Policy defaults kept**: `min_keys T0: 3, T1: 2, T2: 1` stay the schema
   defaults, overridable per ledger.
3. **Name: `keyfleet`** — free on PyPI (checked 2026-08-29); the GitHub org
   name is taken (private/empty) but the repo lives under the owner's account.

## 2026-08-29 — age identities via KEYFLEET_AGE_IDENTITY; informational commands exit 0

`.age` decryption shells out to the `age` CLI (decrypt to memory only). For
non-interactive use (tests, scripts) the identity file is taken from the
`KEYFLEET_AGE_IDENTITY` environment variable; otherwise age's own passphrase
prompt on the terminal is used. A CLI flag was considered and rejected for
v0.1: brief §8 fixes the command surface. Relatedly, `lost`, `report`,
`advisories`, and `services` are informational and always exit 0 on success
(2 on usage/load errors) — exit 1 stays reserved for `check`'s FAIL findings
and `validate`'s invalid-ledger result.

## 2026-08-29 — Capacity thresholds: INFO at ≥50%, WARN at ≥90%

Brief §9 gives no threshold; its sample shows 61/100 as INFO. Emitting on any
usage would be noise for small ledgers, so: INFO from half full (start
planning), WARN from 90% (act now). Constants in checks.py; revisit on
feedback.

## 2026-08-29 — Secret detection: name heuristics + value heuristics

Brief §13 requires rejecting secret-looking content. Decision: scan the raw
YAML before schema validation. Names: a field is refused when any `_`/`-`/space
separated segment is one of secret(s)/seed(s)/totp/otp/pin(s)/password/passwd/
code(s)/token(s) and the value is a non-empty scalar or list — a mapping value
is allowed (that is the `recovery_codes: {stored, where}` pointer form), and
`require_recovery_codes_for` (a schema field) is allowlisted. Values: refuse
`otpauth://` URIs, full-string base32 of ≥16 chars (TOTP seed shape), and
digit-group strings like `1234-5678-9012` (recovery-code shape). Best-effort by
design — gitleaks in pre-commit is the second net. Alternative considered:
entropy scoring (rejected: opaque false positives).
