"""Advisory matching: vendor + firmware ranges, ledger extras, needs-firmware."""

from __future__ import annotations

from conftest import fixture

from keyfleet.bundled import BundledData, load_bundled, match_advisories
from keyfleet.model import Ledger, load_ledger

TEST_BUNDLED = BundledData.model_validate(
    {
        "advisories": [
            {
                "id": "ADV-OLD",
                "vendor": "yubico",
                "affects": {"firmware_ge": "5.0", "firmware_lt": "5.7"},
                "summary": "old firmware issue",
                "url": "https://example.invalid/adv-old",
            },
            {
                "id": "ADV-MID",
                "vendor": "yubico",
                "affects": {"firmware_ge": "5.4.1", "firmware_lt": "5.7.4"},
                "summary": "mid-range issue",
                "url": "https://example.invalid/adv-mid",
            },
        ]
    }
)


def ledger_with_keys(*keys: dict, advisories: list[dict] | None = None) -> Ledger:
    return Ledger.model_validate({"version": 1, "keys": list(keys), "advisories": advisories or []})


def key(key_id: str, vendor: str = "yubico", firmware: str | None = None) -> dict:
    return {"id": key_id, "label": key_id, "vendor": vendor, "firmware": firmware}


class TestMatchAdvisories:
    def test_firmware_selects_matching_ranges(self):
        ledger = ledger_with_keys(key("k1", firmware="5.4.3"), key("k2", firmware="5.7.4"))
        matches = match_advisories(ledger, TEST_BUNDLED)
        assert len(matches) == 1
        assert matches[0].key_id == "k1"
        assert [advisory.id for advisory in matches[0].advisories] == ["ADV-MID", "ADV-OLD"]

    def test_key_without_firmware_needs_firmware(self):
        matches = match_advisories(ledger_with_keys(key("k1")), TEST_BUNDLED)
        assert len(matches) == 1
        assert matches[0].needs_firmware

    def test_vendor_without_advisories_is_omitted(self):
        matches = match_advisories(
            ledger_with_keys(key("k1", vendor="nitrokey", firmware="1.8.2")), TEST_BUNDLED
        )
        assert matches == []

    def test_ledger_advisories_extend_and_override(self):
        extra = {
            "id": "ADV-OLD",  # overrides the bundled one entirely
            "vendor": "yubico",
            "affects": {"firmware_lt": "5.1"},
            "summary": "narrowed by ledger",
            "url": "https://example.invalid/adv-old-v2",
        }
        ledger = ledger_with_keys(key("k1", firmware="5.4.3"), advisories=[extra])
        matches = match_advisories(ledger, TEST_BUNDLED)
        # 5.4.3 no longer matches the overridden ADV-OLD (< 5.1), only ADV-MID.
        assert [advisory.id for advisory in matches[0].advisories] == ["ADV-MID"]

    def test_real_bundled_data_flags_old_yubikey_firmware(self):
        ledger = load_ledger(fixture("valid.yaml"))
        matches = {match.key_id: match for match in match_advisories(ledger, load_bundled())}
        # yk-b runs 5.4.3: inside YSA-2024-02/03 (5.0 to 5.7) and YSA-2025-02.
        assert {a.id for a in matches["yk-b"].advisories} == {
            "YSA-2024-02",
            "YSA-2024-03",
            "YSA-2025-02",
        }
        # yk-a runs 5.7.1: only YSA-2025-02 (5.4.1 to 5.7.4).
        assert {a.id for a in matches["yk-a"].advisories} == {"YSA-2025-02"}
        # spare-c has vendor other with a ledger advisory but no firmware.
        assert matches["spare-c"].needs_firmware
