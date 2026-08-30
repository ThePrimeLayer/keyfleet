"""Pure lost-key impact analysis (brief §9).

Given a key id, compute per-account fallout: remaining coverage, policy
breach, and whether the account becomes inaccessible. No I/O here; the
de-registration checklist rendering lives in :mod:`keyfleet.report`.

The analysis is a pre-mortem as much as an incident tool: it works no matter
the key's current status ("what breaks *if* I lose this key").
"""

from __future__ import annotations

from dataclasses import dataclass

from keyfleet.checks import covering_key_ids
from keyfleet.model import Key, Ledger, Registration, Tier

_TIER_ORDER = {Tier.T0: 0, Tier.T1: 1, Tier.T2: 2}


@dataclass(frozen=True, slots=True)
class AccountImpact:
    """What losing one key means for one account."""

    account_id: str
    label: str
    tier: Tier
    service: str
    lost_registrations: tuple[Registration, ...]  # entries to delete in the service UI
    remaining_keys: int  # active|spare keys still registered afterwards
    required: int  # policy.min_keys for the tier
    other_factor_count: int

    @property
    def below_policy(self) -> bool:
        return self.remaining_keys < self.required

    @property
    def inaccessible(self) -> bool:
        """No hardware key left and no other second factor at all."""
        return self.remaining_keys == 0 and self.other_factor_count == 0


@dataclass(frozen=True, slots=True)
class LostImpact:
    key: Key
    affected: tuple[AccountImpact, ...]  # ordered: tier, inaccessible-first
    unaffected_accounts: int


class UnknownKeyError(ValueError):
    """The requested key id does not exist in the ledger."""


def analyze_lost(ledger: Ledger, key_id: str) -> LostImpact:
    """Impact of losing ``key_id``, or raise :class:`UnknownKeyError`."""
    key = next((key for key in ledger.keys if key.id == key_id), None)
    if key is None:
        known = ", ".join(sorted(k.id for k in ledger.keys)) or "none defined"
        raise UnknownKeyError(f'no key with id "{key_id}" in the ledger (known keys: {known})')

    affected: list[AccountImpact] = []
    unaffected = 0
    for account in ledger.accounts:
        lost_registrations = tuple(
            registration for registration in account.registrations if registration.key == key_id
        )
        if not lost_registrations:
            unaffected += 1
            continue
        remaining = len(covering_key_ids(ledger, account) - {key_id})
        affected.append(
            AccountImpact(
                account_id=account.id,
                label=account.label,
                tier=account.tier,
                service=account.service,
                lost_registrations=lost_registrations,
                remaining_keys=remaining,
                required=ledger.policy.min_keys.for_tier(account.tier),
                other_factor_count=len(account.other_factors),
            )
        )

    affected.sort(key=lambda impact: (_TIER_ORDER[impact.tier], not impact.inaccessible))
    return LostImpact(key=key, affected=tuple(affected), unaffected_accounts=unaffected)
