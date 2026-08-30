"""Lost/retired hygiene: a registration on a lost or retired key is a FAIL
(an attacker holding the key could still use it — de-register it)."""

from __future__ import annotations

from conftest import make_account, make_ledger

from keyfleet.checks import Level, check_lost_retired


class TestLostRetired:
    def test_lost_key_with_registrations_fails(self):
        ledger = make_ledger(
            [
                make_account("T0", ["k-active", "k-lost"], id="mail", label="Mail"),
                make_account("T1", ["k-lost"], id="repo", label="Repo"),
            ]
        )
        findings = check_lost_retired(ledger)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.level is Level.FAIL
        assert finding.key_id == "k-lost"
        assert finding.message == (
            "Key k-lost is LOST but still registered on 2 accounts → run: keyfleet lost k-lost"
        )

    def test_retired_key_with_registration_fails_with_singular_noun(self):
        ledger = make_ledger([make_account("T2", ["k-retired"], id="forum", label="Forum")])
        findings = check_lost_retired(ledger)
        assert len(findings) == 1
        assert findings[0].message == (
            "Key k-retired is RETIRED but still registered on 1 account "
            "→ run: keyfleet lost k-retired"
        )

    def test_unregistered_lost_key_is_clean(self):
        ledger = make_ledger([make_account("T2", ["k-active"])])
        assert check_lost_retired(ledger) == []

    def test_active_and_spare_registrations_never_flagged(self):
        ledger = make_ledger([make_account("T1", ["k-active", "k-spare"])])
        assert check_lost_retired(ledger) == []

    def test_two_registrations_on_one_account_count_one_account(self):
        ledger = make_ledger(
            [
                {
                    "id": "acct",
                    "label": "Account",
                    "tier": "T1",
                    "registrations": [
                        {"key": "k-lost", "type": "fido2-discoverable"},
                        {"key": "k-lost", "type": "piv"},
                    ],
                }
            ]
        )
        findings = check_lost_retired(ledger)
        assert "registered on 1 account " in findings[0].message
