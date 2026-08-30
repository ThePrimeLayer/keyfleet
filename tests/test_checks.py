"""Cross-check behavior: run_checks ordering and shared coverage helpers.
Per-check positive/negative cases live in test_check_*.py, one module each."""

from __future__ import annotations

from conftest import fixture, make_account, make_ledger

from keyfleet.checks import Level, covering_key_ids, run_checks
from keyfleet.model import load_ledger


class TestRunChecks:
    def test_clean_ledger_has_no_findings(self):
        ledger = load_ledger(fixture("valid.yaml"))
        assert run_checks(ledger) == []

    def test_findings_ordered_fail_then_warn_then_info(self):
        # One account triggers min-keys + lost-retired (FAIL), a policy-warned
        # sms factor and the unregistered default spare (WARN), and a missing
        # recovery-code pointer (INFO).
        ledger = make_ledger(
            [make_account("T0", ["k-lost"], id="mail", label="Mail", other_factors=["sms"])]
        )
        levels = [finding.level for finding in run_checks(ledger)]
        assert levels == [Level.FAIL, Level.FAIL, Level.WARN, Level.WARN, Level.INFO]


class TestCoverageHelper:
    def test_covering_key_ids_filters_by_status(self):
        ledger = make_ledger([make_account("T1", ["k-active", "k-spare", "k-lost", "k-retired"])])
        assert covering_key_ids(ledger, ledger.accounts[0]) == {"k-active", "k-spare"}
