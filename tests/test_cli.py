"""CLI behavior: exit codes and user-facing output."""

from __future__ import annotations

import contextlib

from conftest import fixture
from typer.testing import CliRunner

from keyfleet.cli import app

runner = CliRunner()


def all_output(result) -> str:
    """stdout plus stderr, tolerant of click versions that merge or split them."""
    out = result.output
    with contextlib.suppress(ValueError, AttributeError):
        out += result.stderr
    return out


class TestHelp:
    def test_help_lists_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.output


class TestValidate:
    def test_valid_ledger_exits_0(self):
        result = runner.invoke(app, ["validate", str(fixture("valid.yaml"))])
        assert result.exit_code == 0, all_output(result)
        assert "OK" in result.output
        assert "3 keys, 3 accounts" in result.output

    def test_invalid_ledger_exits_1(self):
        result = runner.invoke(app, ["validate", str(fixture("bad_ref.yaml"))])
        assert result.exit_code == 1
        assert 'unknown key "yk-zz"' in all_output(result)

    def test_secret_ledger_exits_1(self):
        result = runner.invoke(app, ["validate", str(fixture("secret_seed.yaml"))])
        assert result.exit_code == 1
        assert "never stores secrets" in all_output(result)

    def test_missing_file_exits_2(self, tmp_path):
        result = runner.invoke(app, ["validate", str(tmp_path / "absent.yaml")])
        assert result.exit_code == 2
        assert "not found" in all_output(result)

    def test_default_ledger_path_used_when_omitted(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["validate"])
        assert result.exit_code == 2
        assert "keyfleet.yaml" in all_output(result)
