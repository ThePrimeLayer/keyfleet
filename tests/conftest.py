from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent


def fixture(name: str) -> Path:
    path = FIXTURES / name
    assert path.is_file(), f"missing test fixture {path}"
    return path
