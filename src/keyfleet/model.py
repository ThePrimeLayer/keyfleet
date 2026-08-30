"""Pydantic models for the keyfleet ledger, plus loading and validation helpers.

Schema reference: keyfleet-BRIEF.md §7. ``schema/keyfleet.schema.json`` is
generated from these models — after any model change run
``uv run python scripts/gen_schema.py`` (a test fails when the file drifts).

:func:`load_ledger` is the single entry point for reading a ledger file: it
parses YAML, refuses secret-looking content, validates the schema and
referential integrity, and reports problems naming the file, the offending
key/account id, and the field.
"""

from __future__ import annotations

import datetime as dt
import re
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)


class LedgerError(ValueError):
    """A ledger failed to parse or validate. The message is user-facing."""


class LedgerNotFoundError(LedgerError):
    """The ledger file does not exist or cannot be read."""


class Vendor(StrEnum):
    YUBICO = "yubico"
    GOOGLE = "google"
    TILLITIS = "tillitis"
    NITROKEY = "nitrokey"
    SOLOKEYS = "solokeys"
    FEITIAN = "feitian"
    OTHER = "other"


class Interface(StrEnum):
    USB_A = "usb-a"
    USB_C = "usb-c"
    NFC = "nfc"
    LIGHTNING = "lightning"
    BLUETOOTH = "bluetooth"


class Capability(StrEnum):
    FIDO2 = "fido2"
    U2F = "u2f"
    PIV = "piv"
    OATH = "oath"
    OTP = "otp"
    OPENPGP = "openpgp"


class KeyStatus(StrEnum):
    ACTIVE = "active"
    SPARE = "spare"
    LOST = "lost"
    RETIRED = "retired"


class Tier(StrEnum):
    """T0 root of trust · T1 important · T2 nice-to-have."""

    T0 = "T0"
    T1 = "T1"
    T2 = "T2"


class RegistrationType(StrEnum):
    FIDO2_DISCOVERABLE = "fido2-discoverable"
    FIDO2_NON_DISCOVERABLE = "fido2-non-discoverable"
    U2F = "u2f"
    PIV = "piv"
    OATH_TOTP = "oath-totp"
    YUBICO_OTP = "yubico-otp"
    OPENPGP = "openpgp"


class Factor(StrEnum):
    """Non-hardware-key second factors an account may also have."""

    TOTP_APP = "totp-app"
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    RECOVERY_CODES = "recovery-codes"
    SYNCED_PASSKEY = "synced-passkey"


class StrictModel(BaseModel):
    """Base for all ledger models: unknown fields are always an error."""

    model_config = ConfigDict(extra="forbid")


_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"

#: YAML may carry numeric serials; normalize to str so comparisons never
#: depend on how the value was quoted.
Serial = Annotated[str | int | None, AfterValidator(lambda v: v if v is None else str(v))]


class Key(StrictModel):
    """One hardware security key."""

    id: str = Field(pattern=_ID_PATTERN, description="Short stable id, referenced by accounts.")
    label: str = Field(min_length=1, description="Human name, e.g. 'YubiKey 5C NFC (daily carry)'.")
    vendor: Vendor
    model: str | None = Field(None, description="Vendor model name; keys into models.yaml (M1).")
    firmware: str | None = Field(None, description="Optional; used for advisories and capacity.")
    serial: Serial = Field(None, description="Optional; the ledger is local-only anyway.")
    interfaces: list[Interface] = Field(default_factory=list)
    capabilities: list[Capability] = Field(default_factory=list)
    status: KeyStatus = KeyStatus.ACTIVE
    holder: str | None = None
    location: str | None = None
    acquired: dt.date | None = None
    notes: str = ""


class Registration(StrictModel):
    """One credential registered on one key for one account."""

    key: str = Field(description="Id of a key in the `keys` list.")
    type: RegistrationType
    registered: dt.date | None = None
    nickname: str | None = Field(
        None, description="Name shown in the service's UI, so you know which entry to delete."
    )


class RecoveryCodesPointer(StrictModel):
    """A pointer to where recovery codes are stored — never the codes."""

    stored: bool
    where: str | None = Field(None, description="e.g. 'password manager, item X'. Never the codes.")


