from __future__ import annotations

import base64
import csv
import functools
import hashlib
import html
import io
import json
import platform
import re
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from decimal import InvalidOperation
from importlib.metadata import version
from pathlib import Path

from connectors.local_model import compile_with_model
from connectors.ocds import award_history
from connectors.public_sources import lookup
from document_pipeline.extract import extract, verify_citation
from mcp_server.schemas.models import ApprovalRequest, CaseRequest, Citation, Criterion, Finding, Plan, ProductLine
from orchestrator.store import Store, canonical, digest, file_hash, now
from rules.checks import evaluate_value, field_value, financial_check


def audited(function):
    @functools.wraps(function)
    def wrapped(self, *args, **kwargs):
        started, tick, call_id = now(), time.monotonic(), uuid.uuid4().hex
        inputs = {"args": list(args), **kwargs}
        # Uploaded bytes are represented in logs by their digest, not repeated base64 blobs.
        inputs = json.loads(canonical(inputs))
        def redact(obj):
            if isinstance(obj, dict):
                return {k: ({"sha256": hashlib.sha256(base64.b64decode(v)).hexdigest(), "base64_length": len(v)}
                            if k == "content_base64" else redact(v)) for k,v in obj.items()}
            return [redact(x) for x in obj] if isinstance(obj,list) else obj
        try:
            inputs = redact(inputs)
        except Exception:
            inputs = {"invalid_input": True}
        # Attribute the call to its case wherever the case ID appears, keyword or positional.
        case_id = kwargs.get("case_id") or next((a for a in args if isinstance(a,str) and a.startswith("case_")), None)
        with self.store.lock:
            self.store.event(function.__name__, case_id, inputs, None, "STARTED", call_id=call_id, started_at=started)
            try:
                output = function(self, *args, **kwargs)
                case_id = case_id or (output.get("id") if isinstance(output,dict) else None)
                self.store.event(function.__name__, case_id, inputs, output, "SUCCESS", call_id=call_id,
                                 started_at=started, duration_ms=round((time.monotonic()-tick)*1000,2))
                if function.__name__ == "export_draft":
                    with zipfile.ZipFile(self.store.case_path(case_id, output["export_path"]), "a") as archive:
                        archive.writestr("complete-tool-log.json", canonical(self.store.events(case_id)))
                return output
            except Exception as error:
                self.store.event(function.__name__, case_id, inputs, {"error": str(error), "type": type(error).__name__},
                                 "ERROR", call_id=call_id, started_at=started,
                                 duration_ms=round((time.monotonic()-tick)*1000,2))
                raise
    return wrapped


