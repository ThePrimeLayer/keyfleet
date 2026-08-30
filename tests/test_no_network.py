"""AGENTS.md §8.1: no network calls in runtime code — grep src/ for the
banned imports and fail on any hit."""

from __future__ import annotations

import re

from conftest import REPO_ROOT

BANNED = ("httpx", "requests", "urllib", "socket", "aiohttp")
IMPORT_RE = re.compile(rf"^\s*(?:import|from)\s+(?:{'|'.join(BANNED)})\b", re.MULTILINE)


def test_no_network_imports_in_src():
    offenders = []
    for path in (REPO_ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        offenders += [
            f"{path.relative_to(REPO_ROOT)}: {match.group(0).strip()}"
            for match in IMPORT_RE.finditer(text)
        ]
    assert not offenders, "network imports are banned in runtime code:\n" + "\n".join(offenders)
