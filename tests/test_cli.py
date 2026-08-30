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


class TestReport:
    def test_terminal_report_shows_three_sections(self):
        result = runner.invoke(app, ["report", str(fixture("valid.yaml"))])
        assert result.exit_code == 0, all_output(result)
        out = result.output
        assert "keyfleet report — 3 keys (2 active, 1 spare) · 3 accounts" in out
        for section in ("Coverage matrix", "Per-tier summary", "Key utilization"):
            assert section in out

    def test_markdown_report_has_matrix_and_capacity(self):
        result = runner.invoke(app, ["report", "--md", str(fixture("valid.yaml"))])
        assert result.exit_code == 0
        out = result.output
        assert "## Coverage matrix" in out
        assert "| Password manager | T0 | fido2 | fido2 | fido2 | 3/3 OK |" in out
        # yk-a is a YubiKey 5C NFC on 5.7.1 → capacity 100 via bundled models.yaml.
        assert "| yk-a | active | 3 | 1/100 |" in out

    def test_json_report_parses_and_carries_matrix(self):
        result = runner.invoke(app, ["report", "--json", str(fixture("valid.yaml"))])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["matrix"]["keys"] == ["yk-a", "yk-b", "spare-c"]
        assert len(payload["matrix"]["accounts"]) == 3
        vault = payload["matrix"]["accounts"][0]
        assert vault["meets_policy"] is True
        assert vault["cells"]["yk-a"] == "fido2"
        tiers = {row["tier"]: row for row in payload["tiers"]}
        assert tiers["T0"]["accounts"] == 1 and tiers["T0"]["meeting_policy"] == 1

    def test_md_and_json_together_is_usage_error(self):
        result = runner.invoke(app, ["report", "--md", "--json", str(fixture("valid.yaml"))])
        assert result.exit_code == 2


class TestAdvisories:
    def test_lists_matches_and_firmware_prompts(self):
        result = runner.invoke(app, ["advisories", str(fixture("valid.yaml"))])
        assert result.exit_code == 0, all_output(result)
        out = result.output
        assert "2 affected keys · 1 without firmware set" in out
        assert "YSA-2024-03" in out
        assert "https://www.yubico.com/support/security-advisories/ysa-2024-03/" in out
        assert "spare-c" in out and "set `firmware:`" in out

    def test_clean_ledger_reports_no_matches(self, tmp_path):
        path = tmp_path / "ledger.yaml"
        path.write_text(
            "version: 1\nkeys: [{id: k1, label: K, vendor: other, firmware: '1.0'}]\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["advisories", str(path)])
        assert result.exit_code == 0
        assert "No keys match any advisory on file." in result.output


class TestServices:
    def test_full_table_lists_bundled_services(self):
        result = runner.invoke(app, ["services"])
        assert result.exit_code == 0
        assert "Bundled services (32)" in result.output
        assert "github" in result.output

    def test_search_filters_by_substring(self):
        result = runner.invoke(app, ["services", "--search", "git"])
        assert result.exit_code == 0
        assert "github" in result.output
        assert "gitlab" in result.output
        assert "discord" not in result.output

    def test_search_miss_says_so(self):
        result = runner.invoke(app, ["services", "--search", "zzznope"])
        assert result.exit_code == 0
        assert 'No bundled service matches "zzznope"' in result.output


class TestInit:
    def test_fresh_directory_gets_example_and_gitignore(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, all_output(result)
        assert (tmp_path / "keyfleet.example.yaml").is_file()
        gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert "keyfleet.yaml" in gitignore.splitlines()
        assert "Next: copy keyfleet.example.yaml" in result.output

    def test_written_example_validates(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["validate", "keyfleet.example.yaml"])
        assert result.exit_code == 0, all_output(result)

    def test_rerun_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert "already exists" in result.output
        gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert gitignore.splitlines().count("keyfleet.yaml") == 1

    def test_appends_to_existing_gitignore_without_trailing_newline(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".gitignore").write_text(".venv/", encoding="utf-8")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        lines = (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()
        assert lines[0] == ".venv/"
        assert "keyfleet.yaml" in lines

    def test_messages_name_absolute_paths(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert str(tmp_path / "keyfleet.example.yaml") in result.output

    def test_unwritable_directory_fails_cleanly(self, tmp_path, monkeypatch):
        # Simulates a terminal opened in an unwritable directory (the Windows
        # System32 default): exit 2, a cd hint, and no traceback.
        from pathlib import Path

        monkeypatch.chdir(tmp_path)

        def denied(self, *args, **kwargs):
            raise PermissionError(13, "Permission denied", str(self))

        monkeypatch.setattr(Path, "write_text", denied)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 2
        out = all_output(result)
        assert "is not writable" in out
        assert "Permission denied" in out
        assert "cd to where your ledger should live" in out
        assert "Traceback" not in out
