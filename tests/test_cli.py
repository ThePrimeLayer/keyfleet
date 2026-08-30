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
        assert (
            "FAIL  Key k-lost is LOST but still registered on 1 account "
            "→ run: keyfleet lost k-lost" in result.output
        )
        assert "3 fail, 0 warn, 2 info · exit 1" in result.output

    def test_json_output_is_parseable_and_complete(self):
        result = runner.invoke(app, ["check", "--json", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["summary"] == {"fail": 3, "warn": 0, "info": 2}
        assert payload["exit_code"] == 1
        assert payload["ledger"]["keys"] == 3
        fails = [finding for finding in payload["findings"] if finding["level"] == "FAIL"]
        assert {finding["account_id"] for finding in fails} == {"g-mail", "repo", None}
        assert {finding["key_id"] for finding in fails} == {None, "k-lost"}
        infos = [finding for finding in payload["findings"] if finding["level"] == "INFO"]
        assert {finding["check"] for finding in infos} == {"recovery-codes"}

    def test_invalid_ledger_exits_2_with_validate_hint(self):
        result = runner.invoke(app, ["check", str(fixture("bad_ref.yaml"))])
        assert result.exit_code == 2
        assert "keyfleet validate" in all_output(result)

    def test_missing_file_exits_2(self, tmp_path):
        result = runner.invoke(app, ["check", str(tmp_path / "absent.yaml")])
        assert result.exit_code == 2


class TestLost:
    def test_checklist_orders_by_tier_and_links_settings(self):
        result = runner.invoke(app, ["lost", "k-main", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 0, all_output(result)
        out = result.output
        assert 'keyfleet lost — k-main "Main key" (status: active)' in out
        # g-mail (T0) must precede repo (T1); google's settings URL comes
        # from the bundled services.yaml.
        assert out.index("Primary email") < out.index("Code hosting")
        assert "myaccount.google.com" in out
        assert "affected account" in out

    def test_md_variant_emits_markdown_checklist(self):
        result = runner.invoke(app, ["lost", "k-main", "--md", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 0
        assert result.output.startswith('# Lost key: k-main — "Main key"')
        assert "- [ ] **T0 Primary email (Google)**" in result.output
        assert 'delete "main" (fido2-discoverable)' in result.output
        assert "set `status: lost` on k-main" in result.output

    def test_unknown_key_exits_2_listing_known_ids(self):
        result = runner.invoke(app, ["lost", "k-nope", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 2
        assert 'no key with id "k-nope"' in all_output(result)
        assert "k-desk" in all_output(result)

    def test_low_impact_key_still_reports(self):
        result = runner.invoke(app, ["lost", "k-desk", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 0
        assert "Chat" in result.output

    def test_unregistered_key_says_nothing_to_deregister(self, tmp_path):
        path = tmp_path / "ledger.yaml"
        path.write_text(
            "version: 1\nkeys: [{id: k-solo, label: Solo, vendor: other}]\naccounts: []\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["lost", "k-solo", str(path)])
        assert result.exit_code == 0
        assert "nothing to de-register" in result.output
