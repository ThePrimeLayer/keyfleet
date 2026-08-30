# Contributing to keyfleet

Thanks for helping! The most valuable contribution by far is a **service
entry** — it takes ten minutes and makes `keyfleet lost` and `keyfleet check`
smarter for everyone.

## Add a service (the ten-minute PR)

1. Open the service's **own** documentation/help page about security keys or
   passkeys. Facts must come from a page on the vendor's domain — that page
   becomes `source_url`. No blog posts, no memory, no guessing.
2. Add an entry to [`src/keyfleet/data/services.yaml`](src/keyfleet/data/services.yaml),
   **alphabetical by id**:

   ```yaml
   example:
     name: "Example"
     security_settings_url: https://example.com/settings/security  # only if documented/linked; else null
     max_keys: null              # integer only if the page states a limit
     fido2_discoverable: true    # passkeys supported? true / false / null (page doesn't say)
     notes: "One short sentence from the page, in your own words."
     source_url: https://help.example.com/security-keys
     verified: 2026-08-30        # the day YOU read the page
   ```

   `null` never means "probably not" — it means *the page does not say*.
   A service with **no** security-key support at all is still a great entry:
   set `fido2_discoverable: false` and say so in `notes` (see `steam`).
3. Regenerate the table and run the data tests:

   ```bash
   uv run python scripts/gen_services_md.py
   ```

   ```bash
   uv run pytest tests/test_data_files.py -q
   ```

4. Commit as `data(services): add example`, one service per PR, and paste the
   sentence from the vendor page that supports each non-null fact into the PR
   description.

Corrections use the same rules — update `verified` to the day you re-checked.
`models.yaml` (key capabilities/capacities) and `advisories.yaml` (vendor
advisories with firmware ranges) follow the same source-cited pattern; see the
header comments in each file.

## Code contributions

```bash
uv sync --all-extras --dev
```

```bash
uv run pytest -q
```

```bash
uv run pre-commit run --all-files
```

- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `data:`, `chore:`);
  one logical change per commit; tests land in the same commit as the change.
- `checks.py` and `impact.py` stay pure (no I/O); rendering lives in
  `report.py`; every finding must tell the user what to *do*.
- Two hard rules, enforced by tests, not negotiable: **no network calls in
  runtime code** and **no storing secrets** (the validator must keep refusing
  anything that looks like one).
- After changing `model.py`, regenerate the JSON schema:
  `uv run python scripts/gen_schema.py`. After changing CLI output on
  purpose, regenerate goldens: `KEYFLEET_UPDATE_GOLDENS=1 uv run pytest -q`
  and review the diff.

Agent-assisted contributions are welcome; the repo's ground rules for that
live in [AGENTS.md](AGENTS.md).
