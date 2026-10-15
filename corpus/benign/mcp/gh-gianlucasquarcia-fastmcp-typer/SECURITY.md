# Security policy

> **Template note:** if you created a project from this template, replace the contact details below with your own.

## Reporting a vulnerability

Please do **not** open a public issue for security problems.

Report privately using GitHub's **Security → Report a vulnerability** (private security advisory) on this repository. Include the affected version or commit, steps to reproduce, and the potential impact.

You can expect an acknowledgement within a few working days and updates as the issue is investigated and fixed.

## Supported versions

Only the latest commit on the default branch (`master`) receives security fixes.

## Security notes for users

- Never commit `.env` or other secrets; use `.env.template` for placeholders.
- Keep `HTTP_REQUEST_TLS_VERIFY` enabled (the default); only disable it locally when you must, e.g. behind a corporate proxy.
- When exposing the server over HTTP, put it behind authentication and TLS; the default setup has none.
- Keep dependencies up to date (`uv lock --upgrade`) and review changes to `uv.lock`.