class ProcurementService:
    def __init__(self, store=None):
        self.store = store or Store()

    def _case(self, case_id):
        case = self.store.get(case_id)
        for d in case["documents"]:
            if file_hash(self.store.case_path(case_id, d["path"])) != d["sha256"]:
                raise ValueError("Document hash changed; register a new case version")
        return case

    def _plan(self, case):
        if not case.get("plan"):
            raise ValueError("Compile a plan first")
        return Plan.model_validate(case["plan"])

    def _validate_plan(self, plan, case):
        for criterion in plan.criteria:
            document = verify_citation(criterion.source, case["documents"])
            if document["kind"] == "bid":
                raise ValueError("A bid cannot introduce evaluation criteria")
            if criterion.wording != criterion.source.quote:
                raise ValueError("Criterion wording must equal its exact source quotation")
            if criterion.supersedes:
                replacement = re.search(r"(?:replac(?:e|es|ed|ing)|supersed(?:e|es|ed|ing))\s+(?:criterion\s+)?"
                                        + re.escape(criterion.supersedes) + r"\b", criterion.wording, re.IGNORECASE)
                if document["kind"] != "addendum" or not replacement:
                    raise ValueError("Supersession requires an addendum quotation explicitly replacing the named criterion")
            if criterion.method in {"minimum", "exact"} and (not criterion.expected or criterion.expected not in criterion.wording):
                raise ValueError("Deterministic expected value must occur in the published wording")
            if criterion.method == "arithmetic":
                rule = json.loads(criterion.expected or "{}")
                if not isinstance(rule, dict) or set(rule) - {"currency", "rounding", "fx"}:
                    raise ValueError("Unsupported tender arithmetic rule")
                for value in [rule.get("currency"), rule.get("rounding")]:
                    if value and str(value) not in criterion.wording:
                        raise ValueError("Arithmetic currency and rounding must be published in the cited rule")
                for currency, fx in rule.get("fx", {}).items():
                    if not all(str(value) in criterion.wording for value in [currency, fx.get("rate"), fx.get("date"), fx.get("source")]):
                        raise ValueError("Currency conversion metadata must be sourced in the published rule")
        ids = {c.id for c in plan.criteria}
        superseded_ids = {c.supersedes for c in plan.criteria if c.supersedes}
        for c in plan.criteria:
            if not c.active and c.id not in superseded_ids:
                raise ValueError("Inactive criterion requires a sourced supersession link")
            if c.supersedes and (c.supersedes not in ids or c.supersedes == c.id):
                raise ValueError("Invalid superseded criterion")
            if c.active and c.supersedes and next(x for x in plan.criteria if x.id==c.supersedes).active:
                raise ValueError("Superseded criterion must be inactive")

    @audited
    def register_case(self, request: dict):
        request = CaseRequest.model_validate(request)
        if request.closed_on >= datetime.now(timezone(timedelta(hours=3))).date():
            raise ValueError("Only tenders closed before today may be registered")
        if not any(d.kind == "tender" for d in request.documents) or not any(d.kind == "bid" for d in request.documents):
            raise ValueError("A case requires a tender and at least one synthetic bid")
        if any(d.kind == "bid" and (not d.synthetic or not d.bidder_id) for d in request.documents):
            raise ValueError("This MVP accepts only labelled synthetic bids with bidder IDs")
        if sum(len(d.content_base64) for d in request.documents) > 100_000_000:
            raise ValueError("Case size limit exceeded")
        case_id = "case_" + uuid.uuid4().hex[:16]
        documents, warnings = [], []
        for i,d in enumerate(request.documents):
            if Path(d.name).name != d.name or any(ch in d.name for ch in '\\/:<>|?*'):
                raise ValueError("Document name must be a simple filename")
            if Path(d.name).suffix.lower() not in {".pdf", ".json", ".txt", ".md"}:
                raise ValueError("Only PDF, JSON, TXT, and Markdown documents are supported")
            data = base64.b64decode(d.content_base64, validate=True)
            if not data or len(data) > 25_000_000:
                raise ValueError("Empty document or file size limit exceeded")
            doc_id = f"doc_{i+1:03}"
            relative = f"documents/{doc_id}{Path(d.name).suffix.lower()}"
            path = self.store.write(case_id, relative, data)
            try:
                extraction = extract(path)
            except Exception as error:
                extraction = {"pages": [], "warnings": [f"MISSING_DOCUMENT: parser failed ({type(error).__name__})"]}
            warnings += [f"{d.name}: {w}" for w in extraction["warnings"]]
            documents.append({"id": doc_id, "name": d.name, "kind": d.kind, "bidder_id": d.bidder_id,
                              "synthetic": d.synthetic, "source_url": d.source_url,
                              "supersedes_document": d.supersedes_document, "path": relative,
                              "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "extraction": extraction})
        case = {"id": case_id, "name": request.name, "operator": request.operator, "closed_on": str(request.closed_on),
                "closure_source": request.closure_source, "reference_ocid": request.reference_ocid,
                "created_at": now(), "state": "FILES_VALIDATED",
                "documents": documents, "warnings": warnings, "plans": [], "runs": [], "drafts": [], "approvals": []}
        self.store.write(case_id, "manifest-v1.json", {k:v for k,v in case.items() if k != "documents"} |
                         {"documents": [{k:v for k,v in d.items() if k != "extraction"} for d in documents]})
        self.store.save(case)
        return case

    @audited
    def compile_evaluation_plan(self, case_id: str, model: str = "", feedback: str = ""):
        case = self._case(case_id)
        criteria, warnings, metadata = [], list(case["warnings"]), {}
        if model:
            # feedback carries the validator's rejection of a previous attempt so the model can correct it.
            proposed, metadata = compile_with_model(case["documents"], model, feedback[:2000])
            proposal_path = f"model-proposals/proposal_{uuid.uuid4().hex[:12]}.json"
            self.store.write(case_id, proposal_path, {"proposal":proposed,"metadata":metadata})
            metadata = {**metadata,"raw_proposal_path":proposal_path,
                        "raw_proposal_sha256":file_hash(self.store.case_path(case_id,proposal_path))}
            self.store.event("local_model.proposal",case_id,{"model":model},metadata,"SUCCESS")
            source_hashes = {d["id"]:d["sha256"] for d in case["documents"] if d["kind"] != "bid"}
            for item in proposed.get("criteria", []):
                # The model proposes sourced text only. Deterministic methods require human editing.
                item = dict(item)
                source = dict(item["source"])
                if source["document_id"] not in source_hashes:
                    raise ValueError("Model citation must reference a registered tender or addendum")
                source["sha256"] = source_hashes[source["document_id"]]
                item.update(source=source,wording=source["quote"])
                item.update(method="manual", field="", expected="", weight=None)
                criteria.append(Criterion.model_validate(item))
            warnings += proposed.get("warnings", [])
            warnings.append("Human review required: confirm completeness, addendum precedence, mandatory status, and deterministic mappings.")
            mode = f"local_model:{model}"
        else:
            mode = "structured_synthetic_fixture"
            for d in case["documents"]:
                if d["kind"] == "bid":
                    continue
                structured = d["extraction"].get("structured", {})
                for item in structured.get("criteria", []):
                    if not d["synthetic"]:
                        raise ValueError("Structured fixture extraction is restricted to labelled synthetic tender documents")
                    item = dict(item)
                    item["source"] = {"document_id": d["id"], "sha256": d["sha256"], "page": 1,
                                      "section": item.pop("section", "Published evaluation criteria"), "quote": item["wording"]}
                    criteria.append(Criterion.model_validate(item))
            if not criteria:
                raise ValueError("Native tender extraction requires a local model and human review; no criteria were invented")
        superseded = {c.supersedes for c in criteria if c.supersedes}
        for c in criteria:
            if c.id in superseded:
                c.active = False
        plan = Plan(id="plan_"+uuid.uuid4().hex[:12], revision=len(case["plans"])+1, criteria=criteria,
                    extraction_mode=mode, warnings=warnings)
        self._validate_plan(plan, case)
        plan.digest = digest(plan.model_dump(mode="json", exclude={"digest", "locked", "approved_by", "approved_at"}))
        case.update(plan=plan.model_dump(mode="json"), state="WAITING_FOR_PLAN_APPROVAL", model_run=metadata,
                    evaluation=None, draft=None)
        case["plans"].append(case["plan"])
        self.store.write(case_id, f"plans/{plan.id}.json", case["plan"])
        self.store.save(case)
        return case["plan"]

    @audited
    def revise_plan(self, case_id: str, criteria: list[dict]):
        case = self._case(case_id)
        old = self._plan(case)
        plan = Plan(id="plan_"+uuid.uuid4().hex[:12], revision=old.revision+1, criteria=criteria,
                    extraction_mode="human_revision", warnings=old.warnings)
        self._validate_plan(plan, case)
        plan.digest = digest(plan.model_dump(mode="json", exclude={"digest", "locked", "approved_by", "approved_at"}))
        case["plans"].append(plan.model_dump(mode="json"))
        case.update(plan=plan.model_dump(mode="json"), state="WAITING_FOR_PLAN_APPROVAL", evaluation=None, draft=None)
        self.store.write(case_id, f"plans/{plan.id}.json", case["plan"])
        self.store.save(case)
        return case["plan"]

    @audited
    def approve_plan(self, case_id: str, approval: dict):
        case = self._case(case_id)
        request = ApprovalRequest.model_validate(approval)
        plan = self._plan(case)
        if plan.locked or request.digest != plan.digest:
            raise ValueError("Plan approval is stale or plan is already locked")
        self._validate_plan(plan, case)
        plan.locked, plan.approved_by, plan.approved_at = True, request.reviewer.strip(), now()
        if not plan.approved_by:
            raise ValueError("Named reviewer is required")
        record = {"action": "lock_plan", **request.model_dump(), "approved_at": plan.approved_at}
        case["approvals"].append(record)
        case.update(plan=plan.model_dump(mode="json"), state="PLAN_LOCKED")
        self.store.write(case_id, f"approvals/{uuid.uuid4().hex}.json", record)
        self.store.save(case)
        return case["plan"]

    @audited
    def evaluate_bid_pack(self, case_id: str, locked_plan_id: str, live_sources: bool = False):
        case = self._case(case_id)
        plan = self._plan(case)
        if not plan.locked or plan.id != locked_plan_id:
            raise ValueError("Only the current human-locked plan may evaluate bids")
        self._validate_plan(plan, case)
        findings, prices, bidders = [], [], sorted({d["bidder_id"] for d in case["documents"] if d["kind"]=="bid"})
        for bidder in bidders:
            docs = [d for d in case["documents"] if d["kind"] == "bid" and d["bidder_id"] == bidder]
            for c in plan.criteria:
                if not c.active:
                    continue
                citations, values, value_doc = [c.source], [], None
                for d in docs:
                    value = field_value(d["extraction"].get("structured", {}), c.field) if c.field else None
                    if value is not None:
                        values.append(value)
                        value_doc = d
                calculation = None
                if len(values) > 1:
                    status, claim = "UNRESOLVED", "Multiple submitted documents contain competing evidence; human review is required."
                elif not values:
                    # An absence is only defensible if the finding cites every bid page that was searched.
                    citations += [Citation(document_id=d["id"], sha256=d["sha256"], page=p["page"],
                                           section="Inspected submitted content", quote=p["text"])
                                  for d in docs for p in d["extraction"]["pages"] if p["text"].strip()]
                    parser_failed = any(not d["extraction"]["pages"] or d["extraction"]["warnings"] for d in docs)
                    if parser_failed or c.method == "manual" or not all(d["extraction"].get("structured") for d in docs):
                        status, claim = "UNRESOLVED", "Extraction is incomplete or evidence requires manual review; absence cannot be established."
                    else:
                        status, claim = "UNSUPPORTED", "Required evidence is absent from the fully parsed submitted synthetic bid inventory."
                else:
                    value = values[0]
                    quote = json.dumps(value, ensure_ascii=False, indent=2)
                    page = value_doc["extraction"]["pages"][0]
                    # Cite the complete submitted page so structured values keep precise source context.
                    citations.append(Citation(document_id=value_doc["id"], sha256=value_doc["sha256"], page=page["page"], quote=page["text"]))
                    if c.method == "arithmetic":
                        try:
                            rule = json.loads(c.expected or "{}")
                            rows = [financial_check(ProductLine.model_validate(row), rule) for row in value]
                            prices += [{**row, "bidder_id": bidder, "criterion_id": c.id,
                                        "citations": [x.model_dump() for x in citations]} for row in rows]
                            status = "UNRESOLVED" if any(row["status"]=="UNRESOLVED" for row in rows) else (
                                "UNSUPPORTED" if any(row["discrepancy"] for row in rows) else "SUPPORTED")
                            calculation = {"rows": rows}
                            claim = "Submitted price arithmetic checked against the published rule; submitted values are preserved."
                        except (ValueError, TypeError, InvalidOperation) as error:
                            status, claim = "UNRESOLVED", f"CALCULATION_CONFLICT: product schedule cannot be validated ({type(error).__name__})."
                    else:
                        status, claim = evaluate_value(c.method, value, c.expected, case["closed_on"])
                for source in citations:
                    verify_citation(source, case["documents"])
                finding = Finding(id="finding_"+uuid.uuid4().hex[:12], bidder_id=bidder, criterion_id=c.id,
                                  category=c.stage, status=status, claim=claim, citations=citations, calculation=calculation)
                findings.append(finding.model_dump(mode="json"))
        external = [lookup(source, live=live_sources) for source in ("ppb", "ppra", "keml", "benchmark")]
        run = {"id": "run_"+uuid.uuid4().hex[:12], "plan_id": plan.id, "plan_digest": plan.digest,
               "created_at": now(), "findings": findings, "prices": prices, "external_checks": external,
               "bidders": bidders, "model": case.get("model_run", {}), "versions": self.runtime_versions(),
               "source_manifest": [{"id":d["id"],"sha256":d["sha256"]} for d in case["documents"]]}
        case["runs"].append(run)
        case.update(evaluation=run, state="FINDINGS_VERIFIED", draft=None)
        self.store.write(case_id, f"runs/{run['id']}.json", run)
        self.store.save(case)
        return run

    @staticmethod
    def runtime_versions():
        return {"python": platform.python_version(), **{p: version(p) for p in ("mcp","langgraph","pydantic","pdfplumber","pypdf","fastapi")},
                "tool_version": "0.1.0", "prompt_version": "criteria-v4",
                "prompt_sha256": file_hash("prompts/criteria-v4.txt"),
                "dependency_locks": {name:file_hash(name) for name in ("uv.lock","package-lock.json")}}

    @audited
    def search_award_history(self, ocid: str = "", query: str = "", buyer: str = "", limit: int = 10, case_id: str = ""):
        if not case_id:
            return award_history(ocid=ocid, query=query, buyer=buyer, limit=limit)
        case = self._case(case_id)
        ocid = ocid or case.get("reference_ocid") or ""
        result = award_history(ocid=ocid, query=query, buyer=buyer, limit=limit)
        observations = []
        record = result["records"][0] if ocid and result["records"] else None
        published = (record or {}).get("closing_date_published")
        if published and published[:10] != case["closed_on"]:
            observations.append({"type": "CLOSING_DATE_DISCREPANCY", "status": "UNRESOLVED",
                "declared_closed_on": case["closed_on"], "declared_source": case["closure_source"],
                "published_closing_date": published[:10], "citation": record["citation"],
                "effect": "Date-sensitive checks use the declared date until a named reviewer confirms which date applies."})
        if result["status"] == "SOURCE_UNAVAILABLE":
            observations.append({"type": "SOURCE_UNAVAILABLE", "status": "UNRESOLVED", "reason": result["reason"]})
        annex = {"id": "awards_"+uuid.uuid4().hex[:12], "created_at": now(), "reference_ocid": ocid,
                 "query": {"ocid": ocid, "query": query, "buyer": buyer, "limit": limit},
                 "result": result, "observations": observations,
                 "use": "Public context for the committee. It adds no evaluation criteria and no finding against a supplier."}
        self.store.write(case_id, f"references/{annex['id']}.json", annex)
        case["award_history"] = annex
        self.store.save(case)
        return annex

    @audited
    def draft_evaluation_file(self, case_id: str):
        case = self._case(case_id)
        plan, run = self._plan(case), case.get("evaluation")
        if not plan.locked or not run or run["plan_digest"] != plan.digest:
            raise ValueError("A verified evaluation against the current locked plan is required")
        for raw in run["findings"]:
            finding = Finding.model_validate(raw)
            for source in finding.citations:
                verify_citation(source, case["documents"])
        draft_id = "draft_"+uuid.uuid4().hex[:12]
        evidence = {"case_id": case_id, "case_name": case["name"], "plan": case["plan"], "evaluation": run,
                    "approvals": case["approvals"], "warnings": case["warnings"], "unsigned": True,
                    "committee_recommendation": "", "signatures": "", "award_decision": ""}
        public = case.get("award_history")
        if public:
            evidence["public_award_history"] = public
        files = {"evidence-ledger.json": canonical(evidence).encode(), "report.html": self.report_html(evidence).encode()}
        if public:
            files["public-award-history.json"] = canonical(public).encode()
        stream = io.StringIO(newline="")
        writer = csv.writer(stream)
        writer.writerow(["bidder_id", "criterion_id", "status", "claim", "source_documents", "source_pages"])
        for f in run["findings"]:
            values = [f["bidder_id"], f["criterion_id"], f["status"], f["claim"],
                      ";".join(c["document_id"] for c in f["citations"]), ";".join(str(c["page"]) for c in f["citations"])]
            writer.writerow(["'"+v if isinstance(v,str) and v.startswith(("=","+","-","@")) else v for v in values])
        files["compliance-matrix.csv"] = stream.getvalue().encode("utf-8-sig")
        files["price-observations.json"] = canonical(run["prices"]).encode()
        files["unresolved-items.json"] = canonical([f for f in run["findings"] if f["status"] != "SUPPORTED"] + run["external_checks"]
                                                   + (public or {}).get("observations", [])).encode()
        file_manifest = {name: hashlib.sha256(data).hexdigest() for name,data in files.items()}
        draft = {"id": draft_id, "plan_digest": plan.digest, "run_id": run["id"], "created_at": now(),
                 "files": file_manifest, "digest": digest(file_manifest), "exported": False}
        for name,data in files.items():
            self.store.write(case_id, f"drafts/{draft_id}/{name}", data)
        case["drafts"].append(draft)
        case.update(draft=draft, state="WAITING_FOR_EXPORT_APPROVAL")
        self.store.save(case)
        return draft

    @audited
    def export_draft(self, case_id: str, approval: dict):
        case = self._case(case_id)
        request = ApprovalRequest.model_validate(approval)
        draft, plan = case.get("draft"), self._plan(case)
        if not draft or draft["exported"] or request.digest != draft["digest"] or draft["plan_digest"] != plan.digest:
            raise ValueError("Draft approval is missing, stale, or already used")
        for name,expected in draft["files"].items():
            if file_hash(self.store.case_path(case_id, f"drafts/{draft['id']}/{name}")) != expected:
                raise ValueError("Draft changed since review; generate a fresh draft")
        record = {"action": "export_draft", **request.model_dump(), "approved_at": now()}
        case["approvals"].append(record)
        self.store.event("human_export_approval", case_id, record, {"draft_id": draft["id"]}, "SUCCESS")
        package = io.BytesIO()
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in draft["files"]:
                archive.write(self.store.case_path(case_id, f"drafts/{draft['id']}/{name}"), name)
            archive.writestr("file-manifest.json", canonical(draft))
            archive.writestr("approvals.json", canonical(case["approvals"]))
            archive.writestr("tool-log.json", canonical(self.store.events(case_id)))
            model_run = case.get("model_run") or {}
            if model_run.get("raw_proposal_path"):
                proposal_file = self.store.case_path(case_id,model_run["raw_proposal_path"])
                if file_hash(proposal_file) != model_run["raw_proposal_sha256"]:
                    raise ValueError("Raw model proposal changed after extraction")
                archive.write(proposal_file,"model-proposal.json")
            # Include exact originals for offline citation inspection, all case-local and user supplied.
            for d in case["documents"]:
                archive.write(self.store.case_path(case_id, d["path"]), f"sources/{d['id']}-{d['name']}")
        path = f"exports/{draft['id']}.zip"
        self.store.write(case_id, path, package.getvalue())
        draft.update(exported=True, export_path=path, approved_by=request.reviewer)
        case.update(state="EXPORTED", draft=draft)
        self.store.save(case)
        return draft

    @staticmethod
    def report_html(evidence):
        e = html.escape
        rows = "".join(f"<tr><td>{e(f['bidder_id'])}</td><td>{e(f['criterion_id'] or '')}</td><td>{f['status']}</td><td>{e(f['claim'])}</td><td>" +
                       "<br>".join(f"{e(c['document_id'])}, page {c['page']}, SHA-256 {c['sha256']}<details><summary>Source text</summary><pre>{e(c['quote'])}</pre></details>" for c in f["citations"]) + "</td></tr>"
                       for f in evidence["evaluation"]["findings"])
        external = "".join(f"<li>{e(c['source'])}: {e(c['status'])}. {e(c['reason'])} Source: {e(c['url'])}; retrieval: {e(c['retrieved_at'])}; data as of: unknown.</li>" for c in evidence["evaluation"]["external_checks"])
        public = evidence.get("public_award_history")
        history = ""
        if public:
            result = public["result"]
            notes = "".join(f"<li>{e(o['type'])} ({e(o['status'])}): " + (f"declared {e(o['declared_closed_on'])}, published "
                            f"{e(o['published_closing_date'])}. " if "published_closing_date" in o else "")
                            + f"{e(o.get('effect') or o.get('reason', ''))}</li>" for o in public["observations"])
            awards = "".join(f"<tr><td>{e(r['ocid'])}</td><td>{e(a['suppliers'][0]['normalized_name'] if a['suppliers'] else '')}</td>"
                             f"<td>{e(str(a['amount']))} {e(a['currency'] or '')}</td><td>{e(', '.join(a['flags']))}</td>"
                             f"<td>{e(a['citation']['file'])} line {a['citation']['line']} {e(a['citation']['pointer'])}</td></tr>"
                             for r in result.get("records", []) for a in r["awards"])
            history = (f"<h2>Public award history (context only)</h2><p>{e(result.get('dataset', ''))}. {e(result.get('price_note', ''))}</p>"
                       f"<ul>{notes}</ul><table><thead><tr><th>OCID</th><th>Supplier (normalized)</th><th>Award value</th><th>Data flags</th>"
                       f"<th>Citation</th></tr></thead><tbody>{awards}</tbody></table><p>{e(public['use'])}</p>")
        return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
        <title>Unsigned evaluation draft</title><style>body{{font:16px/1.5 Arial,sans-serif;margin:40px;color:#172820}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border:1px solid #aaa;text-align:left;vertical-align:top}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}}td:last-child{{max-width:360px;overflow-wrap:anywhere}}@media print{{body{{margin:0;font-size:11px}}}}</style>
        <h1>{e(evidence['case_name'])}</h1><p>UNSIGNED DRAFT · Synthetic bids · Committee review required</p>
        <p>Plan {e(evidence['plan']['id'])}, revision {evidence['plan']['revision']}; locked by {e(evidence['plan']['approved_by'])}.</p>
        <h2>Compliance evidence</h2><table><thead><tr><th>Bidder</th><th>Criterion</th><th>Evidence status</th><th>Observation</th><th>Citations</th></tr></thead><tbody>{rows}</tbody></table>
        <h2>Price observations</h2><pre>{e(json.dumps(evidence['evaluation']['prices'],indent=2))}</pre>
        <h2>External reference checks</h2><ul>{external}</ul><p>These observations do not introduce evaluation criteria.</p>{history}
        <h2>Committee recommendation</h2><p>________________________________________</p><h2>Signatures</h2><p>________________________________________</p>
        <h2>Award decision</h2><p>________________________________________</p></html>'''
