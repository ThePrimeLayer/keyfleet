# Assumptions

External facts relied on but not verified on an authoritative page, with date
and link (AGENTS.md §9). Bundled-data facts (`models.yaml`, `services.yaml`,
`advisories.yaml`) carry `source_url`/`verified` per entry instead and only
appear here when a fact could **not** be verified.

- 2026-08-29 — No runtime-data assumptions yet; bundled data files land in M1.
- 2026-08-29 — Point-in-time observations used for scaffolding (all checked
  this day, may drift): ruff-pre-commit latest release v0.16.5 and gitleaks
  latest v8.30.1 (GitHub `releases/latest` API); `keyfleet` free on PyPI
  (HTTP 404 from https://pypi.org/pypi/keyfleet/json); GitHub org `keyfleet`
  exists but is private/empty (https://github.com/keyfleet);
  actions/checkout latest v7, astral-sh/setup-uv latest v10.
