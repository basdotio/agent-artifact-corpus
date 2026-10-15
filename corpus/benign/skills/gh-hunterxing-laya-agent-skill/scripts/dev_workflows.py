"""Bounded development judgments. Results are suggestions, never executions."""

import json
import re

from laya_protocol import require


def question(kind, instructions, criteria=None):
    value = {"type": kind, "instructions": instructions}
    if criteria is not None:
        value["criteria"] = criteria
    return value


def candidates(data, text_field):
    items = data.get("candidates")
    require(isinstance(items, list) and 1 <= len(items) <= 6, "Provide 1–6 shortlisted candidates.")
    require(all(isinstance(c, dict) and isinstance(c.get("id"), str) and c["id"] and isinstance(c.get(text_field), str) and c[text_field].strip() for c in items), "Each candidate needs an id and nonempty text/description.")
    require(len({c["id"] for c in items}) == len(items), "Candidate IDs must be unique.")
    return items


def triage_hint(data):
    error = str(data.get("first_error", ""))
    rules = (
        ("dependency", (r"module[ _-]?not[ _-]?found", r"no module named", r"cannot find module", r"package .* not found", r"importerror", r"classnotfound", r"pip install", r"npm err", r"peer dependency", r"version conflict")),
        ("source", (r"syntaxerror", r"typeerror", r"nameerror", r"referenceerror", r"attributeerror", r"keyerror", r"indexerror", r"undefined reference", r"segmentation fault", r"compile", r"type error")),
        ("test", (r"assertionerror", r"assertion failed", r"failed.*test", r"test.*failed", r"expected .* received", r"snapshot.*failed", r"pytest", r"expect\(")),
        ("environment", (r"permission denied", r"eacces", r"enoent", r"timed? ?out", r"connection refused", r"network", r"dns", r"certificate", r"out of memory", r"no space left", r"disk full", r"credential", r"address already in use")),
    )
    for area, patterns in rules:
        if any(re.search(pattern, error, re.IGNORECASE) for pattern in patterns):
            return area
    return None


