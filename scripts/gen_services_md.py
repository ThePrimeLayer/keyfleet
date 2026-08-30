"""Regenerate docs/SERVICES.md from the bundled services.yaml.

Usage: uv run python scripts/gen_services_md.py

Run after any change to src/keyfleet/data/services.yaml —
tests/test_data_files.py fails while the checked-in file is stale.
"""

from __future__ import annotations

from pathlib import Path

from keyfleet.bundled import load_bundled, services_markdown

SERVICES_MD = Path(__file__).resolve().parent.parent / "docs" / "SERVICES.md"


def main() -> None:
    SERVICES_MD.write_text(services_markdown(load_bundled()), encoding="utf-8")
    print(f"wrote {SERVICES_MD}")


if __name__ == "__main__":
    main()
