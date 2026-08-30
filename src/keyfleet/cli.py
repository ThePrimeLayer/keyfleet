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
from keyfleet.bundled import example_ledger_text, load_bundled, match_advisories
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


@app.command("report")
def report_cmd(
    ledger: LedgerArg = DEFAULT_LEDGER,
    md: Annotated[bool, typer.Option("--md", help="Markdown tables on stdout.")] = False,
    json_: Annotated[
        bool, typer.Option("--json", help="Machine-readable report on stdout.")
    ] = False,
) -> None:
    """Coverage matrix (accounts x keys), per-tier summary, key utilization."""
    if md and json_:
        _err.print("choose one of --md or --json, not both", style="red")
        raise typer.Exit(2)
    model = _load(ledger, invalid_exit=2, hint=f"Run `keyfleet validate {ledger}` for details.")
    data = report.report_data(model, load_bundled())
    if json_:
        print(report.report_json(data))
    elif md:
        print(report.report_markdown(model, data), end="")
    else:
        report.render_report(model, data, _out)


@app.command()
def advisories(ledger: LedgerArg = DEFAULT_LEDGER) -> None:
    """Keys matching known vendor advisories (bundled list plus ledger extras)."""
    model = _load(ledger, invalid_exit=2, hint=f"Run `keyfleet validate {ledger}` for details.")
    report.render_advisories(match_advisories(model, load_bundled()), _out)


@app.command()
def services(
    search: Annotated[
        str | None, typer.Option("--search", help="Substring filter on service id or name.")
    ] = None,
) -> None:
    """The bundled service table: settings URLs, key limits, passkey support."""
    bundled = load_bundled()
    selected = {
        service_id: service
        for service_id, service in bundled.services.items()
        if search is None
        or search.lower() in service_id.lower()
        or search.lower() in service.name.lower()
    }
    if not selected:
        _out.print(
            f'No bundled service matches "{search}". Use service: other in the ledger, '
            "or contribute the entry (see AGENTS.md §6).",
            soft_wrap=True,
        )
        return
    report.render_services(selected, _out)


_GITIGNORE_ENTRY = "keyfleet.yaml"


@app.command()
def init() -> None:
    """Write keyfleet.example.yaml here and gitignore keyfleet.yaml (never commit a real ledger)."""
    example = Path("keyfleet.example.yaml")
    if example.exists():
        _out.print(f"{example} already exists — leaving it untouched.", soft_wrap=True)
    else:
        example.write_text(example_ledger_text(), encoding="utf-8")
        _out.print(f"Wrote {example} (fictional).", soft_wrap=True)

    gitignore = Path(".gitignore")
    if gitignore.exists():
        lines = gitignore.read_text(encoding="utf-8").splitlines()
        if _GITIGNORE_ENTRY in (line.strip() for line in lines):
            _out.print(f".gitignore already covers {_GITIGNORE_ENTRY}.", soft_wrap=True)
        else:
            content = "\n".join(
                [*lines, "# keyfleet: never commit a real ledger", _GITIGNORE_ENTRY]
            )
            gitignore.write_text(content + "\n", encoding="utf-8")
            _out.print(f"Added {_GITIGNORE_ENTRY} to .gitignore.", soft_wrap=True)
    else:
        gitignore.write_text(
            f"# keyfleet: never commit a real ledger\n{_GITIGNORE_ENTRY}\n", encoding="utf-8"
        )
        _out.print(f"Created .gitignore with {_GITIGNORE_ENTRY}.", soft_wrap=True)

    _out.print(
        "\nNext: copy keyfleet.example.yaml to keyfleet.yaml, make it yours, then run "
        "`keyfleet validate` and `keyfleet check`. The ledger maps which keys guard "
        "which accounts — treat it as sensitive and keep it encrypted where possible.",
        soft_wrap=True,
    )
