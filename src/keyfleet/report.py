"""Rendering for the terminal and JSON — the only layer that formats output.

Output shape follows brief §8's sample. Nothing here mutates the ledger or
decides exit codes; the CLI owns those.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text

from keyfleet.bundled import BundledData, discoverable_capacity, model_info_for_key
from keyfleet.checks import Finding, Level, covering_key_ids
from keyfleet.impact import AccountImpact, LostImpact
from keyfleet.model import KeyStatus, Ledger, Registration, RegistrationType, Tier

LEVEL_STYLES = {Level.FAIL: "bold red", Level.WARN: "bold yellow", Level.INFO: "bold cyan"}


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def ledger_header(ledger: Ledger, command: str = "check") -> str:
    """e.g. ``keyfleet check — 3 keys (2 active, 1 spare) · 14 accounts``."""
    by_status = Counter(key.status for key in ledger.keys)
    breakdown = ", ".join(f"{by_status[s]} {s.value}" for s in KeyStatus if by_status[s])
    keys = _plural(len(ledger.keys), "key")
    if breakdown:
        keys += f" ({breakdown})"
    return f"keyfleet {command} — {keys} · {_plural(len(ledger.accounts), 'account')}"


def summary_line(findings: list[Finding], exit_code: int) -> str:
    """e.g. ``2 fail, 2 warn, 2 info · exit 1``."""
    by_level = Counter(finding.level for finding in findings)
    return (
        f"{by_level[Level.FAIL]} fail, {by_level[Level.WARN]} warn, "
        f"{by_level[Level.INFO]} info · exit {exit_code}"
    )


def render_check(ledger: Ledger, findings: list[Finding], exit_code: int, console: Console) -> None:
    """Human-readable check report (brief §8 sample layout)."""
    console.print(ledger_header(ledger), style="bold", soft_wrap=True)
    console.print()
    for finding in findings:
        line = Text()
        line.append(f"{finding.level.value:<5}", style=LEVEL_STYLES[finding.level])
        line.append(" ")
        line.append(finding.message)
        console.print(line, soft_wrap=True)
    if findings:
        console.print()
    console.print(summary_line(findings, exit_code), soft_wrap=True)


def _settings_url(bundled: BundledData, service: str) -> str | None:
    info = bundled.services.get(service)
    return info.security_settings_url if info else None


def _deregister_actions(registrations: tuple[Registration, ...]) -> str:
    parts = []
    for registration in registrations:
        if registration.nickname:
            parts.append(f'delete "{registration.nickname}" ({registration.type.value})')
        else:
            parts.append(f"delete the {registration.type.value} registration")
    return "; ".join(parts)


def _after_loss(impact: AccountImpact) -> tuple[str, str]:
    """(text, rich style) describing the account's state after the loss."""
    if impact.inaccessible:
        return "INACCESSIBLE — 0 keys, no other factors", "bold red"
    state = f"{impact.remaining_keys}/{impact.required} keys"
    if impact.below_policy:
        return f"{state} — below policy", "yellow"
    return f"{state} — OK", "green"


def _lost_summary(result: LostImpact) -> str:
    inaccessible = sum(impact.inaccessible for impact in result.affected)
    below = sum(impact.below_policy and not impact.inaccessible for impact in result.affected)
    return (
        f"{_plural(len(result.affected), 'affected account')} "
        f"({inaccessible} inaccessible, {below} below policy) · "
        f"{result.unaffected_accounts} unaffected"
    )


def _lost_followup(result: LostImpact) -> str | None:
    if result.key.status in (KeyStatus.ACTIVE, KeyStatus.SPARE):
        return (
            f"Then set `status: lost` on {result.key.id} in the ledger and re-run `keyfleet check`."
        )
    return None


def render_lost(result: LostImpact, bundled: BundledData, console: Console) -> None:
    """De-registration checklist, ordered by tier then inaccessible-first."""
    key = result.key
    console.print(
        f'keyfleet lost — {key.id} "{key.label}" (status: {key.status.value})',
        style="bold",
        soft_wrap=True,
    )
    console.print()
    if not result.affected:
        console.print(
            f"{key.id} is registered on no accounts — nothing to de-register.", soft_wrap=True
        )
        return
    for position, impact in enumerate(result.affected, start=1):
        state, style = _after_loss(impact)
        line = Text()
        line.append(f"{position:>2}. ")
        line.append(f"{impact.tier.value} {impact.label}", style="bold")
        line.append(" — ")
        line.append(state, style=style)
        console.print(line, soft_wrap=True)
        console.print(
            f"    de-register: {_deregister_actions(impact.lost_registrations)}", soft_wrap=True
        )
        url = _settings_url(bundled, impact.service)
        console.print(
            f"    settings: {url or f'({impact.service}: no URL on file)'}", soft_wrap=True
        )
    console.print()
    console.print(_lost_summary(result), soft_wrap=True)
    followup = _lost_followup(result)
    if followup:
        console.print(followup, soft_wrap=True)


