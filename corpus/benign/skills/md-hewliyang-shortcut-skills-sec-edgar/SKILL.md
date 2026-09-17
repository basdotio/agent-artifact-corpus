---
name: sec-edgar
description: Research and download SEC EDGAR filings (10-K, 10-Q, 8-K, etc.) for US public companies.
ui_visibility: summary
---

# SEC EDGAR Filing Research

**Why PDF instead of XBRL?** SEC filings contain inline XBRL (HTML with embedded XML tags) which creates noise for LLMs. Additionally, ~34% of filings have XBRL tagging errors, companies use non-standard tags, and narrative content (MD&A, Risk Factors) isn't captured in XBRL. PDF + file_perception reads what humans see.

**Rate limit:** 10 requests/second. All requests require header: `User-Agent: ShortcutAgent/1.0 (support@shortcut.ai)`

## Workflow Overview

1. **Find company** → Get CIK from ticker/name
2. **Fetch metadata** → Get filing list with dates from SEC API
3. **VERIFY "LATEST"** → Sort by date, confirm against today's date (CRITICAL!)
4. **Convert to PDF** → Use `sec_to_pdf.py` script (Playwright + Chrome)
5. **Analyze** → Use `file_perception` on the PDF

---

## API Reference

All requests require header: `User-Agent: ShortcutAgent/1.0 (support@shortcut.ai)`

| Endpoint | URL |
|----------|-----|
| Company tickers | `https://www.sec.gov/files/company_tickers.json` |
| Filings metadata | `https://data.sec.gov/submissions/CIK{cik_10digit}.json` |
| Download filing | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primaryDocument}` |

Rate limit: 10 requests/second

## Step 1: Find Company CIK

Fetch company tickers JSON and search for the ticker:

```
GET https://www.sec.gov/files/company_tickers.json
```

Returns: `{"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}`

Zero-pad CIK to 10 digits for the next step (e.g., `320193` → `0000320193`).

---

## Step 2: Fetch Filing Metadata

```
GET https://data.sec.gov/submissions/CIK{cik_10digit}.json
```

Response contains `filings.recent` with parallel arrays: `form`, `filingDate`, `reportDate`, `accessionNumber`, `primaryDocument`. Index `i` across all arrays gives one filing's info.

---

## Step 3: VERIFY "Latest" Filing (CRITICAL)

**NEVER assume the first result is the latest.** The API doesn't guarantee sort order.

### Verification Protocol

1. **Check today's date** from the system prompt (e.g., "Today's date: 2026-01-06")

2. **Collect ALL filings** of the requested type from the parallel arrays

3. **Sort by `filingDate` descending** to find the truly latest

4. **Sanity check against expected filing schedule:**

   | Filing | Expected Timing |
   |--------|-----------------|
   | 10-K | 60-90 days after fiscal year end |
   | 10-Q | 40-45 days after quarter end |
   | 8-K | Within 4 business days of event |
   | DEF 14A | ~120 days before annual meeting |

5. **Report exact dates to user:**
   > "Found Tesla's latest 10-K filed on 2026-01-29 for fiscal year ending 2025-12-31. Is this the one you need?"

### Red Flags

- If today is January 2026 but the "latest" 10-K shows FY2024 → something's wrong
- If `reportDate` is more than a year old → re-verify or warn user
- Multiple filings same day → check for amendments (10-K/A vs 10-K)

---

## Step 4: Convert to PDF

Build URL from metadata:

```
https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primaryDocument}
```

- Remove dashes from `accessionNumber` for URL path
- Use unpadded CIK (no leading zeros)

Example:
- CIK: `320193`
- Accession: `0000320193-25-000123` → `000032019325000123`
- Document: `aapl-20250928.htm`
- URL: `https://www.sec.gov/Archives/edgar/data/320193/000032019325000123/aapl-20250928.htm`

Use the `sec_to_pdf.py` script to convert directly from URL (renders images properly):

```bash
python /skills/default/sec-edgar/sec_to_pdf.py "<filing_url>" "/workspace/sec/{TICKER}/{form}_{report_date}.pdf"
```

**File path convention:** Always save SEC filings to `/workspace/sec/{TICKER}/{form}_{report_date}.pdf`
- Example: `/workspace/sec/AAPL/10-K_2024-09-28.pdf`
- Example: `/workspace/sec/TSLA/10-Q_2024-06-30.pdf`
- This keeps filings organized by company and makes them easy to find later

**Why Chrome?** Two reasons: (1) SEC.gov blocks headless Chromium with 403 errors - real Chrome bypasses this. (2) Downloading HTML locally breaks relative image paths; Chrome navigating directly to the URL keeps images loading from SEC's servers.

**Fallback:** If the script fails, you can use httpx to download locally and `weasyprint` amongst other tools and packages to convert the html to PDF. 
If you download HTML first and use `filename=`, relative image paths may break and images may not get rendered. You will have to check and fix this.

---

## Step 5: Analyze with file_perception

Use `file_perception` on the PDF to extract information.
