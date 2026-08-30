"""Golden-file tests: exact CLI output for representative ledgers (brief §12).

Regenerate after intended output changes:
KEYFLEET_UPDATE_GOLDENS=1 uv run pytest -q, then review the diff.
"""

from __future__ import annotations

import json

from conftest import assert_golden, fixture
from typer.testing import CliRunner

from keyfleet.cli import app

runner = CliRunner()


class TestGoldenOutputs:
    def test_check_terminal_output(self):
        result = runner.invoke(app, ["check", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 1
        assert_golden(result.output, "check_min_keys_gap.txt")

    def test_check_json_output(self):
        path = str(fixture("min_keys_gap.yaml"))
        result = runner.invoke(app, ["check", "--json", path])
        assert result.exit_code == 1
        # Normalize the absolute path as it appears INSIDE the JSON (escaped),
        # so the golden is machine- and OS-independent.
        escaped = json.dumps(path)[1:-1]
        assert_golden(result.stdout.replace(escaped, "LEDGER"), "check_min_keys_gap.json")

    def test_report_markdown_output(self):
        result = runner.invoke(app, ["report", "--md", str(fixture("valid.yaml"))])
        assert result.exit_code == 0
        assert_golden(result.output, "report_valid.md")

    def test_lost_markdown_output(self):
        result = runner.invoke(app, ["lost", "k-main", "--md", str(fixture("min_keys_gap.yaml"))])
        assert result.exit_code == 0
        assert_golden(result.output, "lost_k_main.md")
