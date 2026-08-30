"""Capacity check: discoverable-credential usage per key vs models.yaml
(INFO at ≥50%, WARN at ≥90%; ledger-based estimate)."""

from __future__ import annotations

from keyfleet.bundled import BundledData
from keyfleet.checks import Level, check_capacity
from keyfleet.model import Ledger

BUNDLED = BundledData.model_validate(
    {
        "models": [
            {
                "id": "yk5",
                "vendor": "yubico",
                "family": "YubiKey 5",
                "discoverable_capacity": [
                    {"firmware_lt": "5.7", "capacity": 25},
                    {"firmware_ge": "5.7", "capacity": 100},
                ],
                "source_url": "https://example.invalid/doc",
                "verified": "2026-08-29",
            },
            {
                "id": "nk",
                "vendor": "nitrokey",
                "family": "Nitrokey 3",
                "discoverable_capacity": 10,
                "source_url": "https://example.invalid/doc",
                "verified": "2026-08-29",
            },
        ]
    }
)


def ledger_with_discoverable(
    count: int,
    *,
    model: str | None = "YubiKey 5C NFC",
    vendor: str = "yubico",
    firmware: str | None = "5.4.3",
    reg_type: str = "fido2-discoverable",
) -> Ledger:
    return Ledger.model_validate(
        {
            "version": 1,
            "keys": [
                {
                    "id": "k1",
                    "label": "Key",
                    "vendor": vendor,
                    "model": model,
                    "firmware": firmware,
                }
            ],
            "accounts": [
                {
                    "id": f"acct{i}",
                    "label": f"Account {i}",
                    "tier": "T2",
                    "registrations": [{"key": "k1", "type": reg_type}],
                }
                for i in range(count)
            ],
        }
    )


class TestCapacity:
    def test_below_half_is_silent(self):
        assert check_capacity(ledger_with_discoverable(12), BUNDLED) == []

    def test_half_full_is_info_with_counts(self):
        findings = check_capacity(ledger_with_discoverable(13), BUNDLED)
        assert len(findings) == 1
        assert findings[0].level is Level.INFO
        assert findings[0].key_id == "k1"
        assert findings[0].message == (
            "k1: 13/25 discoverable credentials (ledger count) — plan capacity"
        )

    def test_ninety_percent_is_warn(self):
        findings = check_capacity(ledger_with_discoverable(23), BUNDLED)
        assert findings[0].level is Level.WARN
        assert "23/25" in findings[0].message
        assert "nearly full" in findings[0].message

    def test_newer_firmware_uses_bigger_capacity(self):
        ledger = ledger_with_discoverable(13, firmware="5.7.1")
        assert check_capacity(ledger, BUNDLED) == []

    def test_unknown_firmware_with_differing_rules_is_silent(self):
        ledger = ledger_with_discoverable(20, firmware=None)
        assert check_capacity(ledger, BUNDLED) == []

    def test_plain_int_capacity(self):
        ledger = ledger_with_discoverable(5, model="Nitrokey 3A NFC", vendor="nitrokey")
        findings = check_capacity(ledger, BUNDLED)
        assert len(findings) == 1
        assert "5/10" in findings[0].message

    def test_unknown_model_is_silent(self):
        ledger = ledger_with_discoverable(20, model="Mystery Key 9000")
        assert check_capacity(ledger, BUNDLED) == []

    def test_non_discoverable_registrations_do_not_count(self):
        ledger = ledger_with_discoverable(20, reg_type="fido2-non-discoverable")
        assert check_capacity(ledger, BUNDLED) == []
