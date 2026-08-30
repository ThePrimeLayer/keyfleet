"""CLI behavior: exit codes and user-facing output."""

from __future__ import annotations

import contextlib
import json

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


class TestCheck:
    def test_clean_ledger_exits_0(self):
        result = runner.invoke(app, ["check", str(fixture("valid.yaml"))])
        assert result.exit_code == 0, all_output(result)
        assert "keyfleet check — 3 keys (2 active, 1 spare) · 3 accounts" in result.output
        assert "0 fail, 0 warn, 0 info · exit 0" in result.output

    def test_gaps_exit_1_and_render_fail_lines(self):
        result = runner.invoke(app, ["check", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 1
        assert (
            'FAIL  T0 "Primary email (Google)" has 1 hardware key registered; '
            "policy requires 3" in result.output
        )
        assert "2 fail, 0 warn, 0 info · exit 1" in result.output

    def test_json_output_is_parseable_and_complete(self):
        result = runner.invoke(app, ["check", "--json", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["summary"] == {"fail": 2, "warn": 0, "info": 0}
        assert payload["exit_code"] == 1
        assert payload["ledger"]["keys"] == 3
        assert {finding["account_id"] for finding in payload["findings"]} == {"g-mail", "repo"}
        assert all(finding["level"] == "FAIL" for finding in payload["findings"])

    def test_invalid_ledger_exits_2_with_validate_hint(self):
        result = runner.invoke(app, ["check", str(fixture("bad_ref.yaml"))])
        assert result.exit_code == 2
        assert "keyfleet validate" in all_output(result)

    def test_missing_file_exits_2(self, tmp_path):
        result = runner.invoke(app, ["check", str(tmp_path / "absent.yaml")])
        assert result.exit_code == 2
