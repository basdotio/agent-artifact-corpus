# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in `fattureincloud-mcp`, please report it responsibly:

- **Preferred:** [GitHub Security Advisories](https://github.com/aringad/fattureincloud-mcp/security/advisories/new)
- **Alternative:** email `assistenza@mediaform.it` with subject `[fattureincloud-mcp] Security disclosure`

We commit to:

- Acknowledge receipt within 7 days
- Provide a remediation plan within 30 days for valid reports
- Credit reporters in release notes (unless anonymity is requested)

Do **not** disclose publicly until a fix is released.

## Scope

**In scope:**

- Authentication / authorization bypass
- Injection vulnerabilities
- Sensitive data leakage in logs / cache
- Dependency vulnerabilities affecting users

**Out of scope:**

- Issues in FattureInCloud's own API or platform — report to TeamSystem S.p.A.
- Issues in Claude or the MCP protocol — report to Anthropic / the MCP working group.

## Supported versions

Only the latest minor release line on PyPI receives security patches. Older minors are unsupported.
