---
name: receipt-reader
description: Read a folder of receipts and supplier invoices (PDFs, scans, phone photos) into one spreadsheet file (a CSV that opens in Excel) with supplier, date, net, VAT and gross, and list anything a person needs to check. Use when the user says "type up my receipts", "read these receipts", "receipts into a spreadsheet", "process this month's invoices", or runs /receipt-reader.
---

# Receipt reader

Turn a folder of receipts and supplier invoices into one spreadsheet. You read; the
user approves. The one rule that matters: **never guess a figure.** A blank cell with a
reason is useful. A confident wrong number in someone's accounts is not.

## 1. Find the documents

- Work in the current folder unless the user names another one.
- Include `.pdf .jpg .jpeg .png .heic .webp .tif .tiff`. Look one level into
  sub-folders too.
- Ignore anything this skill wrote earlier (`receipts*.csv`).
- Say how many files you found before you start, and name any files you are skipping
  because of their type (a Word or email invoice, for example). If there are no files
  to read, say so and stop. If there are more than 60, ask whether to do them all or
  the first 60.

## 2. Read every file

Open each file and look at it. Never work out what a document is from its filename.
A multi-page PDF may hold several receipts: treat each one as its own row.

For each document, record:

| Field | Notes |
|---|---|
| File | The filename, so the user can find the original |
| Supplier | As printed. Don't expand or correct it |
| Date | The document date, as `YYYY-MM-DD` |
| Type | `receipt`, `invoice`, `credit note`, or `other`. Blank if you can't tell |
| Document no. | Invoice, receipt, ticket or delivery-note number if printed |
| Description | Six words or fewer: what was bought. Summarise if there are several items |
| Net | Amount before VAT |
| VAT | VAT amount |
| Gross | Total paid or payable |
| VAT rate | As printed, e.g. `20%`, `5%`, `0%`, `mixed`. Blank if no rate is printed |
| Currency | `GBP` unless the document says otherwise. Blank if the row has no amounts |
| Job ref | Any job, order or PO reference printed on it |

Amounts are plain numbers with two decimal places and no currency symbol. Credit notes
are negative. Copy names and references as they are printed, including capitals.

## 3. When to flag instead of fill

Give every row a status of `OK` or `CHECK`. Mark it `CHECK`, with a short plain-English
reason, when any of these is true. If a row has more than one reason, list them all,
separated by a semicolon.

- **You can't read it.** Blurred, cropped, faded or handwritten. Leave the unreadable
  cells blank. Do not fill them from context. If you can't read the document at all,
  the row is just the filename, `CHECK` and the reason.
- **The sums don't add up.** Net + VAT should equal gross to within 2p.
- **There's no VAT breakdown.** Only a total is printed. Put the total in Gross, leave
  Net and VAT blank, and say "no VAT breakdown". Do not work the VAT out yourself: you
  don't know the rate or whether the supplier is VAT registered.
- **VAT is charged but no VAT number is printed.** Say "no VAT number on document".
- **It looks like a duplicate.** Same supplier and same gross on the same date, or the
  same document number. Flag every copy, and name the other file in the reason. Leave
  the figures filled in on both: the user decides which copy to keep.
- **The date is missing or unclear.** Read numeric dates as day-first: `08/09/2026` is
  8 September. That is not ambiguous on a UK document, so don't flag it. Flag a date
  only when it is missing, partly unreadable, has a two-digit year that could be the
  day, or sits on a document that is clearly not from the UK.
- **It isn't a receipt or invoice.** Statements, quotes, delivery notes without prices,
  order confirmations. Give it a row with Type `other`, fill in the supplier, date,
  number and description, leave the amounts blank and say what it is. If it clearly
  belongs with an invoice in the same folder, name that file in the reason.
- **It's in another currency.** Record the currency and the amounts as printed. Don't
  convert.

If you are unsure whether to flag something, flag it.

## 4. Write the spreadsheet

Write `receipts.csv` in the folder you read. If that file already exists, don't
overwrite it: write `receipts-2.csv` (then `-3`, and so on) and say which name you used.

- Columns, in this order: `File, Supplier, Date, Type, Document no., Description, Net,
  VAT, Gross, VAT rate, Currency, Job ref, Status, Check reason`
- One header row. Sort by date, oldest first, with undated rows at the end.
- Quote any field that contains a comma, a double quote or a line break. Save as UTF-8
  with a byte-order mark, so Excel shows pound signs and accents correctly.

## 5. Tell the user what happened

Finish with a short summary in the chat:

1. Which file you wrote, how many files you read and how many rows it has.
2. Totals for the `OK` rows only: net, VAT and gross.
3. How much is waiting on a check: the gross of the `CHECK` rows that have a figure,
   counting each set of duplicates once. This stops a flagged invoice from quietly
   dropping out of the picture.
4. The check list: each flagged file with its reason, one per line.
5. This reminder, in your own words: look at the flagged rows, and spot-check a few of
   the OK ones against the originals, before any of this goes into the accounts.

## What this skill never does

- It never renames, moves, edits or deletes the user's files.
- It never sends the documents or the spreadsheet anywhere.
- It never posts anything into accounting software.
- It never gives tax advice. If the user asks whether VAT can be reclaimed on
  something, say that's a question for their accountant.

---

Made by JN Technology · jntechnology.co.uk · Free to use and change.
