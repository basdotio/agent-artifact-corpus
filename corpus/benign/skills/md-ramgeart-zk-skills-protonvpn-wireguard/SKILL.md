---
name: protonvpn-wireguard
description: "Manage Proton VPN WireGuard configurations directly from the Proton account/VPN web panel via browser automation. Use when creating, rotating, downloading, labeling, or revoking WireGuard configs for devices, and when verifying profile state changes in the Proton UI."
---

# ProtonVPN WireGuard

Handle Proton VPN WireGuard profile lifecycle from Proton web interfaces.

## Scope

- Open Proton VPN section in account panel
- Create a new WireGuard configuration/profile for a device
- Rename/label profile if UI allows
- Regenerate/rotate credentials/config
- Download `.conf` file and/or show QR for mobile
- Revoke/delete old profiles
- Verify resulting profile state

## Fixed context

- Account: *(configure your Proton account)*
- Browser mode: `target=host`, `profile=openclaw`
- Proton entrypoint: `https://account.proton.me/apps`

## Workflow

1. Reuse existing Proton tab when possible; otherwise navigate to account entrypoint.
2. Go to Proton VPN area and then WireGuard config/profile section.
3. Snapshot and identify exact target profile/device.
4. Run one requested mutation at a time.
5. Snapshot again and verify success with explicit UI evidence.
6. Return concise status + artifacts generated.

## Safety rules

- Confirm before destructive actions: revoke/delete/rotate active profile.
- Never paste private keys in chat.
- If multiple similar profiles exist, ask user to choose exact one.
- For bulk cleanup, provide preview list first unless user requests immediate action.

## Output

- `Done`: what action was applied.
- `Verified`: visible state in Proton UI.
- `Artifacts`: config downloaded / QR generated.
- `Next`: optional follow-up (test tunnel, retire previous config, etc.).
