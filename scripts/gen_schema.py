"""Regenerate schema/keyfleet.schema.json from the pydantic models.

Usage: uv run python scripts/gen_schema.py

Run after any change to src/keyfleet/model.py —
tests/test_schema_sync.py fails while the checked-in file is stale.
"""

from __future__ import annotations

import json
from pathlib import Path

from keyfleet.model import ledger_json_schema

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "keyfleet.schema.json"


def main() -> None:
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(json.dumps(ledger_json_schema(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
