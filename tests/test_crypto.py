"""Encrypted-ledger support. The round-trip tests are skipped when the `age`
binary is absent (AGENTS.md §7); the resolution tests always run."""

from __future__ import annotations

import shutil
import subprocess

import pytest
from conftest import fixture

from keyfleet import crypto
from keyfleet.crypto import load_ledger_auto
from keyfleet.model import LedgerError, LedgerNotFoundError

AGE = shutil.which("age")
AGE_KEYGEN = shutil.which("age-keygen")
needs_age = pytest.mark.skipif(not (AGE and AGE_KEYGEN), reason="age / age-keygen not installed")


class TestResolution:
    def test_plain_ledger_loads_normally(self):
        assert len(load_ledger_auto(fixture("valid.yaml")).keys) == 3

    def test_missing_both_variants_mentions_age_name(self, tmp_path):
        with pytest.raises(LedgerNotFoundError, match=r"nope\.yaml\.age"):
            load_ledger_auto(tmp_path / "nope.yaml")

    def test_age_file_without_age_cli_gives_install_hint(self, tmp_path, monkeypatch):
        monkeypatch.setattr(crypto.shutil, "which", lambda _name: None)
        encrypted = tmp_path / "keyfleet.yaml.age"
        encrypted.write_bytes(b"age-encryption.org/v1\n")
        with pytest.raises(LedgerError, match="`age` CLI is not on PATH"):
            load_ledger_auto(encrypted)

    def test_fallback_to_age_sibling_requires_age(self, tmp_path, monkeypatch):
        # keyfleet.yaml absent + keyfleet.yaml.age present must take the age
        # path (proved here by hitting the age-missing error, not not-found).
        monkeypatch.setattr(crypto.shutil, "which", lambda _name: None)
        (tmp_path / "keyfleet.yaml.age").write_bytes(b"age-encryption.org/v1\n")
        with pytest.raises(LedgerError, match="age-encrypted ledger"):
            load_ledger_auto(tmp_path / "keyfleet.yaml")


@needs_age
class TestRoundTrip:
    @pytest.fixture()
    def identity(self, tmp_path, monkeypatch):
        identity_file = tmp_path / "identity.txt"
        subprocess.run(
            [AGE_KEYGEN, "-o", str(identity_file)], check=True, capture_output=True, text=True
        )
        content = identity_file.read_text(encoding="utf-8")
        public_key = next(
            line.split(":", 1)[1].strip()
            for line in content.splitlines()
            if line.lower().startswith("# public key:")
        )
        monkeypatch.setenv(crypto.IDENTITY_ENV, str(identity_file))
        return public_key

    def encrypt(self, public_key: str, target) -> None:
        subprocess.run(
            [AGE, "-r", public_key, "-o", str(target), str(fixture("valid.yaml"))],
            check=True,
            capture_output=True,
        )

    def test_explicit_age_path_decrypts_to_memory(self, tmp_path, identity):
        encrypted = tmp_path / "ledger.yaml.age"
        self.encrypt(identity, encrypted)
        ledger = load_ledger_auto(encrypted)
        assert [key.id for key in ledger.keys] == ["yk-a", "yk-b", "spare-c"]
        # Decrypt-to-memory only: no plaintext sibling may appear on disk.
        assert not (tmp_path / "ledger.yaml").exists()

    def test_plain_path_falls_back_to_age_sibling(self, tmp_path, identity):
        self.encrypt(identity, tmp_path / "keyfleet.yaml.age")
        ledger = load_ledger_auto(tmp_path / "keyfleet.yaml")
        assert len(ledger.accounts) == 3

    def test_cli_validate_reads_age_ledger(self, tmp_path, identity):
        from typer.testing import CliRunner

        from keyfleet.cli import app

        encrypted = tmp_path / "keyfleet.yaml.age"
        self.encrypt(identity, encrypted)
        result = CliRunner().invoke(app, ["validate", str(encrypted)])
        assert result.exit_code == 0, result.output
        assert "3 keys, 3 accounts" in result.output

    def test_wrong_identity_fails_clearly(self, tmp_path, identity, monkeypatch):
        encrypted = tmp_path / "ledger.yaml.age"
        self.encrypt(identity, encrypted)
        other_identity = tmp_path / "other.txt"
        subprocess.run(
            [AGE_KEYGEN, "-o", str(other_identity)], check=True, capture_output=True, text=True
        )
        monkeypatch.setenv(crypto.IDENTITY_ENV, str(other_identity))
        with pytest.raises(LedgerError, match="age decryption failed"):
            load_ledger_auto(encrypted)
