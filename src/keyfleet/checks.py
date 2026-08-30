"""Pure check functions over a validated :class:`~keyfleet.model.Ledger`.

Checks take the loaded ledger and return findings; no file or terminal I/O
happens here (AGENTS.md §5). Rendering lives in :mod:`keyfleet.report`.
Core rules: brief §9.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from keyfleet.bundled import BundledData, discoverable_capacity, model_info_for_key
from keyfleet.model import Account, KeyStatus, Ledger, RegistrationType


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


def check_recovery_codes(ledger: Ledger) -> list[Finding]:
    """INFO when a tier that requires recovery codes has an account without a stored pointer."""
    required = set(ledger.policy.require_recovery_codes_for)
    findings: list[Finding] = []
    for account in ledger.accounts:
        if account.tier not in required:
            continue
        pointer = account.recovery_codes
        if pointer is None:
            detail = "has no recovery-code pointer"
        elif not pointer.stored:
            detail = "marks recovery codes as not stored"
        else:
            continue
        findings.append(
            Finding(
                level=Level.INFO,
                check="recovery-codes",
                message=(
                    f'{account.tier} "{account.label}" {detail} '
                    f"(policy requires recovery codes for {account.tier})"
                ),
                account_id=account.id,
            )
        )
    return findings


#: Discoverable-credential usage fractions at which capacity findings appear.
CAPACITY_INFO_AT = 0.5
CAPACITY_WARN_AT = 0.9


def check_capacity(ledger: Ledger, bundled: BundledData) -> list[Finding]:
    """Discoverable-credential usage per key vs models.yaml capacity.

    Ledger-based estimate — it can undercount (registrations made outside the
    ledger are invisible). INFO from 50% usage, WARN from 90%.
    """
    counts: dict[str, int] = {}
    for account in ledger.accounts:
        for registration in account.registrations:
            if registration.type is RegistrationType.FIDO2_DISCOVERABLE:
                counts[registration.key] = counts.get(registration.key, 0) + 1
    findings: list[Finding] = []
    for key in ledger.keys:
        count = counts.get(key.id, 0)
        if not count:
            continue
        info = model_info_for_key(bundled.models, key)
        capacity = discoverable_capacity(info, key.firmware) if info else None
        if not capacity:
            continue
        usage = count / capacity
        if usage >= CAPACITY_WARN_AT:
            level, action = Level.WARN, "nearly full; free slots or add a key"
        elif usage >= CAPACITY_INFO_AT:
            level, action = Level.INFO, "plan capacity"
        else:
            continue
        findings.append(
            Finding(
                level=level,
                check="capacity",
                message=(
                    f"{key.id}: {count}/{capacity} discoverable credentials "
                    f"(ledger count) — {action}"
                ),
                key_id=key.id,
            )
        )
    return findings


def check_unknown_service(ledger: Ledger, bundled: BundledData) -> list[Finding]:
    """WARN when an account's service id names no bundled service ("other" is exempt).

    Usually a typo; a correct id buys the account working links in
    ``keyfleet lost`` and ``keyfleet report``.
    """
    return [
        Finding(
            level=Level.WARN,
            check="unknown-service",
            message=(
                f'account "{account.label}": service "{account.service}" is not in the '
                'bundled services.yaml — typo, or use "other" (contributions welcome)'
            ),
            account_id=account.id,
        )
        for account in ledger.accounts
        if account.service != "other" and account.service not in bundled.services
    ]


#: Ledger-only checks, in run order.
ALL_CHECKS = (
    check_min_keys,
    check_lost_retired,
    check_weak_factors,
    check_spare_unregistered,
    check_recovery_codes,
)

#: Checks that also need the bundled reference data.
DATA_CHECKS = (check_capacity, check_unknown_service)


def run_checks(ledger: Ledger, bundled: BundledData | None = None) -> list[Finding]:
    """Run every check; findings ordered FAIL → WARN → INFO, stable within a level.

    Without ``bundled``, the data-driven checks (capacity, unknown service)
    are skipped.
    """
    findings: list[Finding] = []
    for check in ALL_CHECKS:
        findings.extend(check(ledger))
    if bundled is not None:
        for data_check in DATA_CHECKS:
            findings.extend(data_check(ledger, bundled))
    return sorted(findings, key=lambda finding: _LEVEL_ORDER[finding.level])
