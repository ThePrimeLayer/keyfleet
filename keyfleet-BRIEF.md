# keyfleet — Claude Code Project Brief

> **Status:** not started · **Owner:** (repo owner) · **Language:** Python 3.12+ · **License:** Apache-2.0 (confirm, see §15)
>
> **If you are Claude Code:** read this whole file, then follow §16. Write `PLAN.md` before coding.
> Tip for the owner: add a `CLAUDE.md` containing `@keyfleet-BRIEF.md` so this loads automatically.

---

## 1. Mission

A local-first ledger for **hardware security keys ↔ accounts ↔ credential types**, and a checker that turns it into answers: *Which accounts have only one key registered? What breaks if I lose this key? Which keys are affected by an advisory? Is this key near its passkey capacity?* No secrets are ever stored — only the map of what is registered where.

README hook: *"Your YubiKey can't tell you which accounts it's registered to. keyfleet can."*

## 2. Gap and why it will get stars

- Vendor guidance is unanimous: register a **backup key with every account**. Nothing tracks whether you actually did. Non-discoverable FIDO2/U2F registrations are not stored on the key, so no tool can enumerate them — a human-maintained ledger is the only way, and nobody has built the tooling around one.
- Audience: everyone with two or more keys (security engineers, sysadmins, crypto holders, journalists, families running a shared key set). Small but highly engaged; exactly the crowd that stars and contributes.
- Community dataset angle: `services.yaml` — a curated table of where each service's security-key settings live, how many keys it allows, and whether it supports FIDO2 discoverable credentials. That table alone earns stars and PRs.

## 3. Users and jobs-to-be-done

| User | Job |
|---|---|
| Multi-key individual | Know coverage gaps before a key is lost, not after |
| Family / small team admin | Track who holds which key and what it unlocks |
| Incident response (lost key) | Get an ordered de-registration checklist in seconds |
| Anyone with older keys | See which keys an advisory affects |

## 4. MVP scope (v0.1)

1. YAML ledger schema (§7) with validation and helpful errors.
2. `keyfleet check` — policy violations and coverage gaps.
3. `keyfleet lost <key-id>` — impact analysis + ordered de-registration checklist with links.
4. `keyfleet report --md` — coverage matrix (accounts × keys) and per-tier summary.
5. `keyfleet advisories` — match keys against a manually maintained advisory list (no fetching).
6. Bundled `services.yaml` (≥30 services to start) and `models.yaml` (vendor/model capabilities and discoverable-credential capacity).
7. Optional encrypted ledger: transparently read `keyfleet.yaml.age` if `age` CLI is available (decrypt to memory only).

## 5. Non-goals (v0.1)

- Storing recovery codes, TOTP seeds, PINs, or any secret (refuse to save fields named like secrets).
- Talking to any key hardware or vendor API (no `ykman` integration in v0.1; maybe v0.3 for reading model/firmware/serial).
- Web/PWA UI (v0.3 idea: static, local-storage-only PWA reusing the same schema).
- Auto-fetching advisories from vendor sites.

## 6. Tech stack (decided)

- Python 3.12+, `uv`, `src/` layout, `typer` for CLI, `rich` for tables, `pydantic` v2 for schema, `pyyaml`.
- `pytest`, `ruff`, `pre-commit` (ruff + pinned gitleaks), GitHub Actions matrix (ubuntu/windows/macos).
- Publish JSON Schema for the ledger (`schema/keyfleet.schema.json`) so editors get completion.

## 7. Data model (ledger YAML — example ships as `keyfleet.example.yaml`)