def lost_markdown(result: LostImpact, bundled: BundledData) -> str:
    """The same checklist as a markdown to-do list (``keyfleet lost --md``)."""
    key = result.key
    lines = [
        f'# Lost key: {key.id} — "{key.label}"',
        "",
        f"Ledger status: {key.status.value}. {_lost_summary(result)}.",
        "",
    ]
    if not result.affected:
        lines.append("Registered on no accounts — nothing to de-register.")
        return "\n".join(lines) + "\n"
    for impact in result.affected:
        state, _ = _after_loss(impact)
        url = _settings_url(bundled, impact.service)
        where = f"[security settings]({url})" if url else f"{impact.service} account settings"
        lines.append(
            f"- [ ] **{impact.tier} {impact.label}** — "
            f"{_deregister_actions(impact.lost_registrations)} at {where} "
            f"(after: {state})"
        )
    followup = _lost_followup(result)
    if followup:
        lines += ["", followup]
    return "\n".join(lines) + "\n"


# --- keyfleet report ---------------------------------------------------------

#: Short registration-type labels for matrix cells; the legend explains them.
TYPE_ABBREV = {
    RegistrationType.FIDO2_DISCOVERABLE: "disc",
    RegistrationType.FIDO2_NON_DISCOVERABLE: "fido2",
    RegistrationType.U2F: "u2f",
    RegistrationType.PIV: "piv",
    RegistrationType.OATH_TOTP: "totp",
    RegistrationType.YUBICO_OTP: "otp",
    RegistrationType.OPENPGP: "pgp",
}

_LEGEND = (
    "disc = FIDO2 discoverable (passkey) · fido2 = FIDO2 non-discoverable · "
    "totp = OATH-TOTP · otp = Yubico OTP · pgp = OpenPGP"
)


def report_data(ledger: Ledger, bundled: BundledData) -> dict[str, Any]:
    """Everything ``keyfleet report`` shows, as plain data (drives all formats)."""
    key_ids = [key.id for key in ledger.keys]
    accounts = []
    for account in ledger.accounts:
        by_key: dict[str, list[str]] = {}
        for registration in account.registrations:
            by_key.setdefault(registration.key, []).append(TYPE_ABBREV[registration.type])
        counted = len(covering_key_ids(ledger, account))
        required = ledger.policy.min_keys.for_tier(account.tier)
        accounts.append(
            {
                "account_id": account.id,
                "label": account.label,
                "tier": account.tier.value,
                "cells": {key_id: "+".join(by_key.get(key_id, [])) or None for key_id in key_ids},
                "keys": counted,
                "required": required,
                "meets_policy": counted >= required,
            }
        )
    tiers = []
    for tier in Tier:
        rows = [row for row in accounts if row["tier"] == tier.value]
        tiers.append(
            {
                "tier": tier.value,
                "accounts": len(rows),
                "meeting_policy": sum(row["meets_policy"] for row in rows),
                "min_keys": ledger.policy.min_keys.for_tier(tier),
            }
        )
    keys = []
    for key in ledger.keys:
        used_by = sum(
            1
            for account in ledger.accounts
            if any(registration.key == key.id for registration in account.registrations)
        )
        discoverable = sum(
            1
            for account in ledger.accounts
            for registration in account.registrations
            if registration.key == key.id
            and registration.type is RegistrationType.FIDO2_DISCOVERABLE
        )
        info = model_info_for_key(bundled.models, key)
        capacity = discoverable_capacity(info, key.firmware) if info else None
        keys.append(
            {
                "key_id": key.id,
                "label": key.label,
                "status": key.status.value,
                "accounts": used_by,
                "discoverable": discoverable,
                "discoverable_capacity": capacity,
            }
        )
    return {"matrix": {"keys": key_ids, "accounts": accounts}, "tiers": tiers, "keys": keys}


