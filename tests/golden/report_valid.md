# keyfleet report — 3 keys (2 active, 1 spare) · 3 accounts

## Coverage matrix

| Account | Tier | yk-a | yk-b | spare-c | Keys |
|---|---|---|---|---|---|
| Password manager | T0 | fido2 | fido2 | fido2 | 3/3 OK |
| Mail | T1 | disc | u2f | — | 2/2 OK |
| Niche forum | T2 | u2f | — | — | 1/1 OK |

_disc = FIDO2 discoverable (passkey) · fido2 = FIDO2 non-discoverable · totp = OATH-TOTP · otp = Yubico OTP · pgp = OpenPGP_

## Per-tier summary

| Tier | Accounts | Meeting policy | Min keys |
|---|---|---|---|
| T0 | 1 | 1 | 3 |
| T1 | 1 | 1 | 2 |
| T2 | 1 | 1 | 1 |

## Key utilization

| Key | Status | Accounts | Discoverable |
|---|---|---|---|
| yk-a | active | 3 | 1/100 |
| yk-b | active | 2 | 0/25 |
| spare-c | spare | 1 | 0 |
