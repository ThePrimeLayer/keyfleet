# keyfleet

> Your YubiKey can't tell you which accounts it's registered to. keyfleet can.

**Status: pre-release, under construction (v0.1 in progress).** The full README
lands with the v0.1.0 release; see `PLAN.md` for progress.

keyfleet keeps a local YAML ledger of your hardware security keys, the accounts
they are registered to, and the credential type of each registration — then
answers the questions the keys themselves can't: which accounts have only one
key, what breaks if a key is lost, which keys an advisory affects.

It stores **no secrets** (validation refuses anything that looks like one) and
makes **no network calls**.

## Quick start (from a clone, while pre-release)

```bash
uv sync --all-extras --dev
```

```bash
uv run keyfleet validate keyfleet.example.yaml
```

```bash
uv run keyfleet check keyfleet.example.yaml
```

The example ledger is fictional and contains one deliberate coverage gap so
`check` has something to show. Copy it to `keyfleet.yaml` (gitignored) and make
it yours. Editors pick up completion from `schema/keyfleet.schema.json`.

## Security posture

- The ledger reveals which accounts exist and which keys guard them — treat the
  file as sensitive: keep it in an encrypted location (password-manager
  document, `age`-encrypted file, or a private repo). `keyfleet.yaml` is
  gitignored here by default.
- keyfleet never stores recovery codes, TOTP seeds, PINs, or any secret, and
  refuses to load a ledger that appears to contain one.
- No network calls, no telemetry — enforced by tests.