def _coverage_cell(row: dict[str, Any]) -> tuple[str, str]:
    mark = "OK" if row["meets_policy"] else "SHORT"
    return f"{row['keys']}/{row['required']} {mark}", (
        "green" if row["meets_policy"] else "bold red"
    )


def _discoverable_cell(row: dict[str, Any]) -> str:
    if row["discoverable_capacity"] is not None:
        return f"{row['discoverable']}/{row['discoverable_capacity']}"
    return str(row["discoverable"])


def render_report(ledger: Ledger, data: dict[str, Any], console: Console) -> None:
    """Terminal report: coverage matrix, per-tier summary, key utilization."""
    console.print(ledger_header(ledger, "report"), style="bold", soft_wrap=True)
    console.print()

    matrix = Table(title="Coverage matrix", title_justify="left")
    matrix.add_column("Account")
    matrix.add_column("Tier")
    for key_id in data["matrix"]["keys"]:
        matrix.add_column(key_id)
    matrix.add_column("Keys")
    for row in data["matrix"]["accounts"]:
        state, style = _coverage_cell(row)
        matrix.add_row(
            row["label"],
            row["tier"],
            *[row["cells"][key_id] or "—" for key_id in data["matrix"]["keys"]],
            Text(state, style=style),
        )
    console.print(matrix)
    console.print(_LEGEND, style="dim", soft_wrap=True)
    console.print()

    tiers = Table(title="Per-tier summary", title_justify="left")
    tiers.add_column("Tier")
    tiers.add_column("Accounts", justify="right")
    tiers.add_column("Meeting policy", justify="right")
    tiers.add_column("Min keys", justify="right")
    for row in data["tiers"]:
        tiers.add_row(
            row["tier"], str(row["accounts"]), str(row["meeting_policy"]), str(row["min_keys"])
        )
    console.print(tiers)
    console.print()

    keys = Table(title="Key utilization", title_justify="left")
    keys.add_column("Key")
    keys.add_column("Status")
    keys.add_column("Accounts", justify="right")
    keys.add_column("Discoverable", justify="right")
    for row in data["keys"]:
        keys.add_row(row["key_id"], row["status"], str(row["accounts"]), _discoverable_cell(row))
    console.print(keys)


def report_markdown(ledger: Ledger, data: dict[str, Any]) -> str:
    """The same report as markdown tables (``keyfleet report --md``)."""
    key_ids = data["matrix"]["keys"]
    lines = [f"# {ledger_header(ledger, 'report')}", "", "## Coverage matrix", ""]
    lines.append("| Account | Tier | " + " | ".join(key_ids) + " | Keys |")
    lines.append("|---|---|" + "---|" * len(key_ids) + "---|")
    for row in data["matrix"]["accounts"]:
        state, _ = _coverage_cell(row)
        cells = " | ".join(row["cells"][key_id] or "—" for key_id in key_ids)
        lines.append(f"| {row['label']} | {row['tier']} | {cells} | {state} |")
    lines += ["", f"_{_LEGEND}_", "", "## Per-tier summary", ""]
    lines.append("| Tier | Accounts | Meeting policy | Min keys |")
    lines.append("|---|---|---|---|")
    for row in data["tiers"]:
        lines.append(
            f"| {row['tier']} | {row['accounts']} | {row['meeting_policy']} | {row['min_keys']} |"
        )
    lines += ["", "## Key utilization", ""]
    lines.append("| Key | Status | Accounts | Discoverable |")
    lines.append("|---|---|---|---|")
    for row in data["keys"]:
        lines.append(
            f"| {row['key_id']} | {row['status']} | {row['accounts']} | {_discoverable_cell(row)} |"
        )
    return "\n".join(lines) + "\n"


def report_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2)


def check_json(ledger: Ledger, findings: list[Finding], exit_code: int, ledger_path: str) -> str:
    """Machine-readable check report for ``keyfleet check --json``."""
    by_level = Counter(finding.level for finding in findings)
    payload = {
        "ledger": {
            "path": ledger_path,
            "keys": len(ledger.keys),
            "accounts": len(ledger.accounts),
        },
        "findings": [
            {
                "level": finding.level.value,
                "check": finding.check,
                "message": finding.message,
                "account_id": finding.account_id,
                "key_id": finding.key_id,
            }
            for finding in findings
        ],
        "summary": {
            "fail": by_level[Level.FAIL],
            "warn": by_level[Level.WARN],
            "info": by_level[Level.INFO],
        },
        "exit_code": exit_code,
    }
    return json.dumps(payload, indent=2)
