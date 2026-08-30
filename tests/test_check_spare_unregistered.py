"""Unregistered spares: a spare registered nowhere is not a backup → WARN."""

from __future__ import annotations

from conftest import make_account, make_ledger

from keyfleet.checks import Level, check_spare_unregistered


class TestSpareUnregistered:
    def test_spare_registered_nowhere_warns(self):
        ledger = make_ledger([make_account("T2", ["k-active"])])
        findings = check_spare_unregistered(ledger)
        assert len(findings) == 1
        assert findings[0].level is Level.WARN
        assert findings[0].key_id == "k-spare"
        assert findings[0].message == (
            "Spare key k-spare is registered nowhere "
            "(a spare that isn't registered is not a backup)"
        )

    def test_spare_with_any_registration_is_clean(self):
        ledger = make_ledger([make_account("T2", ["k-spare"])])
        assert check_spare_unregistered(ledger) == []

    def test_unregistered_active_or_lost_keys_not_flagged(self):
        # Only spares get this warning; k-active/k-lost/k-retired stay silent.
        ledger = make_ledger([make_account("T2", ["k-spare"])])
        findings = check_spare_unregistered(ledger)
        assert findings == []
