"""Weak factors: policy.warn_factors[tier] ∩ account.other_factors → WARN."""

from __future__ import annotations

from conftest import make_account, make_ledger

from keyfleet.checks import Level, check_weak_factors


class TestWeakFactors:
    def test_default_policy_warns_sms_and_email_on_t0(self):
        ledger = make_ledger(
            [
                make_account(
                    "T0",
                    ["k-active"],
                    id="vault",
                    label="Password manager",
                    other_factors=["sms", "email", "totp-app"],
                )
            ]
        )
        findings = check_weak_factors(ledger)
        assert [f.level for f in findings] == [Level.WARN, Level.WARN]
        assert findings[0].message == 'T0 "Password manager" lists sms as a factor'
        assert findings[1].message == 'T0 "Password manager" lists email as a factor'
        assert all(f.account_id == "vault" for f in findings)

    def test_same_factor_on_unwarned_tier_is_clean(self):
        ledger = make_ledger([make_account("T1", ["k-active"], other_factors=["sms"])])
        assert check_weak_factors(ledger) == []

    def test_custom_policy_extends_to_other_tiers(self):
        ledger = make_ledger(
            [make_account("T1", ["k-active"], label="Mail", other_factors=["push"])],
            policy={"warn_factors": {"T1": ["push"]}},
        )
        findings = check_weak_factors(ledger)
        assert len(findings) == 1
        assert findings[0].message == 'T1 "Mail" lists push as a factor'

    def test_no_other_factors_is_clean(self):
        ledger = make_ledger([make_account("T0", ["k-active"])])
        assert check_weak_factors(ledger) == []
