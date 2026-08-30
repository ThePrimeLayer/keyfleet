# Lost key: k-main — "Main key"

Ledger status: active. 2 affected accounts (1 inaccessible, 1 below policy) · 1 unaffected.

- [ ] **T0 Primary email (Google)** — delete "main" (fido2-discoverable) at [security settings](https://myaccount.google.com/signinoptions/two-step-verification) (after: 0/3 keys — below policy)
- [ ] **T1 Code hosting** — delete "main" (fido2-discoverable) at github account settings (after: INACCESSIBLE — 0 keys, no other factors)

Then set `status: lost` on k-main in the ledger and re-run `keyfleet check`.
