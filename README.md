# keyfleet

> Your YubiKey can't tell you which accounts it's registered to. keyfleet can.

[![ci](https://github.com/ThePrimeLayer/keyfleet/actions/workflows/ci.yml/badge.svg)](https://github.com/ThePrimeLayer/keyfleet/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/keyfleet)](https://pypi.org/project/keyfleet/)
[![Python](https://img.shields.io/pypi/pyversions/keyfleet)](https://pypi.org/project/keyfleet/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

keyfleet is a local-first CLI that keeps a small YAML ledger of your hardware
security keys, the accounts they are registered to, and the credential type of
each registration — then answers the questions the keys themselves can't:

- Which accounts have only one key registered?
- What breaks if I lose *this* key — and where do I go to de-register it?
- Which of my keys does that vendor advisory affect?
- How close is this key to its passkey capacity?

It stores **no secrets** (validation refuses anything that looks like one) and
makes **no network calls, ever** — both enforced by tests.

![keyfleet demo: check finds a lost key still registered, lost prints the ordered de-registration checklist](https://raw.githubusercontent.com/ThePrimeLayer/keyfleet/main/docs/demo.gif)

## Why a ledger? Your key literally cannot tell you.

FIDO2 has two kinds of credentials. **Discoverable credentials** (passkeys)
live on the key — it has a fixed number of slots, and tools can list them.
But the classic security-key registration — U2F, and most "add a security
key" 2FA flows — is **non-discoverable**: the key stores *nothing* per
account. The service keeps a credential ID that only your key can use, and
the key just answers challenges with it. No software can enumerate those
registrations from the hardware — not `ykman`, nothing — because the list
does not exist anywhere except across the services themselves.

So the only complete map of what your keys unlock is the one you maintain.
Every vendor's advice is to register a **backup key with every account**;
nothing tracks whether you actually did. keyfleet is that map, plus the
checker that turns it into answers.

## Quick start

Once v0.1.0 is on PyPI, no install needed:

```bash
uvx keyfleet init
```

(or `pipx install keyfleet`). From a clone, today:

```bash
uv sync --all-extras --dev
```

```bash
uv run keyfleet check keyfleet.example.yaml
```

`keyfleet init` drops a fictional example ledger next to you and makes sure
`.gitignore` covers `keyfleet.yaml`. Copy `keyfleet.example.yaml` to
`keyfleet.yaml`, make it yours, and from then on it's just `keyfleet check`.

```text
keyfleet check — 4 keys (2 active, 1 spare, 1 lost) · 5 accounts

FAIL  T0 "Primary email (Google)" has 1 hardware key registered; policy requires 3
FAIL  Key yk-old is LOST but still registered on 3 accounts → run: keyfleet lost yk-old
WARN  T0 "Primary email (Google)" lists sms as a factor
INFO  T1 "Code hosting (GitHub)" has no recovery-code pointer (policy requires recovery codes for T1)

2 fail, 1 warn, 1 info · exit 1
```

That `keyfleet lost yk-old` prints the incident checklist: every affected
account ordered by tier (the ones that become **inaccessible** first), which
registration nickname to delete, and the service's security-settings URL —
straight from the bundled, source-cited services table.

## Commands

| Command | What it does |
|---|---|
| `keyfleet validate [LEDGER]` | Schema + referential integrity + secret rejection. Exit 0/1/2. |
| `keyfleet check [LEDGER] [--json]` | Policy violations and coverage gaps; exit 1 on any FAIL. |
| `keyfleet lost KEY_ID [LEDGER] [--md]` | Impact analysis + ordered de-registration checklist. |
| `keyfleet report [LEDGER] [--md\|--json]` | Coverage matrix, per-tier summary, key utilization. |
| `keyfleet advisories [LEDGER]` | Keys matching vendor advisories by firmware range. |
| `keyfleet services [--search NAME]` | The bundled service table. |
| `keyfleet init` | Example ledger + `.gitignore` entry. |

The checks: minimum keys per account tier (default T0:3, T1:2, T2:1 —
override per ledger), registrations still sitting on lost/retired keys,
weak factors on sensitive tiers (default: sms/email on T0), spares registered
nowhere, missing recovery-code *pointers* (never the codes), passkey-slot
usage against known model capacities, and service-id typos.

## The ledger

```yaml
keys:
  - id: yk-blue
    label: "Blue YubiKey 5C NFC — daily carry"
    vendor: yubico
    model: "YubiKey 5C NFC"
    firmware: "5.7.1"
    status: active            # active | spare | lost | retired
accounts:
  - id: email-primary
    service: google           # keys into the bundled services.yaml
    label: "Primary email (Google)"
    tier: T0                  # T0 root of trust · T1 important · T2 nice-to-have
    registrations:
      - { key: yk-blue, type: fido2-discoverable, nickname: blue-daily }
    other_factors: [totp-app, recovery-codes]
    recovery_codes: { stored: true, where: "sealed envelope" }   # a pointer, never the codes
```

Full shape: [keyfleet.example.yaml](keyfleet.example.yaml). Editors get
completion from [schema/keyfleet.schema.json](schema/keyfleet.schema.json)
(VS Code: map it to `keyfleet*.yaml` under `yaml.schemas`).

## The services dataset

[`services.yaml`](src/keyfleet/data/services.yaml) ships knowledge about 32
services: where the security-key settings live, the documented maximum number
of keys, and whether passkeys are supported — every fact read from the
service's own page, with `source_url` and a `verified` date, and `null`
where the vendor documents nothing (never a guess). Browse it in
[docs/SERVICES.md](docs/SERVICES.md); add your service via
[CONTRIBUTING.md](CONTRIBUTING.md) — those PRs are the easiest way to help.

## Encrypted ledgers

The ledger reveals which accounts exist and which keys guard them — treat it
as sensitive. Keep it as a password-manager document, in a private repo, or
[age](https://age-encryption.org)-encrypted: every command transparently
reads `keyfleet.yaml.age` (decrypted to memory only, never to disk). Set
`KEYFLEET_AGE_IDENTITY` to an identity file for non-interactive use.

## Security posture

- No secrets, ever: validation refuses fields or values that look like
  recovery codes, TOTP seeds, PINs, or OTP secrets, with tests to keep it so.
- No network calls in runtime code (a test greps the imports), no telemetry.
- `keyfleet.yaml` is gitignored here and by `keyfleet init`.
- See [SECURITY.md](SECURITY.md) for reporting.

## Roadmap

- **v0.2** — `keyfleet add key|account` interactive prompts; CSV import helpers.
- **v0.3** — optional read-only `ykman`/`fido2` integration to pull
  model/firmware/serial; a static, local-storage-only PWA on the same schema.

## License

Apache-2.0 — see [LICENSE](LICENSE).
