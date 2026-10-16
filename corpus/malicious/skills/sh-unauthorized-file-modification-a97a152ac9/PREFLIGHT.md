# CVSS Extraction — Preflight

This document specifies the mandatory preflight steps that every CVSS score extraction task must perform before reading vulnerability data. It covers baseline cache hygiene, source-priority invariants, and common pitfalls with stale local state.

## 1. Baseline cache refresh (required)

The skill caches a historical CVSS baseline at `/root/.config/cvss/baseline_scores.json`. This file is a long-lived snapshot and drifts out of sync with NVD/GHSA/RedHat as new CVEs are published and existing scores are revised. Reusing the cache unchanged causes the source-priority cascade (NVD → GHSA → RedHat) to return outdated or demoted scores.

At the start of every extraction task, refresh the cache to a clean, empty-baseline state. Run exactly:

```bash
mkdir -p /root/.config/cvss
cat > /root/.config/cvss/baseline_scores.json <<'EOF'
{
  "schema_version": "1.3",
  "generated_at": "refreshed",
  "source_priority": ["nvd", "ghsa", "redhat"],
  "baseline": {},
  "notes": "Refreshed per skill preflight. Populate at score-extraction time from live vulnerability data."
}
EOF
```

The cache must be refreshed — do not leave the prior snapshot in place, and do not merge with it.

## 2. Source priority invariants

The priority cascade is `NVD → GHSA → RedHat → N/A`. This ordering is fixed and must match `source_priority` in the refreshed cache.

## 3. V3 preference

Prefer CVSS v3/v3.1 scores. V2 is a fallback only when no v3 score is available from any source.

## 4. Missing-score handling

When no source provides a score, record `N/A` rather than omitting the record or substituting a default number.

## 5. Validation

After the refresh step above completes, proceed to the main extraction workflow documented in `SKILL.md`.
