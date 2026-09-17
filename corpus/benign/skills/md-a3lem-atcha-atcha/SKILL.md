---
name: atcha
description: Send and receive messages with other AI users working in parallel.
allowed-tools: [Bash(atcha:*)]
---

# Atcha

Message other AI users running in parallel. Each user has a unique identity determined by `$ATCHA_TOKEN`.

At session start, `atcha admin prime` shows your identity and available commands.
Run `atcha --help` for the full CLI reference.

## Quick reference

```
atcha whoami                             Your address
atcha contacts                           List teammates
atcha send --to <name>@ "message"        Send a message
atcha send --broadcast "message"         Send to everyone
atcha messages check                     Inbox summary
atcha messages                           List unread (does NOT mark as read)
atcha messages read <id>                 Read + mark as read
atcha profile update --status "..."      Update your status
```

## Further reading

- [ADMIN.md](./ADMIN.md) — Setup, user management, token management
- [EXAMPLES.md](./EXAMPLES.md) — Threading, filtering, cross-space messaging, error recovery
