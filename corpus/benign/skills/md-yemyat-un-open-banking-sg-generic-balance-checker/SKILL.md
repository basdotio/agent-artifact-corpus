---
name: generic-balance-checker
description: Check balances from Singapore financial institutions using browser automation.
compatibility: Requires bun runtime, and agent-browser npm package.
---

# Singapore Financial Balance Checker

Extract balances and transaction data from Singapore financial websites via browser automation.

## Workflow

### Prerequisites

Ensure you have the following installed:

- Bun runtime (install via `curl -fsSL https://bun.sh/install | bash`)
- Agent-browser (install via `npm install -g agent-browser`)
- Chromium (install via `agent-browser install`)
- Read `history` folder for latest information and trouble shooting tips

### Steps

```bash
# 1. Open financial site (see references/supported-websites.md for URLs)
npx agent-browser open https://app.sg.endowus.com/ --headed

# 2. USER LOGS IN MANUALLY (Singpass, 2FA, etc.)
# Wait for user confirmation before proceeding

# 3. Navigate to portfolio/accounts
npx agent-browser snapshot -i
npx agent-browser find text "Portfolio" click
npx agent-browser wait 2000

# 4. Extract data
npx agent-browser snapshot -c
npx agent-browser eval "document.body.innerText" --json

# 5. Close when done
npx agent-browser close
```

## Key Commands

| Action                   | Command                                                    |
| ------------------------ | ---------------------------------------------------------- |
| Open browser (visible)   | `npx agent-browser open <url> --headed`                    |
| Get interactive elements | `npx agent-browser snapshot -i`                            |
| Get full page data       | `npx agent-browser snapshot -c`                            |
| Click by ref             | `npx agent-browser click @e5`                              |
| Click by text            | `npx agent-browser find text "X" click`                    |
| Click by role            | `npx agent-browser find role button click --name "Submit"` |
| Wait for time            | `npx agent-browser wait 2000`                              |
| Wait for URL             | `npx agent-browser wait --url "**/dashboard**"`            |
| Run JavaScript           | `npx agent-browser eval "..."`                             |
| Get JSON output          | `npx agent-browser eval "..." --json`                      |
| Scroll page              | `npx agent-browser scroll down 500`                        |
| Take screenshot          | `npx agent-browser screenshot output.png`                  |
| Close browser            | `npx agent-browser close`                                  |

## Authentication

**CRITICAL Security Rules:**

- Always use `--headed` flag so user can see and interact
- **NEVER** ask for or handle credentials programmatically
- **NEVER** store or log passwords, OTPs, or 2FA codes
- User must log in manually in the browser window
- Many SG sites require Singpass/2FA - user must complete this themselves

### Handling Singpass Login

1. Wait for Singpass QR or redirect
2. User scans with Singpass app or enters credentials
3. User completes 2FA on their phone
4. Wait for redirect: `npx agent-browser wait --url "**/dashboard**"`

### Handling OTP / TOTP

1. Wait for the user to login
2. Once on the OTP page, ask the user to enter the OTP into the browser

## Data Extraction

### Common Data Points

| Data Point   | Common Patterns                                    |
| ------------ | -------------------------------------------------- |
| Total Value  | "Total", "Portfolio Value", "Net Worth", "Balance" |
| Cash Balance | "Cash", "Available", "Uninvested", "Buying Power"  |
| Returns      | "Return", "P&L", "Gain/Loss", "Performance"        |
| Currency     | SGD, USD, multi-currency balances                  |

### Transaction/Activity History

| Field  | Common Labels                                           |
| ------ | ------------------------------------------------------- |
| Date   | "Date", "Transaction Date", "Trade Date"                |
| Type   | Buy, Sell, Deposit, Withdrawal, Dividend, Fee, Transfer |
| Amount | "Amount", "Value", "Quantity"                           |
| Status | Completed, Pending, Processing, Failed, Cancelled       |

### Extract Transaction Table

```bash
npx agent-browser eval "Array.from(document.querySelectorAll('table')[1].querySelectorAll('tbody tr')).map(row => { const cells = row.querySelectorAll('td'); return cells.length >= 4 ? [cells[0].innerText.trim(), cells[1].innerText.replace(/\\n/g, ' ').trim(), cells[2].innerText.trim(), cells[3].innerText.trim()].join(' | ') : null; }).filter(x => x && !x.includes('Load more')).join('\\n')"
```

### Pagination Handling

```bash
# Load all transactions
for i in {1..15}; do
  npx agent-browser find text "Load more" click 2>/dev/null || break
  npx agent-browser wait 800
done

# Verify all loaded (should show "1-194 of 194")
npx agent-browser eval "document.body.innerText.match(/\\d+-\\d+ of \\d+/)?.[0]"
```

## Security Best Practices

### DO:

- Always use `--headed` mode for financial sites
- Let users authenticate manually (Singpass, OTP, 2FA)
- Close browser sessions after use
- Verify you're on the correct domain before proceeding

### DON'T:

- Never capture, store, or transmit passwords
- Never ask the user to tell you their password
- Never screenshot login pages or OTP screens
- Never automate credential entry
- Never store session cookies for financial sites

## Error Handling

| Issue                            | Solution                                        |
| -------------------------------- | ----------------------------------------------- |
| Timeout on network idle          | Proceed with snapshot anyway                    |
| Multiple table selector conflict | Use `snapshot -c` instead of `-s "table"`       |
| Element not found                | Use `2>/dev/null` to suppress errors in loops   |
| Empty snapshot content           | See `references/when-snapshot-returns-empty.md` |

## Verification Checklist

Before completing extraction:

- [ ] Browser opened with `--headed` flag
- [ ] User completed authentication manually
- [ ] Navigated to correct account/portfolio page
- [ ] All paginated data loaded (if applicable)
- [ ] Data extracted and validated
- [ ] Browser closed with `npx agent-browser close`

## Scripts

Reusable shell scripts in `scripts/` for common automation tasks.

| Script                     | When to Use                                                                             | Usage                                             |
| -------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `detect-frames.sh`         | When `snapshot` returns empty or minimal content (DBS, OCBC legacy sites use framesets) | `./scripts/detect-frames.sh`                      |
| `extract-balances.sh`      | Quick extraction of SGD amounts and currency patterns from current page                 | `./scripts/extract-balances.sh`                   |
| `load-all-transactions.sh` | When transaction list has "Load more" pagination                                        | `./scripts/load-all-transactions.sh [max_clicks]` |

## Dealing with Dynamic Sites and Documenting new lines

- It's common for financial websites to always update their page design, layout, security system and more.
- What works today may not work tomorrow.
- Everytime you discover a way to fetch information that the user is looking for, update it in `history` folder within the skills directory.
- Create a new file for each institution, documenting the changes and the new approach. (e.g `dbs.md`)
- Be very specific about the new approach that you discovered

## Additional Resources

- `references/supported-websites.md` - Full list of institutions and login URLs
- `references/when-snapshot-returns-empty.md` - For DBS/OCBC legacy iframe sites