class Account(StrictModel):
    """One account and the credentials registered on it."""

    id: str = Field(pattern=_ID_PATTERN)
    service: str = Field("other", description="Key into services.yaml, or 'other'.")
    label: str = Field(min_length=1)
    tier: Tier
    registrations: list[Registration] = Field(default_factory=list)
    other_factors: list[Factor] = Field(default_factory=list)
    recovery_codes: RecoveryCodesPointer | None = None
    notes: str = ""


class MinKeys(StrictModel):
    """Required registered-key count per tier. Partial overrides keep defaults."""

    T0: int = Field(3, ge=0)
    T1: int = Field(2, ge=0)
    T2: int = Field(1, ge=0)

    def for_tier(self, tier: Tier) -> int:
        return int(getattr(self, tier.value))


class Policy(StrictModel):
    """Checkable policy. Defaults follow brief §7 (owner question §15.2)."""

    min_keys: MinKeys = Field(default_factory=MinKeys)
    require_recovery_codes_for: list[Tier] = Field(
        default_factory=lambda: [Tier.T0, Tier.T1],
        description="Tiers whose accounts must carry a recovery-codes pointer.",
    )
    warn_factors: dict[Tier, list[Factor]] = Field(
        default_factory=lambda: {Tier.T0: [Factor.SMS, Factor.EMAIL]},
        description="Weak factors that should not exist on accounts of a tier.",
    )


class Affects(StrictModel):
    """Firmware range an advisory applies to (inclusive lower, exclusive upper)."""

    firmware_lt: str | None = None
    firmware_ge: str | None = None


class Advisory(StrictModel):
    """A vendor security advisory, maintained by hand — never fetched."""

    id: str = Field(pattern=_ID_PATTERN)
    vendor: Vendor
    affects: Affects = Field(default_factory=Affects)
    summary: str = ""
    url: str = Field(pattern=r"^https?://", description="Link to the vendor's advisory page.")
    verified: dt.date | None = Field(
        None, description="When the affected ranges were read from the advisory page."
    )
    notes: str = ""


class Ledger(StrictModel):
    """A keyfleet ledger: keys, accounts, registrations, policy — never secrets."""

    version: Literal[1] = 1
    keys: list[Key] = Field(default_factory=list)
    accounts: list[Account] = Field(default_factory=list)
    policy: Policy = Field(default_factory=Policy)
    advisories: list[Advisory] = Field(default_factory=list)

    @model_validator(mode="after")
    def _referential_integrity(self) -> Ledger:
        problems: list[str] = []
        for kind, items in (
            ("key", self.keys),
            ("account", self.accounts),
            ("advisory", self.advisories),
        ):
            seen: set[str] = set()
            for item in items:
                if item.id in seen:
                    problems.append(f'duplicate {kind} id "{item.id}" — {kind} ids must be unique')
                seen.add(item.id)
        key_ids = {key.id for key in self.keys}
        for account in self.accounts:
            for registration in account.registrations:
                if registration.key not in key_ids:
                    known = ", ".join(sorted(key_ids)) or "none defined"
                    problems.append(
                        f'account "{account.id}": registration references unknown key '
                        f'"{registration.key}" (known keys: {known})'
                    )
        if problems:
            raise ValueError("; ".join(problems))
        return self


def ledger_json_schema() -> dict[str, Any]:
    """The JSON Schema published as schema/keyfleet.schema.json."""
    schema = Ledger.model_json_schema()
    schema["title"] = "keyfleet ledger"
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://raw.githubusercontent.com/ThePrimeLayer/keyfleet/main/schema/keyfleet.schema.json",
        **schema,
    }


# --- Secret rejection (brief §13) -------------------------------------------
# The ledger is a map, never a store of secrets. Before schema validation we
# scan the raw YAML and refuse anything that looks like a stored secret.

_SECRET_NAME_SEGMENTS = frozenset(
    {
        "secret",
        "secrets",
        "seed",
        "seeds",
        "totp",
        "otp",
        "pin",
        "pins",
        "password",
        "passwd",
        "code",
        "codes",
        "token",
        "tokens",
    }
)
#: Schema fields whose names would trip the segment heuristic but are safe by
#: construction (values are tier names / a pointer mapping, never secrets).
_ALLOWLISTED_FIELD_NAMES = frozenset({"require_recovery_codes_for"})

_OTPAUTH_RE = re.compile(r"otpauth://", re.IGNORECASE)
_BASE32_RE = re.compile(r"^[A-Z2-7]{16,}=*$")
_DIGIT_GROUPS_RE = re.compile(r"^\d{4,8}([\- ]\d{4,8})+$")