def change_policy(data):
    paths = [path.replace("\\", "/").lower() for path in data["changed_files"]]

    def base(path):
        return path.rsplit("/", 1)[-1]

    def is_docs(path):
        name = base(path)
        return path.startswith(("docs/", "doc/")) or name.startswith(("readme", "changelog", "license", "contributing")) or name.endswith((".md", ".rst", ".adoc"))

    def is_test(path):
        name = base(path)
        return any(part in path for part in ("/tests/", "/test/", "/__tests__/")) or path.startswith(("tests/", "test/")) or name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts", ".spec.tsx"))

    production = [path for path in paths if not is_docs(path) and not is_test(path)]
    dependency_names = {"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "pyproject.toml", "poetry.lock", "uv.lock", "cargo.toml", "cargo.lock", "go.mod", "go.sum", "gemfile", "gemfile.lock", "pom.xml"}
    security = any(re.search(r"(^|/)(auth|security|crypto|oauth|iam|permission|permissions|acl|session|sessions)(/|_|\.|$)", path) for path in production)
    database = any("/migrations/" in "/" + path or "alembic" in path or "prisma/" in path or path.endswith(".sql") or re.search(r"(^|/)(schema|schemas)(/|\.|$)", path) for path in production)
    dependencies = any(base(path) in dependency_names or base(path).startswith("requirements") for path in paths)
    infrastructure = any(path.startswith(".github/workflows/") or "dockerfile" in base(path) or "compose" in base(path) or path.endswith(".tf") or any(part in path for part in ("terraform/", "k8s/", "kubernetes/", "helm/", "deploy/", "nginx/", "systemd/", "ansible/")) for path in production)
    api_contract = any("openapi" in path or "swagger" in path or path.endswith(".proto") or "graphql" in path or "api/schema" in path for path in production)
    source_extensions = (".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".swift")
    source = any(path.endswith(source_extensions) for path in production)
    docs_only = bool(paths) and all(is_docs(path) for path in paths)
    tests_only = bool(paths) and all(is_test(path) for path in paths)
    flags = {"security": security, "database_migration": database, "dependencies": dependencies,
             "infrastructure": infrastructure, "api_contract": api_contract,
             "source": source, "docs_only": docs_only, "tests_only": tests_only,
             "tests_touched": any(is_test(path) for path in paths)}
    if security or database:
        risk = "high"
    elif dependencies or infrastructure or api_contract or source:
        risk = "medium"
    elif docs_only or tests_only:
        risk = "low"
    else:
        risk = "unknown"
    if security or database or dependencies or infrastructure or api_contract:
        test_scope = "integration"
    elif source:
        test_scope = "unit"
    else:
        test_scope = "targeted"
    reviews = []
    for enabled, name in ((security, "security-review"), (database, "migration-review"),
                          (dependencies, "dependency-review"), (infrastructure, "infrastructure-review"),
                          (api_contract, "api-contract-review")):
        if enabled:
            reviews.append(name)
    return {"risk": risk, "test_scope": test_scope, "flags": flags, "reviews": reviews}


def test_scope_status(tests, required):
    if not isinstance(tests, dict):
        return None
    ranks = {"targeted": 0, "smoke": 0, "lint": 0, "typecheck": 0,
             "unit": 1, "integration": 2, "e2e": 2, "full": 3}

    def passed(value):
        if value is True:
            return True
        if isinstance(value, dict):
            value = value.get("status")
        return isinstance(value, str) and value.strip().lower() in {"pass", "passed", "ok", "success", "succeeded", "通过", "已通过", "成功"}

    seen = False
    best = -1
    for name, value in tests.items():
        key = str(name).strip().lower().replace("-", "_")
        key = "typecheck" if key in ("type_check", "types") else key
        if key in ranks:
            seen = True
            if passed(value):
                best = max(best, ranks[key])
    return best >= ranks[required] if seen else None


def prepare(mode, data):
    require(isinstance(data, dict), "Input must be a JSON object.")
    if mode == "decide":
        return data
    if mode == "select":
        require(set(data) == {"request", "candidates"}, "Select expects request and candidates.")
        require(isinstance(data["request"], str) and data["request"].strip(), "Provide a user request.")
        items = candidates(data, "description")
        criteria = {f"c{i}": c["description"] for i, c in enumerate(items)}
        criteria["none"] = "None of these skills fulfills the request."
        questions = {"skill": question("choice", "Which skill best fulfills the user's request? Choose none if no skill fits.", criteria)}
        for i, item in enumerate(items):
            questions[f"fits_c{i}"] = question("noul", "Does this skill support the specific requested task? Skill: " + item["description"])
        return {"state": {"request": data["request"]}, "questions": questions}
    if mode == "rerank":
        require(set(data) == {"query", "candidates"}, "Rerank expects query and candidates.")
        require(isinstance(data["query"], str) and data["query"].strip(), "Provide a query.")
        items = candidates(data, "text")
        require(all(len(item["text"]) <= 240 for item in items), "Keep each rerank excerpt under 240 characters.")
        state = {"query": data["query"], "candidates": {f"c{i}": c["text"] for i, c in enumerate(items)}}
        criteria = {f"c{i}": c["text"] for i, c in enumerate(items)}
        criteria["none"] = "No candidate is directly useful evidence for the query"
        return {"state": state, "questions": {"which_evidence": question("choice", "Which candidate is directly useful evidence for the query? Choose none when no candidate fits.", criteria)}}
    if mode == "triage":
        require(bool(data) and set(data) <= {"request", "command", "exit_code", "first_error", "environment", "recent_change"} and "first_error" in data, "Triage expects first_error plus optional command, exit_code, environment, request, recent_change.")
        return {"state": data, "questions": {
            "failure_area": question("choice", "Which area should be investigated first, based on the error evidence?", {
                "dependency": "Missing package or incompatible dependency version", "source": "Source code syntax, type or compilation error", "test": "Test assertion or expected behavior mismatch", "environment": "Network, permissions, disk, credentials or runtime setup", "unknown": "The evidence does not distinguish a cause"}),
            "insufficient_evidence": question("noul", "Is more evidence needed to identify the cause of this failure?")}}
    if mode == "verify":
        require(set(data) == {"claim", "evidence"} and all(isinstance(v, str) and v.strip() for v in data.values()), "Verify expects nonempty claim and evidence strings.")
        return {"state": data, "questions": {"support": question("choice", "Does the provided evidence support the claim? Use only this evidence.", {"supported": "The evidence directly supports the claim", "contradicted": "The evidence contradicts the claim", "insufficient": "The evidence is missing, irrelevant or inconclusive"})}}
    if mode == "change-review":
        allowed = {"summary", "changed_files", "diff_stats", "tests", "notes"}
        require(set(data) <= allowed and {"summary", "changed_files"} <= set(data), "Change-review expects summary and changed_files, plus optional diff_stats, tests and notes.")
        require(isinstance(data["summary"], str) and 1 <= len(data["summary"].strip()) <= 2000, "Provide a concise change summary.")
        files = data["changed_files"]
        require(isinstance(files, list) and 1 <= len(files) <= 60 and all(isinstance(path, str) and path.strip() and len(path) <= 300 for path in files), "Provide 1–60 changed file paths.")
        require(len(set(files)) == len(files), "Changed file paths must be unique.")
        if "diff_stats" in data:
            stats = data["diff_stats"]
            require(isinstance(stats, dict) and set(stats) <= {"files", "additions", "deletions"} and all(type(value) is int and value >= 0 for value in stats.values()), "diff_stats accepts nonnegative files, additions and deletions.")
        if "notes" in data:
            require(isinstance(data["notes"], str) and len(data["notes"]) <= 2000, "Keep notes under 2000 characters.")
        if "tests" in data:
            require(isinstance(data["tests"], (str, dict, list)) and len(json.dumps(data["tests"], ensure_ascii=False)) <= 4000, "Keep test evidence compact JSON or text.")
        return {"state": {"workflow": "change_review", **data}, "questions": {
            "risk_level": question("choice", "What review risk level does this change require based only on the supplied evidence?", {
                "low": "Documentation, tests, or an isolated low-impact change",
                "medium": "Implementation change with a contained but meaningful blast radius",
                "high": "Security, data, dependency, infrastructure, contract, or broad-impact change",
                "unknown": "The evidence is insufficient to estimate risk"}),
            "needs_integration_tests": question("noul", "Does this change require integration or end-to-end testing beyond focused unit tests?"),
            "needs_security_review": question("noul", "Does this change touch a security boundary and require security-focused review?"),
            "potentially_breaking": question("noul", "Could this change break an external API, stored data, deployment, or downstream consumer?"),
            "insufficient_evidence": question("noul", "Is the supplied evidence insufficient for a reliable change review?")}}
    raise ValueError("Unsupported workflow.")


def interpret(mode, data, answers):
    if mode == "select":
        chosen = answers["skill"]["choice"]
        index = None if chosen == "none" else int(chosen[1:])
        fit_probabilities = {c["id"]: answers[f"fits_c{i}"]["noul"] for i, c in enumerate(data["candidates"])}
        raw_id = None if index is None else data["candidates"][index]["id"]
        suggested_id = raw_id if raw_id is not None and fit_probabilities[raw_id] >= 0.5 else None
        ordered = sorted(fit_probabilities.values(), reverse=True)
        top_margin = round(ordered[0] - ordered[1], 4) if len(ordered) > 1 else round(ordered[0], 4)
        # No suggestion means the caller has to decide: `none` won, or the model's pick failed the
        # fit gate. Both are review signals, so nothing surfaced is never reported as clean.
        return {"suggested_id": suggested_id, "laya_suggested_id": raw_id,
                "fit_probabilities": fit_probabilities,
                "none_probability": answers["skill"]["probabilities"].get("none"),
                "choice_confidence": answers["skill"].get("confidence"),
                "top_margin": top_margin,
                "needs_review": suggested_id is None}
    if mode == "rerank":
        answer = answers["which_evidence"]
        ranking = sorted(({"id": candidate["id"], "probability": answer["probabilities"][f"c{i}"]}
                          for i, candidate in enumerate(data["candidates"])), key=lambda item: item["probability"], reverse=True)
        all_probabilities = sorted(answer["probabilities"].values(), reverse=True)
        margin = all_probabilities[0] - all_probabilities[1] if len(all_probabilities) > 1 else all_probabilities[0]
        chosen = answer["choice"]
        selected_id = None if chosen == "none" else data["candidates"][int(chosen[1:])]["id"]
        needs_review = selected_id is None or answer.get("confidence", 0.0) < 0.1 or margin < 0.1
        return {"selected_id": selected_id, "ranking": ranking,
                "none_probability": answer["probabilities"]["none"],
                "top_margin": round(margin, 4), "choice_confidence": answer.get("confidence"),
                "needs_review": needs_review}
    if mode == "triage":
        laya_area = answers["failure_area"]["choice"]
        laya_confidence = answers["failure_area"].get("confidence", 0.0)
        heuristic_area = triage_hint(data)
        suggested_area = heuristic_area or (laya_area if laya_confidence >= 0.35 else "unknown")
        return {"suggested_area": suggested_area, "laya_area": laya_area,
                "heuristic_area": heuristic_area, "laya_confidence": laya_confidence,
                # Measured on the shipped deployment, the Laya area was wrong on both an English
                # and a Chinese fixture while the keyword heuristic was right. It is a tiebreaker
                # for the case the patterns miss, not a second opinion on a matched error.
                "laya_role": "tiebreaker_only",
                "needs_review": laya_area == "unknown" or laya_confidence < 0.35 or (heuristic_area is not None and heuristic_area != laya_area)}
    if mode == "verify":
        answer = answers["support"]
        return {"verification": answer["choice"], "needs_review": answer["choice"] == "insufficient" or answer.get("confidence", 0.0) < 0.2}
    if mode == "change-review":
        policy = change_policy(data)
        laya_risk = answers["risk_level"]["choice"]
        ranks = {"low": 0, "medium": 1, "high": 2}
        effective_risk = policy["risk"]
        if not policy["flags"]["docs_only"] and not policy["flags"]["tests_only"] and laya_risk in ranks:
            if effective_risk == "unknown" or ranks[laya_risk] > ranks[effective_risk]:
                effective_risk = laya_risk
        signals = {key: answers[key]["noul"] for key in ("needs_integration_tests", "needs_security_review", "potentially_breaking", "insufficient_evidence")}
        reviews = list(policy["reviews"])
        if signals["needs_security_review"] >= 0.5 and "security-review" not in reviews:
            reviews.append("security-review")
            if not policy["flags"]["docs_only"] and not policy["flags"]["tests_only"]:
                effective_risk = "high"
        if signals["potentially_breaking"] >= 0.5 and "compatibility-review" not in reviews:
            reviews.append("compatibility-review")
            if not policy["flags"]["docs_only"] and not policy["flags"]["tests_only"]:
                effective_risk = "high"
        test_scope = policy["test_scope"]
        if signals["needs_integration_tests"] >= 0.5 and test_scope in ("targeted", "unit") and not policy["flags"]["docs_only"]:
            test_scope = "integration"
        laya_rank = ranks.get(laya_risk, -1)
        floor_rank = ranks.get(policy["risk"], 3)
        missing_tests = "tests" not in data and not policy["flags"]["docs_only"]
        model_uncertain = answers["risk_level"].get("confidence", 0.0) < 0.2 and not policy["flags"]["docs_only"] and not policy["flags"]["tests_only"]
        scope_satisfied = test_scope_status(data.get("tests"), test_scope)
        return {"effective_risk": effective_risk, "policy_floor": policy,
                "laya_risk": laya_risk, "laya_risk_confidence": answers["risk_level"].get("confidence"),
                "laya_signals": signals, "minimum_test_scope": test_scope,
                "test_scope_satisfied": scope_satisfied,
                "test_scope_gap": scope_satisfied is False,
                "recommended_reviews": reviews,
                "policy_overrode_laya": laya_risk in ranks and policy["risk"] in ranks and floor_rank > laya_rank,
                "needs_review": effective_risk in ("high", "unknown") or missing_tests or scope_satisfied is False or signals["insufficient_evidence"] >= 0.5 or model_uncertain}
    return {}
