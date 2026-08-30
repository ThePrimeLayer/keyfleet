# Security policy

## What keyfleet does and doesn't hold

keyfleet is a local-first inventory. The ledger maps which accounts exist and
which hardware keys guard them — that map is sensitive, and the README tells
users to keep it encrypted (`age`, password-manager document, or a private
repo). keyfleet itself:

- never stores secrets — validation rejects fields or values that look like
  recovery codes, TOTP seeds, PINs, or OTP secrets;
- makes no network calls in runtime code and has no telemetry (both enforced
  by tests);
- decrypts `.age` ledgers to memory only, never to disk;
- talks to no key hardware in v0.1.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Reporting a vulnerability

Please use GitHub's **private vulnerability reporting** on this repository
("Report a vulnerability" under the Security tab) rather than a public issue.
Reports that show how a crafted ledger, data file, or `.age` input breaks the
promises above are exactly what we want to hear about. You should receive an
initial response within a week.