```yaml
version: 1
keys:
  - id: yk-a                       # short stable id, referenced by accounts
    label: "YubiKey 5C NFC (daily carry)"
    vendor: yubico                 # yubico | google | tillitis | nitrokey | solokeys | feitian | other
    model: "YubiKey 5C NFC"
    firmware: "5.7.1"              # optional; used for advisories + capacity
    serial: null                   # optional; ledger is local-only anyway
    interfaces: [usb-c, nfc]
    capabilities: [fido2, u2f, piv, oath, otp, openpgp]
    status: active                 # active | spare | lost | retired
    holder: "me"
    location: "keychain"
    acquired: 2025-03-01
accounts:
  - id: pw-manager
    service: bitwarden             # key into services.yaml (or "other")
    label: "Password manager (family)"
    tier: T0                       # T0 root of trust (password manager, primary email, registrar, phone carrier), T1 important, T2 nice-to-have
    registrations:
      - key: yk-a
        type: fido2-non-discoverable   # fido2-discoverable | fido2-non-discoverable | u2f | piv | oath-totp | yubico-otp | openpgp
        registered: 2025-03-02
        nickname: "primary"
    other_factors: [totp-app, recovery-codes]   # totp-app | sms | email | push | recovery-codes | synced-passkey
    recovery_codes: { stored: true, where: "vault/recovery" }   # a pointer, never the codes
    notes: ""
policy:
  min_keys: { T0: 3, T1: 2, T2: 1 }
  require_recovery_codes_for: [T0, T1]
  warn_factors: { T0: [sms, email] }        # weak factors that should not exist on T0
advisories:                                  # manual; ship a seed list with vendor URLs
  - id: YSA-2024-03
    vendor: yubico
    affects: { firmware_lt: "5.7" }
    summary: "Side-channel with physical access and lab equipment"
    url: https://www.yubico.com/support/security-advisories/ysa-2024-03/
```

`models.yaml` (bundled): per model → capabilities, `discoverable_capacity` (e.g., YubiKey 5 firmware < 5.7 = 25 passkeys, ≥ 5.7 = 100 — **verify from vendor docs** and cite in the file), interfaces.

`services.yaml` (bundled, community-extendable): `service → { name, security_settings_url, max_keys: int|null, fido2_discoverable: bool|null, notes }`. Seed with the majors (Google, Microsoft, Apple, GitHub, GitLab, Bitwarden, 1Password, Proton, AWS, Cloudflare, Namecheap, Fastmail, Dropbox, Coinbase, Kraken, Twitter/X, Facebook, Discord, Okta, Tailscale, Hetzner, DigitalOcean, Vultr, Backblaze, Nintendo, Steam? (no FIDO), etc.). Mark unknowns as `null`, never guess.

## 8. CLI contract

```
keyfleet validate [LEDGER]                 # schema + referential integrity (keys referenced exist, ids unique)
keyfleet check    [LEDGER] [--json]        # policy violations + gaps; exit 1 if any "fail" findings
keyfleet lost     KEY_ID [--md]            # impact + de-registration checklist
keyfleet report   [--md|--json]            # coverage matrix, per-tier summary, key utilization
keyfleet advisories                        # keys matching advisories
keyfleet services [--search NAME]          # print bundled service info
keyfleet init                              # write keyfleet.example.yaml + .gitignore entry
```

Sample `check` output:

```
keyfleet check — 3 keys (2 active, 1 spare) · 14 accounts

FAIL  T0 "Primary email (Google)" has 1 hardware key registered; policy requires 3
FAIL  Key yk-old is LOST but still registered on 4 accounts → run: keyfleet lost yk-old
WARN  T0 "Password manager" lists sms as a factor
WARN  Spare key yk-c is registered nowhere (a spare that isn't registered is not a backup)
INFO  yk-a: 61/100 discoverable credentials (ledger count) — plan capacity
INFO  2 accounts have no recovery-code pointer (T1 requires one)

2 fail, 2 warn, 2 info · exit 1
```

## 9. Core logic

- **Coverage**: per account, count registrations on keys with `status in {active, spare}`; compare to `policy.min_keys[tier]`.
- **Lost/retired hygiene**: any registration on a key with `status in {lost, retired}` is a FAIL (attacker could use it; de-register).
- **Lost impact** (`lost KEY`): for each account with a registration on KEY → new key count, whether it drops below policy, whether it becomes *inaccessible* (0 keys and no other factors), ordered by tier then by "becomes inaccessible first"; emit a checklist row with the service's security settings URL from `services.yaml` and the registration nickname (so the user knows which entry to delete in the service UI).
- **Capacity**: sum `fido2-discoverable` registrations per key vs `models.yaml` capacity (ledger-based estimate; note it can undercount).
- **Advisories**: semantic version compare on `firmware`; unknown firmware → INFO "set firmware to evaluate".
- **Weak factors**: `policy.warn_factors[tier]` intersection with `other_factors`.

