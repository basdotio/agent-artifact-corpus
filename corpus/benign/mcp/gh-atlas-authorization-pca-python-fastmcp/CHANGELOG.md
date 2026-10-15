# Changelog

## 0.4.1 - 2026-10-12

- Requires `atlas-pca>=0.4.1,<0.5`: the 0.4.1 verifier is a security release (root caveats are enforced). No API change in this adapter.

## 0.4.0 - 2026-10-11

- Requires `atlas-pca>=0.4.0,<0.5` (lockstep with the 0.4.0 verifier, which is breaking: strict canonical digests with a depth cap, full signer-set validation in threshold shares, the root PQ pin, caveat and document size caps). No API change in this adapter.

## 0.3.0

- Requires `atlas-pca>=0.3.0,<0.4`. 0.2.0 is superseded: it could not be used with current releases of the framework (see the fixes below).

- Added end-to-end tests against the real framework (FastMCP 4.1.0); run them with `make test-real`.
- Fix: A proof carried in tool arguments is now stripped after verification so a tool with a strict schema accepts the call.
- Optional `test-real` extra pins the framework version the end-to-end tests are validated against.

## 0.2.0 (superseded by 0.3.0)

- Tracks `atlas-pca` 0.2.0, which adds the `grant_ref_bound` verification check.
- Requires `atlas-pca>=0.2.0,<0.3`.
- MIT license metadata and LICENSE file included in the distribution.

## 0.1.0

- Initial release.
