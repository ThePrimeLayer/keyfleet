from __future__ import annotations

from pathlib import Path

from keyfleet.model import Ledger

FIXTURES = Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent

#: Default key set for inline check tests: one key per status.
DEFAULT_KEYS = [
    {"id": "k-active", "label": "Active", "vendor": "yubico", "status": "active"},
    {"id": "k-spare", "label": "Spare", "vendor": "yubico", "status": "spare"},
    {"id": "k-lost", "label": "Lost", "vendor": "yubico", "status": "lost"},
    {"id": "k-retired", "label": "Retired", "vendor": "yubico", "status": "retired"},
]


def fixture(name: str) -> Path:
    path = FIXTURES / name
    assert path.is_file(), f"missing test fixture {path}"
    return path


def make_ledger(
    accounts: list[dict] | None = None,
    keys: list[dict] | None = None,
    policy: dict | None = None,
) -> Ledger:
    """Build a small in-memory ledger for check tests."""
    raw: dict = {
        "version": 1,
        "keys": DEFAULT_KEYS if keys is None else keys,
        "accounts": accounts or [],
    }
    if policy is not None:
        raw["policy"] = policy
    return Ledger.model_validate(raw)


def make_account(tier: str, regs: list[str], **extra) -> dict:
    """An account dict registering ``regs`` keys as fido2-discoverable."""
    return {
        "id": extra.pop("id", "acct"),
        "label": extra.pop("label", "Account"),
        "tier": tier,
        "registrations": [{"key": key, "type": "fido2-discoverable"} for key in regs],
        **extra,
    }