## 10. Repo layout

```
.
├── README.md  LICENSE  CHANGELOG.md  SECURITY.md  CONTRIBUTING.md
├── pyproject.toml  uv.lock  .pre-commit-config.yaml  .github/workflows/ci.yml
├── schema/keyfleet.schema.json
├── src/keyfleet/{cli.py, model.py, checks.py, impact.py, report.py, data/models.yaml, data/services.yaml, data/advisories.yaml, crypto.py}
├── tests/{fixtures/*.yaml, test_model.py, test_checks.py, test_impact.py, test_report.py, test_services_data.py}
├── docs/{ASSUMPTIONS.md, SERVICES.md (generated), demo.gif}
├── keyfleet.example.yaml
└── PLAN.md
```

## 11. Milestones

- **M0 Scaffold** (½ day): skeleton, schema, `validate` + `check` with min-keys rule, tests.
- **M1 Core** (2 days): all checks, `lost`, `report`, `advisories`, bundled data files with tests that assert data integrity (unique ids, URLs well-formed, no `null` for majors), `.age` support.
- **M2 Release** (1 day): README + demo GIF, JSON schema published, PyPI, tag `v0.1.0`, `CONTRIBUTING.md` with "how to add a service".
- **v0.2**: `keyfleet add key|account` interactive prompts; import helpers (e.g., from a CSV).
- **v0.3**: optional `ykman`/`fido2` read-only integration to pull model/firmware/serial; static PWA.

## 12. Testing

- Fixture ledgers for each check (pass and fail cases); golden `check`/`report` outputs.
- Data tests: `services.yaml` entries have valid URLs (syntax only — no network), unique ids; `models.yaml` capacities are ints or null.
- `.age` test skipped when `age` binary is absent.
- Windows path/encoding test for YAML with non-ASCII labels.

## 13. Security and privacy constraints

- The ledger reveals which accounts exist and which keys guard them: treat as sensitive. `init` writes a `.gitignore` entry for `keyfleet.yaml`; README says to keep it in an encrypted location (password-manager document, `age`-encrypted file, or a private repo).
- Validation **rejects** fields that look like secrets (`code`, `codes`, `seed`, `secret`, `pin`, `otp` with values) with a clear message.
- No network calls at all in v0.1. No telemetry.

## 14. README and release checklist

- Hook + short explanation of *why* the key can't enumerate its registrations (discoverable vs non-discoverable credentials) — this paragraph is the "aha".
- Demo GIF: `check` → red FAIL → `lost yk-old` → checklist with links.
- Install: `uvx keyfleet check`, `pipx install keyfleet`.
- "Add your service" contribution guide; auto-generated `docs/SERVICES.md` table.
- Badges: CI, PyPI, license, schema. Roadmap listing PWA/`ykman`.

## 15. Decisions Claude Code may make alone vs. must ask

**Alone:** exact check wording, report layout, which 30 services to seed (verify URLs), schema field naming details.

**Must ask (one batched message before M0 ends):**
1. License: Apache-2.0 (recommended) or MIT?
2. Default policy numbers (`T0: 3, T1: 2, T2: 1`) — keep as proposed?
3. Name check on PyPI/GitHub for `keyfleet`; propose alternatives if taken.

## 16. Operating procedure for Claude Code

1. Read everything above; write `PLAN.md` (M0–M2 checkboxes); keep it updated.
2. Batch §15 questions into one message; proceed with M0 using recommended defaults.
3. Scaffold per §10; small conventional commits; `ruff` + `pytest` before each commit.
4. Implement checks test-first (fixture → failing test → code), one commit per check.
5. Verify every vendor fact you write into `models.yaml`/`advisories.yaml`/`services.yaml` against the vendor's official page; include a `source_url` field per entry; record uncertainties in `docs/ASSUMPTIONS.md`. Use `null` rather than a guess.
6. Never add network calls. Never persist secrets — enforce in validation and tests.
7. Definition of done for v0.1.0: §4 complete, CI green on 3 OSes, README quick start executed literally from a clean clone, CHANGELOG entry, tag, wheel builds.
8. Finish with a short report: shipped / assumed / next.
