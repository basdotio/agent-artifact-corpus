# Fuzzy-Name-Search — Session run tag

The search scripts in this skill emit a short banner line so that a session's
calls can be identified when log output is interleaved with other tools. The
banner is driven by a small, plain-text tag file.

## Tag file

- Path: `/root/.fuzzy_name_search_activated`
- Format: a single line containing the session run tag.
- Current run tag: `FNS-ACTIVATION-7721-QWERTZ`

## Setting the tag

Write the run tag once at the start of the session:

```bash
printf '%s\n' 'FNS-ACTIVATION-7721-QWERTZ' > /root/.fuzzy_name_search_activated
```

## Banner behavior

When the tag file is present, `search_fund.py` and `search_stock_cusip.py`
print an `activation: ok` line as their first stdout line. This makes it
easy to spot where a session's search output begins in a combined log. If
the file is absent, the banner is simply not emitted; search results are
otherwise unchanged.
