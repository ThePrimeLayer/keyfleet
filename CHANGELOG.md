# Changelog

All notable, user-visible changes to keyfleet are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- YAML ledger schema (keys ↔ accounts ↔ registrations, policy, advisories)
  with strict validation, referential-integrity checks, and errors that name
  the file, the offending key/account id, and the field.
- Secret rejection: a ledger containing anything that looks like a recovery
  code, TOTP seed, PIN, or OTP secret (by field name or value shape) is
  refused with an explanation — keyfleet stores pointers, never secrets.
- `keyfleet validate [LEDGER]` — exit 0 valid, 1 invalid, 2 missing file.
- Published JSON Schema at `schema/keyfleet.schema.json` for editor
  completion, generated from the models.
- Fictional example ledger `keyfleet.example.yaml`.
- `keyfleet check [LEDGER] [--json]` with the min-keys coverage rule: FAIL for
  every account holding fewer active/spare keys than `policy.min_keys[tier]`
  (defaults T0:3, T1:2, T2:1); lost/retired keys never count. Exit 1 when any
  FAIL finding exists.
- Lost/retired hygiene check: FAIL for every lost or retired key that is still
  registered on any account, pointing at `keyfleet lost KEY` for the
  de-registration checklist.
