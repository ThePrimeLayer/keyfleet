"""Optional encrypted-ledger support: read ``keyfleet.yaml.age`` via the age CLI.

Decryption goes to memory only — plaintext never touches disk (brief §4.7).
Identities: point ``KEYFLEET_AGE_IDENTITY`` at an age identity file for
non-interactive use; without it, age falls back to its own passphrase prompt
on the terminal. keyfleet never encrypts and never stores key material.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from keyfleet.model import Ledger, LedgerError, LedgerNotFoundError, load_ledger, parse_ledger

IDENTITY_ENV = "KEYFLEET_AGE_IDENTITY"


def age_available() -> bool:
    return shutil.which("age") is not None


def decrypt_age_to_text(path: Path) -> str:
    """Decrypt an .age file to a str in memory, or raise :class:`LedgerError`."""
    if not age_available():
        raise LedgerError(
            f"{path}: this is an age-encrypted ledger but the `age` CLI is not on PATH. "
            "Install age (https://age-encryption.org) or decrypt it yourself."
        )
    command = ["age", "--decrypt"]
    identity = os.environ.get(IDENTITY_ENV)
    if identity:
        command += ["--identity", identity]
    command.append(str(path))
    # age reads a passphrase from the controlling terminal itself, so capturing
    # stdout/stderr does not break interactive decryption.
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        detail = result.stderr.strip() or f"age exited with {result.returncode}"
        raise LedgerError(
            f"{path}: age decryption failed — {detail}\n"
            f"(identity file via the {IDENTITY_ENV} environment variable)"
        )
    return result.stdout


def load_ledger_auto(path: str | Path) -> Ledger:
    """Load a ledger, transparently decrypting ``.age`` files to memory.

    Resolution: an existing ``*.age`` path is decrypted; an existing plain
    path loads normally; a missing plain path falls back to ``<path>.age``
    when that exists.
    """
    file = Path(path)
    if file.is_file():
        if file.suffix == ".age":
            return parse_ledger(decrypt_age_to_text(file), source=str(file))
        return load_ledger(file)
    encrypted = file.with_name(file.name + ".age")
    if encrypted.is_file():
        return parse_ledger(decrypt_age_to_text(encrypted), source=str(encrypted))
    raise LedgerNotFoundError(
        f"{file}: ledger file not found (also looked for {encrypted.name}) — pass a path "
        "(keyfleet COMMAND LEDGER) or run from the directory containing keyfleet.yaml."
    )
