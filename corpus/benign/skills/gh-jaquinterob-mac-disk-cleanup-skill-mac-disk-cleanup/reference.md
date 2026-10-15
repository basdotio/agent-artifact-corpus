# Command reference — mac-disk-cleanup

Paths assume a standard user home (`$HOME`). Skip anything that does not exist.

## Baseline

```bash
df -h /
du -sh "$HOME/Library/Developer/Xcode/DerivedData" 2>/dev/null
du -sh "$HOME/Library/Caches/Homebrew" 2>/dev/null
du -sh "$HOME/.npm" 2>/dev/null
command -v docker >/dev/null && docker system df
command -v brew >/dev/null && brew cleanup -n 2>/dev/null | tail -20
```

---

## Safe (auto-clean in mode B)

### Xcode — DerivedData

Regenerated on next build.

```bash
rm -rf "$HOME/Library/Developer/Xcode/DerivedData"/*
```

### Xcode — Archives optional note

Archives (`$HOME/Library/Developer/Xcode/Archives`) can be large but may hold App Store uploads. Treat as **Risky** unless the user confirms.

### Homebrew

```bash
brew cleanup -s
rm -rf "$(brew --cache)"
```

### npm

```bash
npm cache clean --force
```

Also safe if present:

```bash
command -v yarn >/dev/null && yarn cache clean
command -v pnpm >/dev/null && pnpm store prune
```

### Docker — unused data (no volumes)

Requires Docker daemon running.

```bash
docker system prune -f
```

Does **not** remove named volumes or non-dangling images still referenced by containers.

---

## Risky (explicit approval required)

### Docker — including volumes

Destroys unused volumes (possible DB data).

```bash
docker system prune -a --volumes -f
```

### Docker — list large volumes first

```bash
docker volume ls
docker system df -v
```

### Xcode — Simulator runtimes

Frees a lot; removes unused iOS/watchOS runtimes.

```bash
xcrun simctl delete unavailable
xcrun simctl list runtimes
# Then, only if user names a runtime:
# xcodebuild -downloadPlatform iOS   # re-download later if needed
# Prefer: Settings → Storage, or:
xcrun simctl runtime list
```

Deleting a specific runtime (example — adjust identifier after listing):

```bash
xcrun simctl runtime delete <RUNTIME_IDENTIFIER>
```

### Xcode — iOS DeviceSupport

Old device symbols; safe-ish but can slow first debug of old devices → treat as Risky.

```bash
du -sh "$HOME/Library/Developer/Xcode/iOS DeviceSupport"/*
# After user OK for specific old folders:
# rm -rf "$HOME/Library/Developer/Xcode/iOS DeviceSupport/<old-version>"
```

### Unused Xcode app versions

Only if multiple Xcodes exist and user confirms which to keep:

```bash
ls /Applications/Xcode*.app
# Do not delete without explicit path approval
```

---

## Never

- `$HOME/Documents`, `$HOME/Desktop`, Photos, Mail, Messages attachments (unless user gives an exact path)
- `$HOME/.ssh`, keychains, password managers
- Project source trees and `.git` history (unless user asks to delete a named folder)
- `/System`, `/Library` (system), SIP-protected paths

---

## Quick size helpers

```bash
# Largest items in a directory (top 20)
du -hd 1 "$1" 2>/dev/null | sort -hr | head -20
```
