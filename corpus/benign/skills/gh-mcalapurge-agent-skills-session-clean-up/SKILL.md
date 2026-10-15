---
name: session-clean-up
description: Audit and tidy up everything an AI agent left behind during a diagnostic, debugging, investigation or experiment session — temp and scratchpad files, captures and logs, background processes, monitors, listeners, services or daemons it started, virtual interfaces, one-off tools it installed for a specific purpose, config or device changes, subscriptions, published artifacts and shared links. Produces a checked list of what to remove, what to keep and what needs the user, and removes only what the user approves. Use this whenever the user asks to clean up, tidy up, wrap up, reset, "remove what you installed", "what did you leave behind", "do I need to clean anything up", or is finishing a hands-on troubleshooting session, even if they don't say "clean up" explicitly.
---

# Session clean-up

Hands-on diagnostic sessions leave residue: scratch scripts, packet captures, background monitors, daemons loaded "just for this test", permissions granted, test subscriptions on devices, published pages. Some of it is harmless clutter. Some keeps running, survives reboots, or holds sensitive data such as captures, logs with IPs and MACs, tokens or screenshots. The user usually doesn't remember all of it, and you are the only one who knows what you did. This skill turns that knowledge into a verified, user-approved tidy-up.

The workflow has two phases with a hard stop between them: **inventory and propose**, then **remove only what the user approves**. Deleting things the user still wanted is far worse than leaving clutter, so the proposal is the default end state of this skill until the user says go.

## Phase 1: Build the inventory

### 1. Reconstruct what this session did

Go back through the conversation and your own tool calls. List everything you created, started, installed, loaded, changed, granted or published. Include things the user ran at your suggestion, e.g. `sudo` commands you handed them. Walk through these categories so nothing gets missed:

| Category | Examples |
|---|---|
| Files | scratchpad and temp files, helper scripts, generated outputs, downloads, packet captures (`.pcap`), logs, screenshots, exported data, build or venv dirs made for a test |
| Running things | background jobs, monitors, watchers, `tcpdump`/sniffers, local servers, port listeners, tunnels, containers, VMs, simulators you booted |
| System state | services/daemons loaded (launchd, systemd), especially "enabled at boot" flags (`launchctl -w`, `systemctl enable`); virtual or capture interfaces; firewall rules; hosts-file or DNS edits; env vars; cron jobs or scheduled tasks; kernel extensions |
| Installed for this task | packages, CLIs, browser extensions or SDK components pulled in *for a specific one-off purpose*, including side-effect installs a command triggered |
| Permissions and trust | OS privacy grants (Local Network, Full Disk Access, screen recording), device pairing or "Trust this computer", API tokens or keys created, OAuth grants |
| External devices and services | settings changed on routers, IoT devices or phones; test subscriptions or registrations; test records, users or webhooks created in a service; cloud resources |
| Shared or published | artifacts, gists, pastes, shared links, uploaded files, sharing settings you changed, issues or comments you posted |
| Version control | branches, worktrees, stashes or commits made for experiments |

### 2. Verify the current state

Memory of what you did isn't the same as what's still there. Before listing anything, check with read-only commands where you can:
- does the file still exist (and who owns it);
- is the process still running;
- is the service loaded, and is it set to start at boot;
- is the interface up, and is the port still bound?

Drop items that are already gone. Mark anything you couldn't check as "unverified" rather than guessing.

### 3. Classify each item

- **Remove**: session-specific, no longer needed, and safe to remove. Examples: scratch scripts, intermediate outputs, stopped-test leftovers, a daemon loaded only to enable a capture, a test subscription.
- **Remove, needs the user**: removal needs privileges or access you don't have, such as root-owned files, `sudo` service changes, phone or router settings, or account dashboards. Give the exact command or the click path.
- **Keep (deliverable)**: things the user asked for or will want, such as reports, final scripts, published pages they're using, or settings they chose themselves. List these so the user can confirm, but don't propose deleting them.
- **Leave in place (general tooling)**: general-purpose development or debugging tools (compilers, SDKs, Xcode, Wireshark, nmap, Python, Homebrew packages with lasting use), even if you installed them this session. They're useful beyond this session, and removing them can break other work. Mention them in one line so the user knows, and only propose removal if the user asks.
- **No action needed**: things that expire or revert on their own, e.g. a lease or subscription that lapses or a temp dir the platform wipes. Say why, so the user isn't left wondering.

When an item could reasonably go either way, put it under "Remove" with a note, or ask. Don't decide silently.

### 4. Flag sensitive data first

Anything holding personal or network-identifying data goes at the top of the "Remove" list, with a short reason. That includes packet captures, logs with public IPs, MAC addresses, emails or tokens, screenshots, and exported account data. Leftover sensitive files are the main real-world risk of a messy session.

## Phase 2: Present the list, then stop

Use this structure. Keep each line short and concrete, and include paths, PIDs, service names and the exact undo commands.

```
## Session clean-up

**Still active**
1. <thing> — <why it matters, e.g. "starts at every boot">
   <exact command to undo, or "I can do this">

**Remove (sensitive first)**
2. <path or item> — <what it is, why it's not needed>
...

**Needs you** (privileges or access I don't have)
N. <item> — run: `<command>` / go to: <settings path>

**Keeping**
- <deliverable> — <why>

**Leaving in place (general tools)**
- <tool> — useful beyond this session

**No action needed**
- <item> — <why it cleans itself up>

Reply with which numbers to remove ("all", "1-4", "all except 3"). I won't delete anything until you say.
```

Number every actionable item so the user can approve a subset. Then stop and wait.

## Phase 3: Remove what was approved

1. **Remove only the approved items.** If removing one would affect something the user didn't approve (e.g. a shared directory), stop and ask.
2. **Go in a safe order:** stop running processes and interfaces before deleting their files; disable boot-time persistence before unloading a service.
3. **Hand over privileged steps.** For items needing `sudo`, account dashboards or physical devices, give the user the exact command or steps; don't try to work around permissions. In Claude Code, the user can run a command in-session by prefixing it with `!`.
4. **Check again** with the same read-only checks as Phase 1.
5. **Report the result plainly:** what was removed, what the user still needs to do, and anything that failed, with the error.

Use targeted deletes on known paths, never wildcards across directories you didn't create. Never touch files that existed before the session or that the user created, unless the user names them explicitly.

## Platform notes

The workflow is the same everywhere; what you can reach differs.

- **Claude Code CLI / desktop:** you have the real filesystem and shell, so verify and remove directly. Check the session scratchpad directory, background tasks/shells you launched, and artifacts published from the session. Deleting a published artifact can't be undone and breaks the link for everyone, so list it and only delete on an explicit request.
- **Claude app (claude.ai, with code execution) and ChatGPT:** the sandbox (e.g. `/mnt/user-data`, `/mnt/data`) is usually discarded when the conversation ends, so say so under "No action needed" rather than spending effort there. Focus on what outlives the sandbox: files written to connected drives, published artifacts or canvases, shared links, connector or integration changes, and anything the user ran on their own machine at your suggestion (give them the undo commands).
- **Codex (CLI, IDE or cloud):** check the working tree for untracked helper files (`git status --porcelain`), temporary branches or worktrees, stashes, and processes started in the sandbox. Cloud tasks run in a disposable container, so focus on what reached the repo or the user's machine.

If you can't see part of the session (e.g. after a context reset or summary), say so and list only what you can verify, rather than presenting a complete-looking list that isn't.
