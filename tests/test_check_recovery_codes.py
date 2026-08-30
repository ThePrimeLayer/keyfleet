"""Recovery-code pointers: tiers in policy.require_recovery_codes_for must
carry a stored pointer → INFO otherwise."""

from __future__ import annotations

from conftest import make_account, make_ledger

from keyfleet.checks import Level, check_recovery_codes


class TestRecoveryCodes:
    def test_missing_pointer_on_required_tier_is_info(self):
        ledger = make_ledger([make_account("T0", ["k-active"], id="vault", label="Vault")])
        findings = check_recovery_codes(ledger)
        assert len(findings) == 1
        assert findings[0].level is Level.INFO
        assert findings[0].account_id == "vault"
        assert findings[0].message == (
            'T0 "Vault" has no recovery-code pointer (policy requires recovery codes for T0)'
        )

    def test_stored_false_is_info_with_distinct_wording(self):
        ledger = make_ledger(
            [
                make_account(
                    "T1",
                    ["k-active"],
                    label="Mail",
                    recovery_codes={"stored": False},
                )
            ]
        )
        findings = check_recovery_codes(ledger)
        assert len(findings) == 1
        assert "marks recovery codes as not stored" in findings[0].message

    def test_stored_pointer_is_clean(self):
        ledger = make_ledger(
            [
                make_account(
                    "T0",
                    ["k-active"],
                    recovery_codes={"stored": True, "where": "vault/recovery"},
                )
            ]
        )
        assert check_recovery_codes(ledger) == []

    def test_unrequired_tier_is_clean(self):
        ledger = make_ledger([make_account("T2", ["k-active"])])
        assert check_recovery_codes(ledger) == []

    def test_custom_policy_narrows_required_tiers(self):
        ledger = make_ledger(
            [make_account("T1", ["k-active"])],
            policy={"require_recovery_codes_for": ["T0"]},
        )
        assert check_recovery_codes(ledger) == []