def _name_is_secretish(name: str) -> bool:
    segments = re.split(r"[\s_.-]+", name.strip().lower())
    return any(segment in _SECRET_NAME_SEGMENTS for segment in segments)


def _value_reason(value: str) -> str | None:
    if _OTPAUTH_RE.search(value):
        return "value looks like an otpauth:// URI (TOTP secret)"
    if _BASE32_RE.match(value.strip()):
        return "value looks like a base32 TOTP seed"
    if _DIGIT_GROUPS_RE.match(value.strip()):
        return "value looks like a recovery code"
    return None


def _crumb_for_item(item: Any, index: int) -> str:
    if isinstance(item, dict) and isinstance(item.get("id"), str):
        return f"id={item['id']}"
    return str(index)


def _scan_node(node: Any, crumb: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for raw_key, value in node.items():
            name = str(raw_key)
            child = f"{crumb}.{name}" if crumb else name
            if (
                name not in _ALLOWLISTED_FIELD_NAMES
                and _name_is_secretish(name)
                and not isinstance(value, dict)
                and value not in (None, "", [])
            ):
                hits.append((child, f'field name "{name}" suggests a stored secret'))
            else:
                hits.extend(_scan_node(value, child))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            hits.extend(_scan_node(item, f"{crumb}[{_crumb_for_item(item, index)}]"))
    elif isinstance(node, str):
        reason = _value_reason(node)
        if reason:
            hits.append((crumb or "(top level)", reason))
    return hits


def scan_for_secrets(raw: Any, source: str) -> None:
    """Raise :class:`LedgerError` when the raw YAML tree looks like it stores secrets."""
    hits = _scan_node(raw, "")
    if not hits:
        return
    lines = [
        f"{source}: refusing to load — keyfleet never stores secrets, and this looks like one:"
    ]
    lines += [f"  - {path}: {reason}" for path, reason in hits]
    lines.append(
        "Remove the value(s); keep secrets in your password manager and store only a pointer, "
        'e.g. recovery_codes: {stored: true, where: "vault item X"}.'
    )
    raise LedgerError("\n".join(lines))


# --- Loading and error formatting -------------------------------------------


def _humanize_loc(raw: Any, loc: tuple[int | str, ...]) -> str:
    """Turn a pydantic loc into 'accounts[id=pw-manager].registrations[0].key'."""
    parts: list[str] = []
    node = raw
    for step in loc:
        if isinstance(step, int):
            item = node[step] if isinstance(node, list) and step < len(node) else None
            parts.append(f"[{_crumb_for_item(item, step)}]")
            node = item
        else:
            parts.append(f".{step}" if parts else str(step))
            node = node.get(step) if isinstance(node, dict) else None
    return "".join(parts)


def _format_validation_error(exc: ValidationError, raw: Any, source: str) -> str:
    count = exc.error_count()
    lines = [f"{source}: invalid ledger — {count} problem{'s' if count != 1 else ''}:"]
    for error in exc.errors(include_url=False):
        where = _humanize_loc(raw, error["loc"]) or "(top level)"
        message = error["msg"].removeprefix("Value error, ")
        lines.append(f"  - {where}: {message}")
    lines.append(
        "See keyfleet.example.yaml and schema/keyfleet.schema.json for the expected shape."
    )
    return "\n".join(lines)


def parse_ledger(text: str, source: str) -> Ledger:
    """Validate ledger YAML text; ``source`` names the origin in error messages."""
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        at = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        problem = getattr(exc, "problem", None) or exc
        raise LedgerError(f"{source}: not valid YAML{at}: {problem}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise LedgerError(
            f"{source}: the top level must be a mapping with version/keys/accounts/policy, "
            f"not {type(raw).__name__}"
        )
    scan_for_secrets(raw, source)
    try:
        return Ledger.model_validate(raw)
    except ValidationError as exc:
        raise LedgerError(_format_validation_error(exc, raw, source)) from exc


def load_ledger(path: str | Path) -> Ledger:
    """Load and fully validate a ledger file, or raise :class:`LedgerError`."""
    file = Path(path)
    source = str(file)
    if not file.is_file():
        raise LedgerNotFoundError(
            f"{source}: ledger file not found — pass a path (keyfleet COMMAND LEDGER) "
            "or run from the directory containing keyfleet.yaml."
        )
    try:
        text = file.read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerNotFoundError(f"{source}: cannot read ledger file ({exc})") from exc
    return parse_ledger(text, source)
