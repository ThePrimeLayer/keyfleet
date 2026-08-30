"""keyfleet CLI (typer). Commands per brief §8; exit codes per AGENTS.md §5:
0 clean · 1 findings at FAIL level (or invalid ledger, for `validate`) ·
2 tool/usage error (including a missing ledger file).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text

from keyfleet import report
from keyfleet.bundled import load_bundled
from keyfleet.checks import Level, run_checks
from keyfleet.impact import UnknownKeyError, analyze_lost
from keyfleet.model import Ledger, LedgerError, LedgerNotFoundError, load_ledger

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def main() -> None:
    """Local-first ledger for hardware security keys: what is registered where,
    and what breaks when a key is lost. Stores no secrets.
    """
    # The callback also keeps `keyfleet` a multi-command CLI even while only
    # one command exists (typer otherwise collapses single-command apps).


# markup=False: paths and ledger content must never be parsed as rich markup.
_out = Console(markup=False, highlight=False)
_err = Console(stderr=True, markup=False, highlight=False)

DEFAULT_LEDGER = Path("keyfleet.yaml")
LedgerArg = Annotated[Path, typer.Argument(help="Ledger YAML file.", show_default="keyfleet.yaml")]


def _load(path: Path, *, invalid_exit: int, hint: str | None = None) -> Ledger:
    # soft_wrap: keep message lines whole (grep-able) instead of re-wrapping.
    try:
        return load_ledger(path)
    except LedgerNotFoundError as exc:
        _err.print(str(exc), style="red", soft_wrap=True)
        raise typer.Exit(2) from exc
    except LedgerError as exc:
        _err.print(str(exc), style="red", soft_wrap=True)
        if hint:
            _err.print(hint, soft_wrap=True)
        raise typer.Exit(invalid_exit) from exc


@app.command()
def validate(ledger: LedgerArg = DEFAULT_LEDGER) -> None:
    """Validate LEDGER: YAML syntax, schema, referential integrity, no secret-looking content."""
    model = _load(ledger, invalid_exit=1)
    _out.print(
        Text.assemble(
            ("OK", "bold green"),
            f" {ledger}: {len(model.keys)} keys, {len(model.accounts)} accounts — ledger is valid.",
        ),
        soft_wrap=True,
    )


@app.command()
def check(
    ledger: LedgerArg = DEFAULT_LEDGER,
    json_: Annotated[
        bool, typer.Option("--json", help="Machine-readable findings on stdout.")
    ] = False,
) -> None:
    """Report policy violations and coverage gaps; exit 1 if any FAIL finding."""
    model = _load(ledger, invalid_exit=2, hint=f"Run `keyfleet validate {ledger}` for details.")
    findings = run_checks(model, bundled=load_bundled())
    exit_code = 1 if any(finding.level is Level.FAIL for finding in findings) else 0
    if json_:
        # Plain print: --json output must stay bare JSON on stdout.
        print(report.check_json(model, findings, exit_code, ledger_path=str(ledger)))
    else:
        report.render_check(model, findings, exit_code, _out)
    raise typer.Exit(exit_code)


@app.command()
def lost(
    key_id: Annotated[str, typer.Argument(metavar="KEY_ID", help="Id of the lost key.")],
    ledger: LedgerArg = DEFAULT_LEDGER,
    md: Annotated[bool, typer.Option("--md", help="Markdown checklist on stdout.")] = False,
) -> None:
    """Impact of losing KEY_ID: ordered de-registration checklist with links."""
    model = _load(ledger, invalid_exit=2, hint=f"Run `keyfleet validate {ledger}` for details.")
    try:
        result = analyze_lost(model, key_id)
    except UnknownKeyError as exc:
        _err.print(str(exc), style="red", soft_wrap=True)
        raise typer.Exit(2) from exc
    if md:
        print(report.lost_markdown(result, load_bundled()), end="")
    else:
        report.render_lost(result, load_bundled(), _out)
