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
