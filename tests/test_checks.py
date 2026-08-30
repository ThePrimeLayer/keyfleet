"""Min-keys coverage rule: positive and negative cases (brief §9)."""

from __future__ import annotations

from conftest import fixture

from keyfleet.checks import Level, check_min_keys, covering_key_ids, run_checks
from keyfleet.model import Ledger, load_ledger


def ledger_with(accounts: list[dict], keys: list[dict] | None = None) -> Ledger:
    return Ledger.model_validate(
        {
            "version": 1,
            "keys": keys
            or [
                {"id": "k-active", "label": "Active", "vendor": "yubico", "status": "active"},
                {"id": "k-spare", "label": "Spare", "vendor": "yubico", "status": "spare"},
                {"id": "k-lost", "label": "Lost", "vendor": "yubico", "status": "lost"},
                {"id": "k-retired", "label": "Retired", "vendor": "yubico", "status": "retired"},
            ],
            "accounts": accounts,
        }
    )


def account(tier: str, regs: list[str], **extra) -> dict:
    return {
        "id": extra.pop("id", "acct"),
        "label": extra.pop("label", "Account"),
        "tier": tier,
        "registrations": [{"key": key, "type": "fido2-discoverable"} for key in regs],
        **extra,
    }


class TestMinKeys:
    def test_gap_fixture_produces_expected_fails(self):
        ledger = load_ledger(fixture("min_keys_gap.yaml"))
        findings = check_min_keys(ledger)
        assert [(f.level, f.account_id) for f in findings] == [
            (Level.FAIL, "g-mail"),
            (Level.FAIL, "repo"),
        ]
        assert (
            findings[0].message
            == 'T0 "Primary email (Google)" has 1 hardware key registered; policy requires 3'
        )
        assert (
            findings[1].message == 'T1 "Code hosting" has 1 hardware key registered; '
            "policy requires 2"
        )

    def test_clean_ledger_has_no_findings(self):
        ledger = load_ledger(fixture("valid.yaml"))
        assert run_checks(ledger) == []

    def test_lost_and_retired_keys_do_not_count(self):
        ledger = ledger_with([account("T1", ["k-active", "k-lost", "k-retired"])])
        findings = check_min_keys(ledger)
        assert len(findings) == 1
        assert "has 1 hardware key registered; policy requires 2" in findings[0].message

    def test_spare_keys_do_count(self):
        ledger = ledger_with([account("T1", ["k-active", "k-spare"])])
        assert check_min_keys(ledger) == []

    def test_two_registrations_on_same_key_count_once(self):
        ledger = ledger_with(
            [
                {
                    "id": "acct",
                    "label": "Account",
                    "tier": "T1",
                    "registrations": [
                        {"key": "k-active", "type": "fido2-discoverable"},
                        {"key": "k-active", "type": "piv"},
                    ],
                }
            ]
        )
        findings = check_min_keys(ledger)
        assert len(findings) == 1
        assert "has 1 hardware key registered" in findings[0].message

    def test_zero_keys_message_uses_plural(self):
        ledger = ledger_with([account("T2", [])])
        findings = check_min_keys(ledger)
        assert "has 0 hardware keys registered; policy requires 1" in findings[0].message

    def test_custom_policy_respected(self):
        ledger = ledger_with([account("T2", ["k-active"])])
        assert check_min_keys(ledger) == []
        stricter = ledger.model_copy(deep=True)
        stricter.policy.min_keys.T2 = 2
        assert len(check_min_keys(stricter)) == 1


class TestCoverageHelper:
    def test_covering_key_ids_filters_by_status(self):
        ledger = ledger_with([account("T1", ["k-active", "k-spare", "k-lost", "k-retired"])])
        assert covering_key_ids(ledger, ledger.accounts[0]) == {"k-active", "k-spare"}
