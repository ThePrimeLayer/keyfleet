"""schema/keyfleet.schema.json must match the pydantic models exactly."""

from __future__ import annotations

import json

from conftest import REPO_ROOT

from keyfleet.model import ledger_json_schema


def test_schema_file_matches_models():
    schema_path = REPO_ROOT / "schema" / "keyfleet.schema.json"
    assert schema_path.is_file(), "schema/keyfleet.schema.json is missing"
    on_disk = json.loads(schema_path.read_text(encoding="utf-8"))
    assert on_disk == ledger_json_schema(), (
        "schema/keyfleet.schema.json is stale — regenerate with: "
        "uv run python scripts/gen_schema.py"
    )
