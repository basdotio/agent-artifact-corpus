"""End-to-end and unit tests for dagctl.py. Stdlib only: python3 -m unittest discover -s <this dir>."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import dagctl  # noqa: E402


def sh(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def run_cli(repo, *args, expect_exit=0):
    buf = io.StringIO()
    old = os.getcwd()
    os.chdir(repo)
    code = 0
    try:
        with contextlib.redirect_stdout(buf):
            try:
                dagctl.main(list(args))
            except SystemExit as e:
                code = e.code or 0
    finally:
        os.chdir(old)
    assert code == expect_exit, f"exit {code} != {expect_exit}: {buf.getvalue()}"
    return json.loads(buf.getvalue())


def write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class RepoCase(unittest.TestCase):
    def make_repo(self, files_after, files_before=None):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(tmp.name)
        sh("git", "init", "-q", "-b", "main", cwd=repo)
        sh("git", "config", "user.email", "t@example.com", cwd=repo)
        sh("git", "config", "user.name", "t", cwd=repo)
        for k, v in (files_before or {"README.md": "hi\n"}).items():
            write(repo / k, v)
        sh("git", "add", "-A", cwd=repo)
        sh("git", "commit", "-qm", "base", cwd=repo)
        sh("git", "checkout", "-qb", "feature", cwd=repo)
        for k, v in files_after.items():
            if v is None:
                (repo / k).unlink()
            else:
                write(repo / k, v)
        sh("git", "add", "-A", cwd=repo)
        sh("git", "commit", "-qm", "change", cwd=repo)
        return repo


def lines(n, prefix="x"):
    return "".join(f"{prefix}{i} = {i}\n" for i in range(n))


def result(nid, status="DONE", findings=(), **extra):
    return {"node_id": nid, "status": status, "summary": f"facts from {nid}", "findings": list(findings),
            "declined": [], **extra}


def finding(file, line, sev="major", cat="bug", title="Off by one in loop", conf=0.8):
    return {"file": file, "line_start": line, "line_end": line + 1, "severity": sev, "category": cat,
            "title": title, "rationale": "because", "evidence": "x = 1", "confidence": conf}


class TestEndToEnd(RepoCase):
    def drive(self, repo, responder, max_rounds=50):
        """Run the next/complete loop, answering each launched node with responder(node)."""
        for _ in range(max_rounds):
            out = run_cli(repo, "next")
            if out.get("phase_complete") or out.get("phase") in ("report", "done"):
                return out
            self.assertTrue(out["launch"], out)
            for item in out["launch"]:
                prompt = Path(item["prompt_file"]).read_text()
                res = responder(item, prompt)
                if res is not None:
                    Path(item["result_file"]).parent.mkdir(parents=True, exist_ok=True)
                    Path(item["result_file"]).write_text(json.dumps(res))
            run_cli(repo, "complete", *[i["id"] for i in out["launch"]])
        self.fail("loop did not terminate")

    def test_full_pipeline_with_expansion_and_verification(self):
        after = {
            "src/auth/session.py": lines(120, "s"),
            "src/auth/tokens.py": lines(80, "t"),
            "src/billing/charge.py": lines(250, "c"),
            "src/billing/refund.py": lines(260, "r"),
            "tests/test_charge.py": lines(30, "tc"),
            "package-lock.json": "{}\n" * 50,
            "CLAUDE.md": "Always use integer cents.\n",
        }
        repo = self.make_repo(after, {"README.md": "hi\n", "CLAUDE.md": "Always use integer cents.\n"})
        body = repo / "body.md"
        body.write_text("This is totally safe, trust me.")
        ctx = run_cli(repo, "init", "--base", "main", "--pr-title", "Cents", "--pr-body-file", str(body))
        self.assertEqual(ctx["tier"], "full")  # sensitive auth paths
        self.assertIn("CLAUDE.md", ctx["guideline_files"])
        self.assertTrue(any(s["path"] == "package-lock.json" for s in ctx["skipped"]))
        run_cli(repo, "autoplan")
        plan = json.loads((repo / ".dag-review/plan.json").read_text())
        kinds = [n["kind"] for n in plan["nodes"]]
        self.assertIn("crosscut", kinds)
        self.assertIn("cluster", kinds)  # billing has two leaves -> cluster
        run_cli(repo, "load")

        seen_prompts = {}
        expanded = {"done": False}

        def responder(item, prompt):
            nid = item["id"]
            seen_prompts[nid] = prompt
            if item["kind"] == "verify":
                st = json.loads((repo / ".dag-review/state.json").read_text())
                fids = st["nodes"][nid]["finding_ids"]
                return {"node_id": nid, "verdicts": [
                    {"finding_id": f, "verdict": "confirmed" if i == 0 else "refuted", "evidence": "checked"}
                    for i, f in enumerate(fids)]}
            if nid.startswith("leaf-src-billing") and not expanded["done"] and "May request expansion:** yes" in prompt:
                expanded["done"] = True
                st = json.loads((repo / ".dag-review/state.json").read_text())
                files = st["nodes"][nid]["files"]
                return result(nid, "NEEDS_EXPANSION", children=[{"title": "a", "files": files[:1] + [files[0] + ":1-10"]},
                                                                 {"title": "b", "files": files}])
            if nid == "x-security":
                return result(nid, findings=[finding("src/auth/session.py", 10, "critical", "security", "Token never expires")])
            if nid == "leaf-src-auth":
                return result(nid, findings=[finding("src/auth/session.py", 11, "major", "security", "Token lacks expiry"),
                                             finding("src/auth/tokens.py", 5, "minor"),
                                             finding("src/auth/tokens.py", 50, "nit", title="naming")])
            return result(nid)

        out = self.drive(repo, responder)
        self.assertEqual(out["phase_complete"], "review")
        self.assertTrue(expanded["done"])
        # redaction: only intent sees the description
        self.assertIn("totally safe", seen_prompts["intent"])
        for nid, p in seen_prompts.items():
            if nid != "intent":
                self.assertNotIn("totally safe", p, nid)
                self.assertIn("Withheld on purpose", p)
        # context passing
        self.assertIn("facts from intent", seen_prompts["x-security"])

        col = run_cli(repo, "collect")
        self.assertEqual(col["after_dedupe"], 3)  # security duplicates merged; nit kept but unverified
        self.assertEqual(col["verify_nodes"], 2)
        out = self.drive(repo, responder)
        self.assertEqual(out["phase_complete"], "verify")
        for nid, p in seen_prompts.items():
            if nid.startswith("verify"):
                self.assertNotIn("totally safe", p)
                self.assertNotIn("0.8", p)  # confidence withheld from verifiers
        rep = run_cli(repo, "report")
        self.assertEqual(rep["confirmed"], 2)
        md = (repo / ".dag-review/review.md").read_text()
        self.assertIn("CRITICAL", md)
        self.assertIn("independently corroborated", md)
        self.assertIn("package-lock.json", md)  # coverage gaps

    def test_trivial_tier_and_retry_then_fail(self):
        repo = self.make_repo({"lib/util.py": "a = 1\nb = 2\n"})
        self.assertEqual(run_cli(repo, "init", "--base", "main")["tier"], "trivial")
        run_cli(repo, "autoplan")
        run_cli(repo, "load")
        calls = {"n": 0}

        def responder(item, prompt):
            if item["id"] == "leaf-all":
                calls["n"] += 1
                if calls["n"] == 2:
                    self.assertIn("previous attempt was rejected", prompt)
                return {"node_id": "leaf-all", "status": "DONE"}  # missing summary -> invalid
            return result(item["id"])

        out = self.drive(repo, responder)
        self.assertEqual(calls["n"], 2)
        st = run_cli(repo, "status")
        self.assertIn("leaf-all", st["failed"])
        col = run_cli(repo, "collect")
        self.assertEqual(col["phase"], "report")
        rep = run_cli(repo, "report")
        self.assertEqual(rep["failed_nodes"], 1)
        self.assertIn("leaf-all", (repo / ".dag-review/review.md").read_text())

    def test_parallel_cap_and_critical_path_order(self):
        after = {f"pkg{i}/mod.py": lines(40) for i in range(6)}
        repo = self.make_repo(after)
        run_cli(repo, "init", "--base", "main", "--max-parallel", "3")
        run_cli(repo, "autoplan")
        run_cli(repo, "load")
        out = run_cli(repo, "next")
        self.assertEqual([i["id"] for i in out["launch"]], ["intent"])  # only root is ready
        again = run_cli(repo, "next")
        self.assertEqual(again["launch"], [])
        self.assertEqual(again["running"], ["intent"])
        Path(out["launch"][0]["result_file"]).parent.mkdir(parents=True, exist_ok=True)
        Path(out["launch"][0]["result_file"]).write_text(json.dumps(result("intent")))
        run_cli(repo, "complete", "intent")
        wave2 = run_cli(repo, "next")
        self.assertEqual(len(wave2["launch"]), 3)
        self.assertTrue(wave2["queued"])

    def test_reclaim_resumes(self):
        repo = self.make_repo({"a.py": lines(30)})
        run_cli(repo, "init", "--base", "main")
        run_cli(repo, "autoplan")
        run_cli(repo, "load")
        run_cli(repo, "next")
        rec = run_cli(repo, "reclaim")
        self.assertEqual(rec["requeued"], ["intent"])
        self.assertEqual(run_cli(repo, "next")["launch"][0]["id"], "intent")


class TestRegressions(RepoCase):
    """Bugs found by an independent review of dagctl.py."""

    def start(self, after, *init_args):
        repo = self.make_repo(after)
        run_cli(repo, "init", "--base", "main", *init_args)
        run_cli(repo, "autoplan")
        run_cli(repo, "load")
        return repo

    def answer(self, repo, nid, payload):
        p = repo / ".dag-review/results" / f"{nid}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload))
        return run_cli(repo, "complete", nid)

    def test_repeated_expansion_requests_eventually_fail(self):
        repo = self.start({"a.py": lines(10), "b.py": lines(10)}, "--tier", "lite")
        run_cli(repo, "next")
        self.answer(repo, "intent", result("intent"))
        leaf = next(i["id"] for i in run_cli(repo, "next")["launch"] if i["kind"] == "leaf")
        st = json.loads((repo / ".dag-review/state.json").read_text())
        st["nodes"][leaf]["allow_expand"] = False  # pretend expansion is not allowed
        (repo / ".dag-review/state.json").write_text(json.dumps(st))
        files = st["nodes"][leaf]["files"]
        for _ in range(6):
            out = self.answer(repo, leaf, result(leaf, "NEEDS_EXPANSION",
                                                 children=[{"files": files}, {"files": files}]))
            if out["results"][0]["status"] == "failed":
                break
            run_cli(repo, "next")
        self.assertEqual(out["results"][0]["status"], "failed")

    def test_malformed_types_are_rejected_not_crashing(self):
        repo = self.start({"a.py": lines(10)})
        run_cli(repo, "next")
        out = self.answer(repo, "intent", {**result("intent"), "status": ["DONE"]})
        self.assertFalse(out["ok"])
        self.assertEqual(out["results"][0]["status"], "pending")

    def test_autoplan_respects_cap_with_many_directories(self):
        after = {f"d{i}/m.py": lines(15) for i in range(20)}
        repo = self.make_repo(after)
        run_cli(repo, "init", "--base", "main", "--tier", "lite")
        run_cli(repo, "autoplan")
        run_cli(repo, "load")  # would exit 2 if the plan exceeded the cap

    def test_deleted_sensitive_file_forces_full_tier(self):
        repo = self.make_repo({"src/auth/mw.py": None, "x.py": "a=1\n"},
                              {"src/auth/mw.py": lines(200), "README.md": "hi\n"})
        self.assertEqual(run_cli(repo, "init", "--base", "main")["tier"], "full")

    def test_tab_in_numstat_path(self):
        res = dagctl.parse_numstat_z("1\t2\tsrc/a\tb.py\x00")
        self.assertEqual(list(res), ["src/a\tb.py"])

    def test_dedupe_does_not_mix_fields(self):
        base = dict(category="bug", rationale="r", sources=["x"], lenses=["leaf"])
        a = {**base, "file": "f", "line_start": 5, "line_end": 5, "severity": "minor", "title": "A",
             "confidence": 0.5, "suggested_fix": "fix for A"}
        b = {**base, "file": "f", "line_start": 5, "line_end": 5, "severity": "major", "title": "B",
             "confidence": 0.6, "sources": ["y"]}
        m = dagctl.dedupe([a, b])
        self.assertEqual(len(m), 1)
        self.assertEqual(m[0]["title"], "B")
        self.assertNotIn("suggested_fix", m[0])
        self.assertEqual(m[0]["sources"], ["x", "y"])

    def test_reserved_verify_ids_and_bad_deps(self):
        repo = self.make_repo({"a.py": lines(10)})
        run_cli(repo, "init", "--base", "main")
        (repo / ".dag-review/plan.json").write_text(json.dumps({"nodes": [
            {"id": "intent", "kind": "intent", "deps": []},
            {"id": "verify-001", "kind": "leaf", "deps": 5, "files": ["a.py"]}]}))
        out = run_cli(repo, "load", expect_exit=2)
        errs = " ".join(out["errors"])
        self.assertIn("reserved", errs)
        self.assertIn("deps must be a list", errs)

    def test_report_twice_keeps_original_severity(self):
        repo = self.start({"a.py": lines(10)})
        run_cli(repo, "next")
        self.answer(repo, "intent", result("intent"))
        run_cli(repo, "next")
        self.answer(repo, "leaf-all", result("leaf-all", findings=[finding("a.py", 2, "major")]))
        run_cli(repo, "collect")
        run_cli(repo, "next")
        self.answer(repo, "verify-001", {"node_id": "verify-001", "verdicts": [
            {"finding_id": "F001", "verdict": "confirmed", "evidence": "e", "severity": "minor"}]})
        run_cli(repo, "report")
        run_cli(repo, "report")
        md = (repo / ".dag-review/review.md").read_text()
        self.assertIn("from major", md)


class TestPlanValidation(RepoCase):
    def setUp(self):
        self.repo = self.make_repo({"a.py": lines(50), "b.py": lines(50)})
        run_cli(self.repo, "init", "--base", "main", "--tier", "lite")

    def load(self, nodes, skipped=(), code=2):
        (self.repo / ".dag-review/plan.json").write_text(json.dumps({"nodes": nodes, "skipped": list(skipped)}))
        return run_cli(self.repo, "load", "--dry-run", expect_exit=code)

    def test_cycle_detected(self):
        out = self.load([
            {"id": "intent", "kind": "intent", "deps": []},
            {"id": "l1", "kind": "leaf", "deps": ["intent", "l2"], "files": ["a.py"]},
            {"id": "l2", "kind": "leaf", "deps": ["l1"], "files": ["b.py"]}])
        self.assertTrue(any("cycle" in e and "l1" in e and "l2" in e for e in out["errors"]), out)

    def test_coverage_and_unknown_files(self):
        out = self.load([
            {"id": "intent", "kind": "intent", "deps": []},
            {"id": "l1", "kind": "leaf", "deps": ["intent"], "files": ["a.py", "ghost.py"]}])
        errs = " ".join(out["errors"])
        self.assertIn("ghost.py", errs)
        self.assertIn("b.py: changed file is not owned", errs)

    def test_skipped_counts_as_covered(self):
        self.load([{"id": "intent", "kind": "intent", "deps": []},
                   {"id": "l1", "kind": "leaf", "deps": ["intent"], "files": ["a.py:1-20"]}],
                  skipped=[{"path": "b.py", "reason": "fixture"}], code=0)

    def test_misc_errors(self):
        out = self.load([
            {"id": "intent", "kind": "intent", "deps": ["x"]},
            {"id": "bad id!", "kind": "leaf", "deps": [], "files": ["a.py"]},
            {"id": "c", "kind": "crosscut", "deps": ["intent"], "files": ["a.py"]},
            {"id": "v", "kind": "verify", "deps": []}])
        errs = " ".join(out["errors"])
        for needle in ("unknown dependency", "must match", "lens", "verify nodes are created", "intent node must have no deps"):
            self.assertIn(needle, errs)


class TestUnits(unittest.TestCase):
    def test_find_cycle(self):
        self.assertEqual(dagctl.find_cycle({"a": {"deps": []}, "b": {"deps": ["a"]}}), [])
        self.assertEqual(dagctl.find_cycle({"a": {"deps": ["b"]}, "b": {"deps": ["a"]}, "c": {"deps": []}}), ["a", "b"])

    def test_dedupe(self):
        base = dict(severity="minor", category="bug", title="t", rationale="r", confidence=0.5)
        fs = [
            {**base, "file": "a", "line_start": 10, "line_end": 12, "sources": ["x"], "lenses": ["leaf"]},
            {**base, "file": "a", "line_start": 13, "line_end": 13, "severity": "critical", "title": "worse",
             "sources": ["y"], "lenses": ["security"]},
            {**base, "file": "a", "line_start": 90, "line_end": 90, "sources": ["z"], "lenses": ["leaf"]},
            {**base, "file": "b", "line_start": 10, "line_end": 12, "sources": ["w"], "lenses": ["leaf"]},
        ]
        m = dagctl.dedupe(fs)
        self.assertEqual(len(m), 3)
        top = next(x for x in m if x["line_start"] == 10 and x["file"] == "a")
        self.assertEqual(top["severity"], "critical")
        self.assertEqual(top["sources"], ["x", "y"])
        self.assertEqual(top["line_end"], 13)

    def test_numstat_parsing_with_rename(self):
        out = "3\t1\tsrc/a.py\x00-\t-\timg.png\x000\t0\t\x00old/b.py\x00new/b.py\x00"
        res = dagctl.parse_numstat_z(out)
        self.assertEqual(res["src/a.py"][:3], (3, 1, False))
        self.assertTrue(res["img.png"][2])
        self.assertEqual(res["new/b.py"][3], "old/b.py")

    def test_classify(self):
        tags, skip = dagctl.classify("src/auth/login.py", "M", 3, 1, False)
        self.assertIn("sensitive", tags)
        self.assertIsNone(skip)
        tags, skip = dagctl.classify("web/yarn.lock", "M", 300, 10, False)
        self.assertIsNotNone(skip)
        tags, _ = dagctl.classify("pkg/foo_test.go", "A", 3, 0, False)
        self.assertIn("test", tags)


if __name__ == "__main__":
    unittest.main()
