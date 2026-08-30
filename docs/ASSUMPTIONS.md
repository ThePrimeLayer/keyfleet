# Assumptions

External facts relied on but not verified on an authoritative page, with date
and link (AGENTS.md §9). Bundled-data facts (`models.yaml`, `services.yaml`,
`advisories.yaml`) carry `source_url`/`verified` per entry instead and only
appear here when a fact could **not** be verified.

- 2026-08-29 — Security Key Series discoverable capacity (25 pre-5.7 / 100 at
  5.7+): the YubiKey tech manual states the 25 figure for "YubiKeys in the
  5 Series" (yk5-apps-fido.html) and the 100 figure for firmware 5.7
  (yk5-firmware-5.7.html). The Security Key Series runs the same firmware
  line, so `models.yaml` applies the same numbers to it; Yubico does not spell
  the figures out for that series on the fetched pages.
- 2026-08-29 — `services.yaml` facts researched via subagents that fetched
  each vendor's page and returned verbatim quotes; four numeric limits (Apple
  6, AWS 8, Nintendo 10 passkeys, Discord 16) were independently re-verified
  by a second fetch. Discord's help center blocks plain fetchers (HTTP 403);
  its quote comes from an in-session browser read of the same URL.
- 2026-08-29 — Point-in-time observations used for scaffolding (all checked
  this day, may drift): ruff-pre-commit latest release v0.16.5 and gitleaks
  latest v8.30.1 (GitHub `releases/latest` API); `keyfleet` free on PyPI
  (HTTP 404 from https://pypi.org/pypi/keyfleet/json); GitHub org `keyfleet`
  exists but is private/empty (https://github.com/keyfleet);
  actions/checkout latest v7, astral-sh/setup-uv latest v10.
