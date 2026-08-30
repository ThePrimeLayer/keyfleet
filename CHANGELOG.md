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
- Weak-factor check: WARN for every factor a tier's policy warns against
  (default: sms and email on T0 accounts).
- Unregistered-spare check: WARN for spare keys registered on no account.
- Recovery-code pointer check: INFO for accounts in tiers listed in
  `policy.require_recovery_codes_for` (default T0+T1) that have no stored
  recovery-code pointer.
- `keyfleet advisories` — matches every key against the bundled advisory list
  (plus any ledger-local advisories) by vendor and firmware range; keys
  without `firmware:` are prompted to set it.
- `keyfleet services [--search NAME]` — prints the bundled service table.
- `keyfleet report [--md|--json]` — coverage matrix (accounts x keys with
  registration types), per-tier summary, and key utilization including
  discoverable-credential usage against known capacities.
- `keyfleet lost KEY_ID [--md]` — lost-key impact analysis and an ordered
  de-registration checklist (tier first, becomes-inaccessible first) with the
  registration nicknames to delete and each service's security-settings URL.
- Bundled reference data, every fact verified on the vendor's own page (or
  `null`, never guessed): `services.yaml` with 32 services (settings URLs,
  documented key limits, passkey support), `models.yaml` with
  discoverable-credential capacities per firmware (YubiKey 5 / Security Key
  series 25→100 at 5.7, Nitrokey 3 family), and `advisories.yaml` seeded with
  YSA-2024-02, YSA-2024-03, and YSA-2025-02. `docs/SERVICES.md` is generated
  from the services table.
