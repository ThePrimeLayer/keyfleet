"""Unknown-service check: account.service must name a bundled service or
be "other" — otherwise WARN (probably a typo)."""

from __future__ import annotations

from conftest import make_account, make_ledger

from keyfleet.bundled import BundledData, load_bundled
from keyfleet.checks import Level, check_unknown_service

BUNDLED = BundledData.model_validate(
    {
        "services": {
            "github": {
                "name": "GitHub",
                "source_url": "https://example.invalid/doc",
                "verified": "2026-08-29",
            }
        }
    }
)


class TestUnknownService:
    def test_typo_service_warns_with_account_and_service(self):
        ledger = make_ledger([make_account("T1", ["k-active"], label="Code", service="guthib")])
        findings = check_unknown_service(ledger, BUNDLED)
        assert len(findings) == 1
        assert findings[0].level is Level.WARN
        assert findings[0].message == (
            'account "Code": service "guthib" is not in the bundled services.yaml '
            '— typo, or use "other" (contributions welcome)'
        )

    def test_known_service_is_clean(self):
        ledger = make_ledger([make_account("T1", ["k-active"], service="github")])
        assert check_unknown_service(ledger, BUNDLED) == []

    def test_other_is_exempt(self):
        ledger = make_ledger([make_account("T1", ["k-active"], service="other")])
        assert check_unknown_service(ledger, BUNDLED) == []

    def test_default_service_is_other_and_exempt(self):
        ledger = make_ledger([make_account("T1", ["k-active"])])
        assert check_unknown_service(ledger, BUNDLED) == []

    def test_real_bundled_data_covers_the_majors(self):
        ledger = make_ledger(
            [
                make_account("T1", ["k-active"], id=svc, service=svc)
                for svc in ("google", "github", "bitwarden", "aws", "discord")
            ]
        )
        assert check_unknown_service(ledger, load_bundled()) == []
