# Security policy

## Supported versions

Only the latest version on the `main` branch is supported. Fixes are not
backported.

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Report it privately through GitHub:
<https://github.com/OWNER/REPO/security/advisories/new>

Include what you found, how to reproduce it, and which platform you were on.
You should get a reply within 7 days. If the report is confirmed, a fix will be
released and you will be credited unless you ask not to be.

## What PROJECT touches

Knowing this helps you judge what counts as a vulnerability:

- REPLACE: files it reads or edits outside its own directory
- REPLACE: what data it stores, where, and whether anything leaves the machine
- REPLACE: background jobs, services, or elevated privileges it uses
- REPLACE: other programs it starts, and how untrusted text reaches them

REPLACE: one sentence saying what is in scope.
