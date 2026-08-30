"""Pure check functions over a validated :class:`~keyfleet.model.Ledger`.

Checks take the loaded ledger and return findings; no file or terminal I/O
happens here (AGENTS.md §5). Rendering lives in :mod:`keyfleet.report`.
Core rules: brief §9.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from keyfleet.model import Account, KeyStatus, Ledger


class Level(StrEnum):
    FAIL = "FAIL"
    WARN = "WARN"
    INFO = "INFO"


_LEVEL_ORDER = {Level.FAIL: 0, Level.WARN: 1, Level.INFO: 2}


@dataclass(frozen=True, slots=True)
class Finding:
    """One actionable result of one check."""

    level: Level
    check: str  # machine-readable check id, e.g. "min-keys"
    message: str
    account_id: str | None = None
    key_id: str | None = None


#: Key statuses that count toward an account's coverage (brief §9): a lost or
#: retired key is not a backup.
COVERAGE_STATUSES = frozenset({KeyStatus.ACTIVE, KeyStatus.SPARE})


def covering_key_ids(ledger: Ledger, account: Account) -> set[str]:
    """Distinct keys registered on ``account`` whose status counts as coverage."""
    status_by_id = {key.id: key.status for key in ledger.keys}
    return {
        registration.key
        for registration in account.registrations
        if status_by_id[registration.key] in COVERAGE_STATUSES
    }


def check_min_keys(ledger: Ledger) -> list[Finding]:
    """FAIL for every account with fewer counted keys than ``policy.min_keys[tier]``."""
    findings: list[Finding] = []
    for account in ledger.accounts:
        required = ledger.policy.min_keys.for_tier(account.tier)
        have = len(covering_key_ids(ledger, account))
        if have < required:
            noun = "hardware key" if have == 1 else "hardware keys"
            findings.append(
                Finding(
                    level=Level.FAIL,
                    check="min-keys",
                    message=(
                        f'{account.tier} "{account.label}" has {have} {noun} registered; '
                        f"policy requires {required}"
                    ),
                    account_id=account.id,
                )
            )
    return findings


#: Every check, in run order. M1 adds lost/retired hygiene, weak factors,
#: unregistered spares, capacity, and recovery-code pointers.
ALL_CHECKS = (check_min_keys,)


def run_checks(ledger: Ledger) -> list[Finding]:
    """Run every check; findings ordered FAIL → WARN → INFO, stable within a level."""
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        findings.extend(check(ledger))
    return sorted(findings, key=lambda finding: _LEVEL_ORDER[finding.level])
