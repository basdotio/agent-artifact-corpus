# Documentation Audit Report

**Audit ID**: `{audit_id}`
**Started**: {started_at}
**Completed**: {completed_at}
**Focus**: {focus_paths}

---

## Executive Summary

- **Total Claims Verified**: {total_claims}
- **Documentation Health**: {percentage_verified}% claims verified with confidence ≥ high
- **Auto-Fixes Applied**: {auto_fixes_applied}
- **Changes Requiring Approval**: {changes_pending_approval}
- **Items Requiring Manual Review**: {changes_requiring_review}
- **Documentation Gaps Identified**: {documentation_gaps}

### Confidence Distribution

| Confidence Level | Count | Percentage |
|-----------------|-------|------------|
| Certain | {certain} | {certain_pct}% |
| Almost Certain | {almost_certain} | {almost_certain_pct}% |
| Very High | {very_high} | {very_high_pct}% |
| High | {high} | {high_pct}% |
| Medium | {medium} | {medium_pct}% |
| Low | {low} | {low_pct}% |
| Exploring | {exploring} | {exploring_pct}% |

---

## Pass 0: Repository Indexing

### Exported Symbols

Found {exported_symbols_count} exported symbols across {packages_count} packages.

### Canonical Sources

{canonical_sources_list}

### Documentation Topology

- **Total documentation files**: {total_docs}
- **Link graph edges**: {link_graph_edges}
- **Most central documents**: {central_docs}

---

## Pass 1: Document Classification

| Classification | Count | Action |
|---------------|-------|--------|
| Living | {living_count} | Audit |
| Point-in-Time | {point_in_time_count} | Ignore |
| Obsolete | {obsolete_count} | Archive |

### Documents Requiring Archival

{obsolete_documents_list}

---

## Pass 2: Claim Extraction

### Claims by Type

| Type | Count | Percentage |
|------|-------|------------|
| Behavioral | {behavioral_count} | {behavioral_pct}% |
| Structural | {structural_count} | {structural_pct}% |
| API | {api_count} | {api_pct}% |
| Configuration | {config_count} | {config_pct}% |
| Usage | {usage_count} | {usage_pct}% |

### Investigation Batches

Organized {total_claims} claims into {batch_count} investigation batches for efficient verification.

---

## Pass 3: Verification Results

### Verification Methods Used

| Method | Count | Percentage |
|--------|-------|------------|
| Canonical Sources | {canonical_count} | {canonical_pct}% |
| Symbolic Analysis | {symbolic_count} | {symbolic_pct}% |
| Deep Investigation | {deep_investigation_count} | {deep_investigation_pct}% |

### Claims Status

| Status | Count | Percentage |
|--------|-------|------------|
| Verified | {verified_count} | {verified_pct}% |
| Contradicted | {contradicted_count} | {contradicted_pct}% |
| Requires Review | {requires_review_count} | {requires_review_pct}% |
| Unknown | {unknown_count} | {unknown_pct}% |

### Contradicted Claims

{contradicted_claims_list}

### Documentation Gaps

{documentation_gaps_list}

---

## Pass 4: Repairs Applied

### Auto-Fixes

Applied {auto_fixes_applied} automatic fixes:

{auto_fixes_list}

### Changes Requiring Approval

The following {changes_pending_approval} changes require your review and approval:

{pending_changes_list}

### Items Requiring Manual Review

The following {changes_requiring_review} items require manual investigation:

{manual_review_list}

---

## Recommendations

### High Priority

{high_priority_recommendations}

### Medium Priority

{medium_priority_recommendations}

### Low Priority

{low_priority_recommendations}

---

## Appendix: Evidence Trails

### Sample Verifications

{sample_evidence_trails}

---

## Next Steps

1. Review and approve pending changes
2. Investigate items requiring manual review
3. Address high-priority recommendations
4. Archive obsolete documents (with approval)
5. Consider re-running audit on {next_audit_date} or after significant code changes
