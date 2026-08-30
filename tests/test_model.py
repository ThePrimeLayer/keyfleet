"""Schema, loader, referential-integrity, and secret-rejection tests."""

from __future__ import annotations

import pytest
from conftest import fixture
from pydantic import ValidationError

from keyfleet.model import (
    Factor,
    KeyStatus,
    Ledger,
    LedgerError,
    LedgerNotFoundError,
    Tier,
    load_ledger,
    scan_for_secrets,
)


def minimal(**overrides) -> dict:
    """A minimal valid raw ledger, for inline schema tests."""
    raw = {
        "version": 1,
        "keys": [{"id": "yk-a", "label": "Key A", "vendor": "yubico"}],
        "accounts": [],
    }
    raw.update(overrides)
    return raw


class TestLoadValid:
    def test_valid_ledger_loads(self):
        ledger = load_ledger(fixture("valid.yaml"))
        assert [k.id for k in ledger.keys] == ["yk-a", "yk-b", "spare-c"]
        assert len(ledger.accounts) == 3
        assert ledger.advisories[0].id == "EX-2026-01"

    def test_non_ascii_label_survives(self):
        ledger = load_ledger(fixture("valid.yaml"))
        assert ledger.keys[1].label == "Clé de secours ☂ (sac à dos)"

    def test_int_serial_normalized_to_str(self):
        ledger = load_ledger(fixture("valid.yaml"))
        assert ledger.keys[0].serial == "12345678"

    def test_status_and_defaults(self):
        ledger = load_ledger(fixture("valid.yaml"))
        assert ledger.keys[2].status is KeyStatus.SPARE
        assert ledger.keys[0].notes == ""

    def test_recovery_codes_pointer_is_allowed(self):
        ledger = load_ledger(fixture("valid.yaml"))
        pointer = ledger.accounts[0].recovery_codes
        assert pointer is not None and pointer.stored and pointer.where == "vault/recovery"


class TestPolicyDefaults:
    def test_defaults_when_policy_omitted(self):
        ledger = Ledger.model_validate(minimal())
        assert ledger.policy.min_keys.for_tier(Tier.T0) == 3
        assert ledger.policy.min_keys.for_tier(Tier.T1) == 2
        assert ledger.policy.min_keys.for_tier(Tier.T2) == 1
        assert ledger.policy.require_recovery_codes_for == [Tier.T0, Tier.T1]
        assert ledger.policy.warn_factors == {Tier.T0: [Factor.SMS, Factor.EMAIL]}

    def test_partial_min_keys_keeps_other_tier_defaults(self):
        ledger = Ledger.model_validate(minimal(policy={"min_keys": {"T0": 5}}))
        assert ledger.policy.min_keys.for_tier(Tier.T0) == 5
        assert ledger.policy.min_keys.for_tier(Tier.T1) == 2

    def test_require_recovery_codes_for_is_not_flagged_as_secret(self):
        scan_for_secrets({"policy": {"require_recovery_codes_for": ["T0", "T1"]}}, "inline")


class TestSchemaRejections:
    def test_unknown_field_rejected(self):
        raw = minimal()
        raw["keys"][0]["favourite_color"] = "blue"
        with pytest.raises(ValidationError, match="favourite_color"):
            Ledger.model_validate(raw)

    def test_version_must_be_1(self):
        with pytest.raises(ValidationError, match="version"):
            Ledger.model_validate(minimal(version=2))

    def test_bad_enum_value_rejected(self):
        raw = minimal()
        raw["keys"][0]["status"] = "misplaced"
        with pytest.raises(ValidationError, match=r"misplaced|status"):
            Ledger.model_validate(raw)


class TestIntegrity:
    def test_duplicate_key_ids(self):
        with pytest.raises(LedgerError) as excinfo:
            load_ledger(fixture("dup_ids.yaml"))
        message = str(excinfo.value)
        assert 'duplicate key id "yk-a"' in message
        assert "dup_ids.yaml" in message

    def test_unknown_registration_ref_names_account_key_and_file(self):
        with pytest.raises(LedgerError) as excinfo:
            load_ledger(fixture("bad_ref.yaml"))
        message = str(excinfo.value)
        assert 'account "acct-x"' in message
        assert 'unknown key "yk-zz"' in message
        assert "bad_ref.yaml" in message


class TestSecretRejection:
    def test_totp_seed_field_refused(self):
        with pytest.raises(LedgerError) as excinfo:
            load_ledger(fixture("secret_seed.yaml"))
        message = str(excinfo.value)
        assert "never stores secrets" in message
        assert "totp_seed" in message
        assert "id=mail" in message

    def test_recovery_codes_list_refused(self):
        with pytest.raises(LedgerError, match="recovery_codes"):
            load_ledger(fixture("secret_codes.yaml"))

    def test_otpauth_value_refused_under_innocent_field(self):
        raw = {"accounts": [{"id": "a", "notes": "otpauth://totp/x?secret=abc"}]}
        with pytest.raises(LedgerError, match="otpauth"):
            scan_for_secrets(raw, "inline")

    def test_base32_value_refused(self):
        with pytest.raises(LedgerError, match="base32"):
            scan_for_secrets({"notes": "JBSWY3DPEHPK3PXPJBSWY3DP"}, "inline")

    def test_digit_group_value_refused(self):
        with pytest.raises(LedgerError, match="recovery code"):
            scan_for_secrets({"notes": "1234-5678-9012"}, "inline")

    def test_ordinary_values_pass(self):
        scan_for_secrets(
            {
                "label": "YubiKey 5C NFC (daily carry)",
                "serial": "12345678",
                "acquired": "2025-03-01",
                "other_factors": ["recovery-codes", "totp-app"],
                "type": "yubico-otp",
            },
            "inline",
        )


class TestLoaderErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(LedgerNotFoundError, match="not found"):
            load_ledger(tmp_path / "nope.yaml")

    def test_broken_yaml_reports_position(self):
        with pytest.raises(LedgerError, match="not valid YAML"):
            load_ledger(fixture("not_yaml.yaml"))

    def test_top_level_must_be_mapping(self, tmp_path):
        path = tmp_path / "list.yaml"
        path.write_text("- 1\n- 2\n", encoding="utf-8")
        with pytest.raises(LedgerError, match="top level must be a mapping"):
            load_ledger(path)

    def test_validation_error_names_offending_account(self, tmp_path):
        path = tmp_path / "bad_tier.yaml"
        path.write_text(
            "version: 1\n"
            "keys: [{id: k1, label: K, vendor: other}]\n"
            "accounts: [{id: shop, label: Shop, tier: T9}]\n",
            encoding="utf-8",
        )
        with pytest.raises(LedgerError) as excinfo:
            load_ledger(path)
        message = str(excinfo.value)
        assert "id=shop" in message
        assert "tier" in message
