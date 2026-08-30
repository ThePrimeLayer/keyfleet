"""Bundled reference data: services.yaml, models.yaml, advisories.yaml.

Every entry in the data files carries ``source_url`` and ``verified`` — facts
are read from the vendor's/service's own pages, never guessed (AGENTS.md §6).
Loading happens once via :func:`load_bundled`; checks receive the result as a
plain argument so they stay pure.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache
from importlib import resources
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from keyfleet.model import (
    Advisory,
    Capability,
    Interface,
    Key,
    LedgerError,
    StrictModel,
    Vendor,
)

_URL_PATTERN = r"^https?://\S+$"


class CapacityRule(StrictModel):
    """Discoverable-credential capacity for a firmware range (lt exclusive, ge inclusive)."""

    firmware_lt: str | None = None
    firmware_ge: str | None = None
    capacity: int = Field(ge=0)


class KeyModelInfo(StrictModel):
    """One hardware-key model family in models.yaml."""

    id: str
    vendor: Vendor
    family: str = Field(
        min_length=1,
        description="Case-insensitive prefix matched against Key.model; longest family wins.",
    )
    capabilities: list[Capability] | None = None
    interfaces: list[Interface] | None = None
    discoverable_capacity: int | list[CapacityRule] | None = None
    source_url: str = Field(pattern=_URL_PATTERN)
    verified: dt.date
    notes: str = ""


class ServiceInfo(StrictModel):
    """One service entry in services.yaml."""

    name: str = Field(min_length=1)
    security_settings_url: str | None = Field(None, pattern=_URL_PATTERN)
    max_keys: int | None = Field(None, ge=0)
    fido2_discoverable: bool | None = None
    notes: str = ""
    source_url: str = Field(pattern=_URL_PATTERN)
    verified: dt.date


class BundledData(BaseModel):
    """All bundled reference data, loaded once and passed around."""

    services: dict[str, ServiceInfo] = Field(default_factory=dict)
    models: list[KeyModelInfo] = Field(default_factory=list)
    advisories: list[Advisory] = Field(default_factory=list)


def _read_data_yaml(name: str) -> Any:
    file = resources.files("keyfleet").joinpath("data", name)
    try:
        text = file.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LedgerError(f"bundled data file {name} is missing from the package") from exc
    return yaml.safe_load(text)


@lru_cache(maxsize=1)
def load_bundled() -> BundledData:
    """Load and validate the three bundled data files."""
    try:
        return BundledData.model_validate(
            {
                "services": (_read_data_yaml("services.yaml") or {}).get("services", {}),
                "models": (_read_data_yaml("models.yaml") or {}).get("models", []),
                "advisories": (_read_data_yaml("advisories.yaml") or {}).get("advisories", []),
            }
        )
    except ValidationError as exc:
        raise LedgerError(f"bundled data is invalid (packaging bug):\n{exc}") from exc


def services_markdown(bundled: BundledData) -> str:
    """The generated docs/SERVICES.md content."""
    lines = [
        "# Services",
        "",
        "Generated from `src/keyfleet/data/services.yaml` — do not edit by hand;",
        "regenerate with `uv run python scripts/gen_services_md.py`.",
        "",
        "Every fact comes from the service's own page (*source*), read on the",
        "*verified* date. `—` means the service documents no such fact; `?` means",
        "the page does not say either way.",
        "",
        "| Service | Security-key settings | Max keys | Passkeys | Source | Verified |",
        "|---|---|---|---|---|---|",
    ]
    for service_id, service in bundled.services.items():
        settings = (
            f"[settings]({service.security_settings_url})" if service.security_settings_url else "—"
        )
        max_keys = "—" if service.max_keys is None else str(service.max_keys)
        passkeys = {True: "yes", False: "no", None: "?"}[service.fido2_discoverable]
        lines.append(
            f"| {service.name} (`{service_id}`) | {settings} | {max_keys} "
            f"| {passkeys} | [source]({service.source_url}) | {service.verified} |"
        )
    lines += ["", f"{len(bundled.services)} services."]
    return "\n".join(lines) + "\n"


def firmware_tuple(firmware: str) -> tuple[int, ...]:
    """'5.7.1' → (5, 7, 1). Non-numeric segment suffixes are ignored ('4a' → 4)."""
    parts: list[int] = []
    for segment in firmware.strip().split("."):
        digits = ""
        for char in segment:
            if char.isdigit():
                digits += char
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def firmware_in_range(
    firmware: str, *, firmware_ge: str | None = None, firmware_lt: str | None = None
) -> bool:
    """Inclusive lower bound, exclusive upper bound; missing bounds are open."""
    value = firmware_tuple(firmware)
    if firmware_ge is not None and value < firmware_tuple(firmware_ge):
        return False
    return not (firmware_lt is not None and value >= firmware_tuple(firmware_lt))


def model_info_for_key(models: list[KeyModelInfo], key: Key) -> KeyModelInfo | None:
    """The models.yaml entry for a ledger key: same vendor, longest family prefix."""
    if not key.model:
        return None
    name = key.model.strip().lower()
    candidates = [
        info
        for info in models
        if info.vendor is key.vendor and name.startswith(info.family.lower())
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda info: len(info.family))


def discoverable_capacity(info: KeyModelInfo, firmware: str | None) -> int | None:
    """Resolve a key's discoverable-credential capacity, or None if indeterminate."""
    rules = info.discoverable_capacity
    if rules is None or isinstance(rules, int):
        return rules
    if firmware is None:
        capacities = {rule.capacity for rule in rules}
        return capacities.pop() if len(capacities) == 1 else None
    for rule in rules:
        if firmware_in_range(firmware, firmware_ge=rule.firmware_ge, firmware_lt=rule.firmware_lt):
            return rule.capacity
    return None
