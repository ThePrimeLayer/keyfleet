"""Rendering for the terminal and JSON — the only layer that formats output.

Output shape follows brief §8's sample. Nothing here mutates the ledger or
decides exit codes; the CLI owns those.
"""

from __future__ import annotations

import json
from collections import Counter

from rich.console import Console
from rich.text import Text

from keyfleet.checks import Finding, Level
from keyfleet.model import KeyStatus, Ledger

LEVEL_STYLES = {Level.FAIL: "bold red", Level.WARN: "bold yellow", Level.INFO: "bold cyan"}


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def ledger_header(ledger: Ledger) -> str:
    """e.g. ``keyfleet check — 3 keys (2 active, 1 spare) · 14 accounts``."""
    by_status = Counter(key.status for key in ledger.keys)
    breakdown = ", ".join(f"{by_status[s]} {s.value}" for s in KeyStatus if by_status[s])
    keys = _plural(len(ledger.keys), "key")
    if breakdown:
        keys += f" ({breakdown})"
    return f"keyfleet check — {keys} · {_plural(len(ledger.accounts), 'account')}"


def summary_line(findings: list[Finding], exit_code: int) -> str:
    """e.g. ``2 fail, 2 warn, 2 info · exit 1``."""
    by_level = Counter(finding.level for finding in findings)
    return (
        f"{by_level[Level.FAIL]} fail, {by_level[Level.WARN]} warn, "
        f"{by_level[Level.INFO]} info · exit {exit_code}"
    )


def render_check(ledger: Ledger, findings: list[Finding], exit_code: int, console: Console) -> None:
    """Human-readable check report (brief §8 sample layout)."""
    console.print(ledger_header(ledger), style="bold", soft_wrap=True)
    console.print()
    for finding in findings:
        line = Text()
        line.append(f"{finding.level.value:<5}", style=LEVEL_STYLES[finding.level])
        line.append(" ")
        line.append(finding.message)
        console.print(line, soft_wrap=True)
    if findings:
        console.print()
    console.print(summary_line(findings, exit_code), soft_wrap=True)


def check_json(ledger: Ledger, findings: list[Finding], exit_code: int, ledger_path: str) -> str:
    """Machine-readable check report for ``keyfleet check --json``."""
    by_level = Counter(finding.level for finding in findings)
    payload = {
        "ledger": {
            "path": ledger_path,
            "keys": len(ledger.keys),
            "accounts": len(ledger.accounts),
        },
        "findings": [
            {
                "level": finding.level.value,
                "check": finding.check,
                "message": finding.message,
                "account_id": finding.account_id,
                "key_id": finding.key_id,
            }
            for finding in findings
        ],
        "summary": {
            "fail": by_level[Level.FAIL],
            "warn": by_level[Level.WARN],
            "info": by_level[Level.INFO],
        },
        "exit_code": exit_code,
    }
    return json.dumps(payload, indent=2)
