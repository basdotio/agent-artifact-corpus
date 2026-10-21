# Privacy Policy — fattureincloud-mcp

**Effective date:** 10 May 2026
**Maintainer:** Mediaform s.c.r.l. (P.IVA 01263870998), Salita N. S. del Monte 3, 16143 Genova, Italy.

This document mirrors the Privacy Policy hosted at https://media-form.it/privacy-policy.html

## 1. Scope

This Privacy Policy describes how the open-source software `fattureincloud-mcp` (the "Software") handles data when installed and run by an end user on their own machine.

## 2. Data Controller

When you install and use the Software, **you act as the data controller** for any personal or business data accessed through it. Mediaform s.c.r.l. is the **author and maintainer** of the Software, but does not operate any server or cloud component as part of this Software's standard operation.

## 3. What data the Software accesses

The Software, when invoked by you, may access the following data through the FattureInCloud API on your behalf:

- Client and supplier registry data (names, addresses, VAT numbers)
- Issued and received documents (invoices, credit notes, proformas, etc.)
- Products and services catalog
- Cost/revenue centers and expense categories
- Financial summaries (revenue, expenses, totals)
- E-invoice (SDI) status

## 4. Where data is processed

- API calls are made **directly from your machine** to FattureInCloud's servers (api-v2.fattureincloud.it).
- No data is routed through Mediaform's servers.
- A local cache of static reference data is stored on your machine in `~/.fattureincloud-mcp/cache/` (or a directory you specify via `FIC_CACHE_DIR`).

## 5. Local cache

To minimize redundant API calls, the Software caches reference data (clients, suppliers, products, cost centers, VAT regimes, payment methods) as plaintext JSON files in your local cache directory.

- Cache contents include the same data the user would see in FattureInCloud's web interface for these resources.
- Cache files are scoped per FattureInCloud company ID.
- You can disable caching via `FIC_CACHE_DISABLED=1` or delete the cache directory at any time.
- The Software does **not** transmit cache contents anywhere.

## 6. Credentials

- Your FattureInCloud API token and company ID are provided by you via environment variables or Claude Desktop's `user_config`.
- The Software uses these credentials only to authenticate API calls to FattureInCloud.
- Credentials are **not** logged, persisted, or transmitted to any third party other than FattureInCloud's API itself.

## 7. Logging

The Software logs operational messages (API call summaries, errors) to standard output by default. These logs are visible in your Claude Desktop logs but are not transmitted off-machine. Sensitive data (tokens, full payloads) are redacted where possible.

## 8. Third parties

- **FattureInCloud / TeamSystem S.p.A.:** the upstream service. Their privacy policy applies to data stored in your FattureInCloud account: https://www.fattureincloud.it/privacy-policy/
- **Anthropic:** if you use Claude Desktop, Anthropic's privacy policy applies to your interactions with Claude: https://www.anthropic.com/legal/privacy
- **Mediaform s.c.r.l.:** the maintainer. Mediaform does not collect, receive, or process any data through this Software in normal use.

## 9. Your rights

Because Mediaform does not operate any data processing infrastructure as part of the Software, GDPR data subject rights (access, rectification, erasure) are exercised:

- Toward **FattureInCloud / TeamSystem S.p.A.** for data in your FattureInCloud account.
- Toward **Anthropic** for data in Claude Desktop logs.
- Toward **yourself** for the local cache (delete files freely).

## 10. Security

- The Software is open-source and auditable: https://github.com/aringad/fattureincloud-mcp
- Vulnerability disclosure: see [SECURITY.md](../SECURITY.md) in the repository.

## 11. Changes

This Privacy Policy may be updated as the Software evolves. The effective date at the top reflects the latest version. Material changes will be announced in [CHANGELOG.md](../CHANGELOG.md).

## 12. Contact

- Email: assistenza@mediaform.it
- Postal: Mediaform s.c.r.l., Salita N. S. del Monte 3, 16143 Genova, Italy
- PEC: mediaform@pec.it
