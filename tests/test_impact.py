"""Lost-key impact analysis: ordering, inaccessibility, policy math (brief §9)."""

from __future__ import annotations

import pytest
from conftest import fixture

from keyfleet.impact import UnknownKeyError, analyze_lost
from keyfleet.model import Ledger, load_ledger


def ledger() -> Ledger:
    return Ledger.model_validate(
        {
            "version": 1,
            "keys": [
                {"id": "k-main", "label": "Main", "vendor": "yubico", "status": "active"},
                {"id": "k-second", "label": "Second", "vendor": "yubico", "status": "active"},
                {"id": "k-old", "label": "Old", "vendor": "yubico", "status": "lost"},
            ],
            "accounts": [
                # T2 but becomes fully inaccessible: only k-main, no other factors.
                {
                    "id": "solo",
                    "label": "Solo forum",
                    "tier": "T2",
                    "registrations": [{"key": "k-main", "type": "u2f", "nickname": "main"}],
                },
                # T0, drops 3→... has k-main + k-second (+ k-old lost, not counted).
                {
                    "id": "vault",
                    "label": "Vault",
                    "tier": "T0",
                    "registrations": [
                        {"key": "k-main", "type": "fido2-non-discoverable", "nickname": "main"},
                        {"key": "k-second", "type": "fido2-non-discoverable", "nickname": "2nd"},
                        {"key": "k-old", "type": "fido2-non-discoverable", "nickname": "old"},
                    ],
                    "other_factors": ["recovery-codes"],
                },
                # T0, unaffected (only k-second).
                {
                    "id": "mail",
                    "label": "Mail",
                    "tier": "T0",
                    "registrations": [{"key": "k-second", "type": "fido2-discoverable"}],
                    "other_factors": ["totp-app"],
                },
            ],
        }
    )


class TestAnalyzeLost:
    def test_unknown_key_raises_with_known_ids(self):
        with pytest.raises(UnknownKeyError, match=r"k-main, k-old, k-second"):
            analyze_lost(ledger(), "k-nope")

    def test_affected_and_unaffected_partition(self):
        result = analyze_lost(ledger(), "k-main")
        assert {impact.account_id for impact in result.affected} == {"solo", "vault"}
        assert result.unaffected_accounts == 1

    def test_ordering_tier_first_then_inaccessible(self):
        result = analyze_lost(ledger(), "k-main")
        assert [impact.account_id for impact in result.affected] == ["vault", "solo"]

    def test_inaccessible_needs_zero_keys_and_zero_factors(self):
        result = analyze_lost(ledger(), "k-main")
        by_id = {impact.account_id: impact for impact in result.affected}
        assert by_id["solo"].inaccessible
        assert by_id["solo"].remaining_keys == 0
        assert not by_id["vault"].inaccessible

    def test_remaining_counts_exclude_lost_status_keys(self):
        result = analyze_lost(ledger(), "k-main")
        vault = next(i for i in result.affected if i.account_id == "vault")
        # k-old is status lost so it never counted; losing k-main leaves k-second.
        assert vault.remaining_keys == 1
        assert vault.required == 3
        assert vault.below_policy

    def test_lost_registrations_carry_nicknames(self):
        result = analyze_lost(ledger(), "k-main")
        vault = next(i for i in result.affected if i.account_id == "vault")
        assert [r.nickname for r in vault.lost_registrations] == ["main"]

    def test_analyzing_already_lost_key_works(self):
        result = analyze_lost(ledger(), "k-old")
        vault = next(i for i in result.affected if i.account_id == "vault")
        # k-old never counted toward coverage, so remaining is unchanged: 2.
        assert vault.remaining_keys == 2

    def test_inaccessible_first_within_same_tier(self):
        raw = ledger().model_dump(mode="json")
        # Same tier everywhere and vault listed before solo: the inaccessible
        # solo must still sort first.
        for account in raw["accounts"]:
            account["tier"] = "T2"
        raw["accounts"].reverse()
        result = analyze_lost(Ledger.model_validate(raw), "k-main")
        assert [impact.account_id for impact in result.affected] == ["solo", "vault"]

    def test_fixture_ledger_end_to_end(self):
        result = analyze_lost(load_ledger(fixture("min_keys_gap.yaml")), "k-lost")
        assert [impact.account_id for impact in result.affected] == ["repo"]
        assert result.affected[0].remaining_keys == 1
