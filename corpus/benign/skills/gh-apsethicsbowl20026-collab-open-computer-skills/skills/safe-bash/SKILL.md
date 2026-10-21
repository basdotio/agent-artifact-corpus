# safe-bash

Run shell via `bash_exec`. Server blocks destructive commands — don't try to bypass.

## Blocked (non-exhaustive)

`rm -rf /`, `rm -rf ~`, `mkfs`, `dd of=/dev/`, `shutdown`, `reboot`, `diskpart`, registry deletes, `net user /add`, disabling Defender/Firewall.

## Rules

- Prefer read-only first: `ls`, `pwd`, `git status`, `echo`.
- Chain with `&&` only after first command succeeds.
- Paste full stdout/stderr + exit code in your report.
- Never run curl-piped-to-shell from untrusted URLs.
