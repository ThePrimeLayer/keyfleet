"""Firmware comparison, model matching, and capacity resolution."""

from __future__ import annotations

from keyfleet.bundled import (
    BundledData,
    discoverable_capacity,
    firmware_in_range,
    firmware_tuple,
    load_bundled,
    model_info_for_key,
)
from keyfleet.model import Key


def key(model: str | None, vendor: str = "yubico", firmware: str | None = None) -> Key:
    return Key.model_validate(
        {"id": "k", "label": "K", "vendor": vendor, "model": model, "firmware": firmware}
    )


def models_data(*entries: dict) -> list:
    return BundledData.model_validate({"models": list(entries)}).models


YK5 = {
    "id": "yk5",
    "vendor": "yubico",
    "family": "YubiKey 5",
    "discoverable_capacity": [
        {"firmware_lt": "5.7", "capacity": 25},
        {"firmware_ge": "5.7", "capacity": 100},
    ],
    "source_url": "https://example.invalid/doc",
    "verified": "2026-08-29",
}
YK5C = {
    "id": "yk5c",
    "vendor": "yubico",
    "family": "YubiKey 5C",
    "discoverable_capacity": 25,
    "source_url": "https://example.invalid/doc",
    "verified": "2026-08-29",
}


class TestFirmwareCompare:
    def test_tuple_parsing(self):
        assert firmware_tuple("5.7.1") == (5, 7, 1)
        assert firmware_tuple("5.7") == (5, 7)
        assert firmware_tuple("5.7.4a") == (5, 7, 4)
        assert firmware_tuple("weird") == (0,)

    def test_range_bounds_ge_inclusive_lt_exclusive(self):
        assert firmware_in_range("5.4.1", firmware_ge="5.4.1", firmware_lt="5.7.4")
        assert firmware_in_range("5.7.3", firmware_ge="5.4.1", firmware_lt="5.7.4")
        assert not firmware_in_range("5.7.4", firmware_ge="5.4.1", firmware_lt="5.7.4")
        assert not firmware_in_range("5.4.0", firmware_ge="5.4.1", firmware_lt="5.7.4")

    def test_open_bounds(self):
        assert firmware_in_range("1.0")
        assert firmware_in_range("5.6.9", firmware_lt="5.7")
        assert not firmware_in_range("5.7", firmware_lt="5.7")


class TestModelMatching:
    def test_prefix_match_is_case_insensitive(self):
        models = models_data(YK5)
        assert model_info_for_key(models, key("yubikey 5c nfc")).id == "yk5"

    def test_longest_family_wins(self):
        # "YubiKey 5C NFC" is a prefix-match for both families; the longer,
        # more specific one must win. (Prefix matching deliberately cannot
        # catch suffix-style names like "... FIPS" — such series need their
        # own family spelled as the actual model prefix.)
        models = models_data(YK5, YK5C)
        assert model_info_for_key(models, key("YubiKey 5C NFC")).id == "yk5c"
        assert model_info_for_key(models, key("YubiKey 5 NFC")).id == "yk5"

    def test_vendor_must_match(self):
        models = models_data(YK5)
        assert model_info_for_key(models, key("YubiKey 5 NFC", vendor="other")) is None

    def test_no_model_string_means_no_match(self):
        assert model_info_for_key(models_data(YK5), key(None)) is None


class TestCapacityResolution:
    def test_firmware_selects_rule(self):
        info = models_data(YK5)[0]
        assert discoverable_capacity(info, "5.4.3") == 25
        assert discoverable_capacity(info, "5.7.1") == 100

    def test_unknown_firmware_with_differing_rules_is_indeterminate(self):
        info = models_data(YK5)[0]
        assert discoverable_capacity(info, None) is None

    def test_unknown_firmware_with_agreeing_rules_resolves(self):
        entry = dict(YK5, discoverable_capacity=[{"firmware_lt": "9", "capacity": 25}])
        info = models_data(entry)[0]
        assert discoverable_capacity(info, None) == 25

    def test_plain_int_capacity(self):
        info = models_data(YK5C)[0]
        assert discoverable_capacity(info, None) == 25


class TestLoadBundled:
    def test_bundled_data_loads_and_validates(self):
        bundled = load_bundled()
        assert len(bundled.services) >= 30
        assert bundled.models
        assert bundled.advisories
