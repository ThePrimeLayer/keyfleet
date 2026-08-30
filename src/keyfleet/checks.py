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


def check_lost_retired(ledger: Ledger) -> list[Finding]:
    """FAIL for every lost/retired key still carrying registrations.

    Whoever holds the key can still use those credentials — de-register them
    (``keyfleet lost KEY`` prints the ordered checklist).
    """
    accounts_using: dict[str, int] = {}
    for account in ledger.accounts:
        for key_id in {registration.key for registration in account.registrations}:
            accounts_using[key_id] = accounts_using.get(key_id, 0) + 1
    findings: list[Finding] = []
    for key in ledger.keys:
        if key.status not in (KeyStatus.LOST, KeyStatus.RETIRED):
            continue
        count = accounts_using.get(key.id, 0)
        if count:
            noun = "account" if count == 1 else "accounts"
            findings.append(
                Finding(
                    level=Level.FAIL,
                    check="lost-retired",
                    message=(
                        f"Key {key.id} is {key.status.value.upper()} but still registered "
                        f"on {count} {noun} → run: keyfleet lost {key.id}"
                    ),
                    key_id=key.id,
                )
            )
    return findings


def check_weak_factors(ledger: Ledger) -> list[Finding]:
    """WARN for every factor an account carries that its tier's policy warns against."""
    findings: list[Finding] = []
    for account in ledger.accounts:
        warned = ledger.policy.warn_factors.get(account.tier, [])
        findings.extend(
            Finding(
                level=Level.WARN,
                check="weak-factor",
                message=f'{account.tier} "{account.label}" lists {factor.value} as a factor',
                account_id=account.id,
            )
            for factor in account.other_factors
            if factor in warned
        )
    return findings


def check_spare_unregistered(ledger: Ledger) -> list[Finding]:
    """WARN for spare keys registered nowhere — an unregistered spare is not a backup."""
    registered = {
        registration.key for account in ledger.accounts for registration in account.registrations
    }
    return [
        Finding(
            level=Level.WARN,
            check="spare-unregistered",
            message=(
                f"Spare key {key.id} is registered nowhere "
                "(a spare that isn't registered is not a backup)"
            ),
            key_id=key.id,
        )
        for key in ledger.keys
        if key.status is KeyStatus.SPARE and key.id not in registered
    ]


#: Every check, in run order. Still to come in M1: capacity vs models.yaml
#: and unknown-service ids vs services.yaml.
ALL_CHECKS = (check_min_keys, check_lost_retired, check_weak_factors, check_spare_unregistered)


def run_checks(ledger: Ledger) -> list[Finding]:
    """Run every check; findings ordered FAIL → WARN → INFO, stable within a level."""
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        findings.extend(check(ledger))
    return sorted(findings, key=lambda finding: _LEVEL_ORDER[finding.level])
