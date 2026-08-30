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
