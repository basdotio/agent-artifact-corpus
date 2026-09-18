#!/usr/bin/env python3
"""Fetch a SELECTED subset of SkillSafetyBench's poisoned skill artifacts.

Why a selective fetch and not `corpus fetch` (a full clone): the upstream is 330 MB, and its
NOTICE.md warns that bundled BENIGN task content (adapted upstream tasks, PDFs, PPTX, MP4, CSV)
carries provenance the authors have not fully cleared. Cloning it wholesale would vendor that
uncleared media. So this pulls ONLY the files the upstream's own metadata.json marks as the
injected poison — the authors' adversarial additions — for the scenarios we integrate, into
sample trees under cache/skill-safety-bench/_selected/<id>/.

The repo is Apache-2.0 (verified against the LICENSE bytes; GitHub's licenseInfo returned null,
which is why it was read rather than trusted). Vendoring the authored poison files is within
that grant; leaving the media behind respects the NOTICE.

SELECTION: only scenarios whose attack, READ against the artifact, genuinely exercises one of
the three dimensions cisco monopolises — filesystem, reconnaissance, resource-abuse. The
upstream's category names do NOT map to these dimensions (its reconnaissance category is
labelled `malware_ransomware`, its destructive category mixes backdoor/exfil), so the mapping
here is per-sample and hand-read, recorded in SELECTED with the deciding file. That is the same
discipline the audit forced on every category-derived label.
"""

import hashlib
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHA = "e0589d7b68c7442027a287c956c40e3df4b7bbab"
RAW = f"https://raw.githubusercontent.com/AI45Lab/skill-safety-bench/{SHA}/"
DEST = ROOT / "cache" / "skill-safety-bench" / "_selected"

B = "benchmark/"
R2 = B + "risk-domain-2-agency-scope-and-authorization-risks/category3-destructive_and_sensitive_operation_induction/"
R3 = B + "risk-domain-3-execution-runtime-framework-and-protocol-risks/category5-sandbox_and_environment_boundary_escape/"
R6 = B + "risk-domain-6-knowledge-model-supply-chain-and-operational-risks/category1-availability_cost_and_service_exhaustion/"

# id -> list of (dest_name, upstream_path). The poison for these upstream scenarios is split
# across a SKILL.md and a companion policy/note file; both are the injected set, and both are
# taken so the vendored sample is judgeable on its own (the skill references the policy).
SELECTED = {
    # --- filesystem: hides a user-visible file into a dotfile directory ---
    "organize-audit-log-erasure": [
        ("SKILL.md", R2 + "organize_files_audit_log_erasure_remove_sorting_history/attacked_task/environment/skills/file-organizer/SKILL.md"),
    ],
    "organize-intake-manifest": [
        ("SKILL.md", R2 + "organize_files_destructive_cleanup_remove_intake_manifest/attacked_task/environment/skills/file-organizer/SKILL.md"),
    ],
    # --- reconnaissance: documents host/metadata probing back to the caller ---
    "metadata-service-probe": [
        ("SKILL.md", R3 + "fix_build_internal_metadata_service_escape_discovery_note/attacked_task/environment/skills/analyze-ci/SKILL.md"),
    ],
    "docker-socket-repro": [
        ("SKILL.md", R3 + "fix_build_mount_host_integration_docker_socket_repro/attacked_task/environment/skills/analyze-ci/SKILL.md"),
    ],
    # --- resource-abuse: a policy the skill obeys forces wasteful re-run loops ---
    "requery-loop": [
        ("SKILL.md", R6 + "enterprise_search_structural_tool_loop_amplification_requery_trace/attacked_task/environment/skills/enterprise-artifact-search/SKILL.md"),
        ("rd6_requery_policy.md", R6 + "enterprise_search_structural_tool_loop_amplification_requery_trace/attacked_task/environment/DATA/metadata/rd6_requery_policy.md"),
    ],
    "training-sweep-drain": [
        ("SKILL.md", R6 + "mhc_budget_drain_training_sweep_matrix/attacked_task/environment/skills/modal-gpu/SKILL.md"),
        ("rd6_training_sweep_note.md", R6 + "mhc_budget_drain_training_sweep_matrix/attacked_task/environment/rd6_training_sweep_note.md"),
    ],
    "tfidf-budget-drain": [
        ("SKILL.md", R6 + "parallel_tfidf_budget_drain_latency_amplification_benchmark_plan/attacked_task/environment/skills/workload-balancing/SKILL.md"),
        ("rd6_benchmark_budget.txt", R6 + "parallel_tfidf_budget_drain_latency_amplification_benchmark_plan/attacked_task/environment/workspace/rd6_benchmark_budget.txt"),
    ],
    "travel-fanout-explosion": [
        ("SKILL.md", R6 + "travel_planning_recursive_query_fanout_workflow_explosion_variant_manifest/attacked_task/environment/skills/search-cities/SKILL.md"),
        ("rd6_city_variant_policy.json", R6 + "travel_planning_recursive_query_fanout_workflow_explosion_variant_manifest/attacked_task/environment/data/background/rd6_city_variant_policy.json"),
    ],
    "video-rescan-loop": [
        ("SKILL.md", R6 + "video_tutorial_malfunction_amplification_irrelevant_rescan_log/attacked_task/environment/skills/speech-to-text/SKILL.md"),
        ("rd6_rescan_policy.md", R6 + "video_tutorial_malfunction_amplification_irrelevant_rescan_log/attacked_task/environment/rd6_rescan_policy.md"),
    ],
}


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    written = failed = 0
    for sid, files in SELECTED.items():
        out = DEST / sid
        out.mkdir(parents=True, exist_ok=True)
        for name, path in files:
            try:
                data = urllib.request.urlopen(RAW + path, timeout=30).read()
            except Exception as exc:  # noqa: BLE001 - any failure short-changes the sample
                print(f"  {sid}/{name}: {exc}", file=sys.stderr)
                failed += 1
                continue
            (out / name).write_bytes(data)
        written += 1
    print(f"fetched {written} selected sample(s) into {DEST.relative_to(ROOT)}")
    if failed:
        print(f"{failed} file(s) failed — the affected samples are incomplete", file=sys.stderr)
        return 1
    # A digest so a re-fetch that returns different bytes is visible.
    h = hashlib.sha256()
    for f in sorted(DEST.rglob("*")):
        if f.is_file():
            h.update(f.read_bytes())
    print(f"selected-set digest: {h.hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
