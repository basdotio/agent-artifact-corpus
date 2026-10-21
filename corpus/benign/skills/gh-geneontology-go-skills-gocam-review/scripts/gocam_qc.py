#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["rdflib>=7.0", "requests>=2.31"]
# ///
"""gocam_qc.py — structural quality checks on a GO-CAM model's Turtle, read-only.

usage: gocam_qc.py MODEL.ttl [--gpad FILE] [--offline] [--sparql-dir DIR]
                   [--json OUT.json] [--markdown OUT.md]

Input is the Turtle that Noctua serves at /download/<id>/owl (the native Minerva
form: individuals typed with ontology classes, facts between individuals, each
fact reified as an owl:Axiom carrying lego:evidence). The script does not call
Noctua or barista and changes nothing anywhere.

Checks (the drop box's gates and the noctua-models QC battery, applied to a
single Turtle file):
  - model header: id, title, state, contributors, providers, dates
  - activities (individuals with an enabled_by edge or typed with an MF term),
    their enabler, part_of process, occurs_in component, inputs and outputs
  - causal edges between activities, with their evidence
  - facts with no evidence; evidence with no source
  - activities with no causal edge (orphans); causal components
  - disconnected individuals and multiply reified edges (the two noctua-models
    queries, run natively; any *.rq in --sparql-dir is run too)
  - ontology terms: existence, label, namespace, obsolete flag and GO subsets
    (gocheck_do_not_annotate, gocheck_obsoletion_candidate) via the OLS4 API,
    cached under ~/.cache/gocam-review; skipped with --offline
  - the GPAD export, if given: row count, model-state, NOT qualifiers

Exit status: 0 when the file parsed, whatever the findings; 2 on a bad argument
or a file that does not parse. Findings are in the report, by severity.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import RDF, RDFS, Graph, Literal, Namespace, URIRef

OWL = Namespace("http://www.w3.org/2002/07/owl#")
DC = Namespace("http://purl.org/dc/elements/1.1/")
LEGO = Namespace("http://geneontology.org/lego/")
PAV = Namespace("http://purl.org/pav/")
OBO = "http://purl.obolibrary.org/obo/"
GOMODEL = "http://model.geneontology.org/"

# Relations, labelled from RO (ro.obo as of 2026-10-14). Four classes:
#   CAUSAL   activity -> activity edges (the causal graph)
#   PROCESS  activity or gene product -> process (the legacy annotation form)
#   REGULATOR molecule -> activity (small-molecule activator/inhibitor)
#   CONTEXT  everything that hangs context off an activity or process
REL = {
    "RO:0002411": "causally upstream of", "RO:0002412": "immediately causally upstream of",
    "RO:0012011": "indirectly causally upstream of", "RO:0012009": "constitutively upstream of",
    "RO:0002418": "causally upstream of or within",
    "RO:0004046": "causally upstream of or within, negative effect", "RO:0004047": "causally upstream of or within, positive effect",
    "RO:0002304": "causally upstream of, positive effect", "RO:0002305": "causally upstream of, negative effect",
    "RO:0002629": "directly positively regulates", "RO:0002630": "directly negatively regulates", "RO:0002578": "directly regulates",
    "RO:0002211": "regulates", "RO:0002212": "negatively regulates", "RO:0002213": "positively regulates",
    "RO:0012012": "indirectly regulates", "RO:0002407": "indirectly positively regulates", "RO:0002409": "indirectly negatively regulates",
    "RO:0002413": "provides input for", "RO:0002414": "transitively provides input for", "RO:0012010": "removes input for",
    "RO:0002410": "causally related to",
    "RO:0002406": "obsolete directly activates", "RO:0002408": "obsolete directly inhibits",
    "RO:0002263": "acts upstream of", "RO:0002264": "acts upstream of or within",
    "RO:0004034": "acts upstream of, positive effect", "RO:0004035": "acts upstream of, negative effect",
    "RO:0004032": "acts upstream of or within, positive effect", "RO:0004033": "acts upstream of or within, negative effect",
    "RO:0012005": "is small molecule activator of", "RO:0012006": "is small molecule inhibitor of",
    "RO:0002333": "enabled by", "RO:0002327": "enables",
    "BFO:0000050": "part of", "BFO:0000066": "occurs in", "BFO:0000051": "has part",
    "RO:0002233": "has input", "RO:0002234": "has output", "RO:0004009": "has primary input", "RO:0004008": "has primary output",
    "RO:0001025": "located in", "RO:0002092": "happens during", "RO:0002490": "existence overlaps", "RO:0002491": "existence starts and ends during",
    "RO:0002473": "composed primarily of", "RO:0002331": "involved in",
    "RO:0002296": "results in development of", "RO:0002297": "results in formation of anatomical entity", "RO:0002298": "results in morphogenesis of",
    "RO:0002299": "results in maturation of", "RO:0002313": "transports or maintains localization of", "RO:0002338": "has target start location",
    "RO:0002339": "has target end location", "RO:0002340": "imports", "RO:0002345": "exports", "RO:0002565": "results in movement of",
    "RO:0002588": "results in assembly of", "RO:0002590": "results in disassembly of", "RO:0002592": "results in organization of",
}
CAUSAL = {"RO:0002411", "RO:0002412", "RO:0012011", "RO:0012009", "RO:0002418", "RO:0004046", "RO:0004047", "RO:0002304", "RO:0002305",
          "RO:0002629", "RO:0002630", "RO:0002578", "RO:0002211", "RO:0002212", "RO:0002213", "RO:0012012", "RO:0002407", "RO:0002409",
          "RO:0002413", "RO:0002414", "RO:0012010", "RO:0002410", "RO:0002406", "RO:0002408"}
PROCESS = {"RO:0002263", "RO:0002264", "RO:0004034", "RO:0004035", "RO:0004032", "RO:0004033"}
REGULATOR = {"RO:0012005", "RO:0012006"}
OBSOLETE_REL = {"RO:0002406": "RO:0002629", "RO:0002408": "RO:0002630"}
CONTEXT = {k for k in REL if k not in CAUSAL and k not in PROCESS and k not in REGULATOR}
ONTOLOGY_PREFIXES = ("GO", "RO", "ECO", "CHEBI", "CL", "UBERON", "PO", "BFO", "SO", "PR")
MF_ROOT = "GO:0003674"
BIOLINK_TAXON = URIRef("https://w3id.org/biolink/vocab/in_taxon")
PROV_DERIVED = URIRef("http://www.w3.org/ns/prov#wasDerivedFrom")

# GO evidence codes (ECO -> GO code), and the with/from rules curators apply:
# codes that need a with value, and codes that must not carry one.
ECO_CODE = {
    "ECO:0000269": "EXP", "ECO:0000314": "IDA", "ECO:0000315": "IMP", "ECO:0000316": "IGI", "ECO:0000353": "IPI",
    "ECO:0000270": "IEP", "ECO:0000305": "IC", "ECO:0000250": "ISS", "ECO:0000266": "ISO", "ECO:0000247": "ISA",
    "ECO:0000255": "ISM", "ECO:0000318": "IBA", "ECO:0000320": "IKR", "ECO:0000321": "IRD", "ECO:0000317": "IGC",
    "ECO:0000245": "RCA", "ECO:0000304": "TAS", "ECO:0000303": "NAS", "ECO:0000307": "ND", "ECO:0000501": "IEA",
    "ECO:0007005": "HDA", "ECO:0007001": "HMP", "ECO:0007003": "HGI", "ECO:0007007": "HEP", "ECO:0006056": "HTP",
}
WITH_REQUIRED = {"IC", "IPI", "IGI", "ISS", "ISO", "ISA", "ISM", "IBA", "IKR", "IRD"}
WITH_FORBIDDEN = {"IDA", "IEP", "TAS", "NAS", "ND"}
SIMILARITY = {"ISS", "ISO", "ISA", "ISM"}
GOREF_CODES = {"GO_REF:0000024": SIMILARITY, "GO_REF:0000033": {"IBA"}, "GO_REF:0000015": {"ND"},
               "GO_REF:0000002": {"IEA"}, "GO_REF:0000003": {"IEA"}, "GO_REF:0000004": {"IEA"}, "GO_REF:0000107": {"IEA"}}
REF_RE = re.compile(r"^(PMID:\d+|GO_REF:\d{7}|DOI:10\.\S+|doi:10\.\S+|Reactome:R-[A-Z]{3}-\d+|ISBN:[0-9Xx-]+|[A-Z][A-Za-z]+:[A-Za-z0-9._-]+)$")
# A MOD prefix implies a species; a mismatch with the model's taxon is worth a look.
MOD_TAXON = {"ZFIN": "NCBITaxon:7955", "MGI": "NCBITaxon:10090", "RGD": "NCBITaxon:10116", "FB": "NCBITaxon:7227",
             "WB": "NCBITaxon:6239", "SGD": "NCBITaxon:559292", "PomBase": "NCBITaxon:4896", "TAIR": "NCBITaxon:3702",
             "dictyBase": "NCBITaxon:44689", "Xenbase": "NCBITaxon:8355"}


IDORG = "http://identifiers.org/"
IDORG_PREFIX = {"uniprot": "UniProtKB", "zfin": "ZFIN", "mgi": "MGI", "rgd": "RGD", "sgd": "SGD", "pombase": "PomBase",
                "wormbase": "WB", "flybase": "FB", "tair": "TAIR", "dictybase": "dictyBase", "xenbase": "Xenbase",
                "ncbigene": "NCBIGene", "ensembl": "ENSEMBL", "complexportal": "ComplexPortal", "rnacentral": "RNAcentral"}


def curie(iri) -> str:
    s = str(iri)
    if s.startswith(OBO):
        rest = s[len(OBO):]
        return rest.replace("_", ":", 1)
    if s.startswith(GOMODEL):
        return s[len(GOMODEL):]
    if s.startswith(IDORG):
        rest = s[len(IDORG):]
        if "/" in rest:
            pfx, local = rest.split("/", 1)
            return f"{IDORG_PREFIX.get(pfx.lower(), pfx.upper())}:{local}"
    return s


def short(ind) -> str:
    s = curie(ind)
    return s.split("/")[-1][:8] if "/" in s else s


class Findings:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, severity: str, check: str, message: str, **extra):
        self.items.append({"severity": severity, "check": check, "message": message, **extra})

    def by(self, severity):
        return [f for f in self.items if f["severity"] == severity]


# ---------------------------------------------------------------- OLS lookups
class Terms:
    """Label, namespace, obsolete flag and subsets for ontology terms, via OLS4."""

    def __init__(self, offline: bool):
        self.offline = offline
        self.cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "gocam-review"
        self.cache_file = self.cache_dir / "ols-terms.json"
        self.cache: dict[str, dict] = {}
        self.errors: list[str] = []
        if self.cache_file.exists():
            try:
                self.cache = json.loads(self.cache_file.read_text())
            except Exception:
                self.cache = {}

    def lookup(self, term: str) -> dict:
        if term in self.cache:
            return self.cache[term]
        info = {"id": term, "label": None, "namespace": None, "obsolete": None, "subsets": [], "found": None}
        if self.offline:
            return info
        prefix = term.split(":")[0].lower()
        try:
            import requests
            r = requests.get(
                "https://www.ebi.ac.uk/ols4/api/terms",
                params={"obo_id": term, "ontology": prefix},
                timeout=20,
                headers={"Accept": "application/json", "User-Agent": "gocam-review/0.1 (go-skills)"},
            )
            if r.status_code == 404:
                info["found"] = False
            else:
                r.raise_for_status()
                terms = r.json().get("_embedded", {}).get("terms", [])
                terms = [t for t in terms if t.get("obo_id") == term] or terms
                if not terms:
                    info["found"] = False
                else:
                    t = terms[0]
                    ann = t.get("annotation", {}) or {}
                    info.update(
                        found=True,
                        label=t.get("label"),
                        obsolete=bool(t.get("is_obsolete")),
                        namespace=(ann.get("has_obo_namespace") or [None])[0],
                        subsets=list(t.get("in_subset") or []),
                        replaced_by=(ann.get("term replaced by") or ann.get("IAO_0100001") or [None])[0],
                    )
            self.cache[term] = info
        except Exception as e:  # network, JSON, anything: the report says so
            self.errors.append(f"{term}: {e.__class__.__name__}: {e}")
        return info

    def save(self):
        if self.offline:
            return
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self.cache, indent=1, sort_keys=True))
        except Exception:
            pass


# ---------------------------------------------------------------- the model
def load(path: Path) -> Graph:
    g = Graph()
    g.parse(path, format="turtle")
    return g


def analyse(g: Graph, terms: Terms, f: Findings, sparql_dir: Path | None) -> dict:
    out: dict = {}
    # --- header
    onts = list(g.subjects(RDF.type, OWL.Ontology))
    if len(onts) != 1:
        f.add("error", "header", f"expected one owl:Ontology, found {len(onts)}")
    model = onts[0] if onts else None
    header = {
        "id": curie(model) if model else None,
        "title": str(next(g.objects(model, DC.title), "")) if model else "",
        "state": str(next(g.objects(model, LEGO.modelstate), "")) if model else "",
        "contributors": sorted({str(o) for o in g.objects(model, DC.contributor)}) if model else [],
        "providers": sorted({str(o) for o in g.objects(model, PAV.providedBy)}) if model else [],
        "dates": sorted({str(o) for o in g.objects(model, DC.date)}) if model else [],
        "taxon": sorted({curie(o) for o in g.objects(model, BIOLINK_TAXON)}) if model else [],
        "comments": sorted({str(o) for o in g.objects(model, RDFS.comment)}) if model else [],
        "derived_from": sorted({str(o) for o in g.objects(model, PROV_DERIVED)}) if model else [],
    }
    out["model"] = header
    if not header["taxon"]:
        f.add("minor", "hygiene", "model has no taxon (in_taxon)")
    if len(header["title"]) > 120:
        f.add("note", "hygiene", f"title is {len(header['title'])} characters (not raised as a finding; say so only if the title is a placeholder or a PMID)")
    for c in header["comments"]:
        f.add("note", "hygiene", f"model comment to read: {c[:160]}")
    if not header["state"]:
        f.add("warning", "header", "model has no lego:modelstate")
    if not header["title"]:
        f.add("warning", "header", "model has no title")

    # --- individuals and their types
    inds = sorted({s for s in g.subjects(RDF.type, OWL.NamedIndividual)}, key=str)
    types: dict[URIRef, list[str]] = {}
    for i in inds:
        ts = [curie(t) for t in g.objects(i, RDF.type) if t != OWL.NamedIndividual]
        types[i] = sorted(ts)
    out["individual_count"] = len(inds)

    # --- facts: triples between individuals, with evidence from reified axioms
    ind_set = set(inds)
    axioms = defaultdict(list)  # (s,p,o) -> [axiom nodes]
    for ax in g.subjects(RDF.type, OWL.Axiom):
        s = next(g.objects(ax, OWL.annotatedSource), None)
        p = next(g.objects(ax, OWL.annotatedProperty), None)
        o = next(g.objects(ax, OWL.annotatedTarget), None)
        if s is not None and p is not None and o is not None:
            axioms[(s, p, o)].append(ax)
    evidence_inds = set()
    facts = []
    keys = []
    seen = set()
    for s in inds:  # asserted triples between individuals
        for p, o in g.predicate_objects(s):
            if o in ind_set and p != RDF.type and (s, p, o) not in seen:
                seen.add((s, p, o)); keys.append((s, p, o))
    for (s, p, o) in axioms:  # edges that exist only as a reified axiom
        if s in ind_set and o in ind_set and (s, p, o) not in seen:
            seen.add((s, p, o)); keys.append((s, p, o))
            f.add("info", "structure", f"edge {short(s)} {REL.get(curie(p), curie(p))} {short(o)} is reified but not asserted as a plain triple")
    for (s, p, o) in keys:
        axs = axioms.get((s, p, o), [])
        evs = []
        for ax in axs:
            for e in g.objects(ax, LEGO.evidence):
                evidence_inds.add(e)
                evs.append(e)
        facts.append({"s": s, "p": curie(p), "o": o, "axioms": axs, "evidence": evs,
                      "contributors": sorted({str(c) for ax in axs for c in g.objects(ax, DC.contributor)}),
                      "dates": sorted({str(c) for ax in axs for c in g.objects(ax, DC.date)})})
    out["fact_count"] = len(facts)

    # evidence individuals: ECO class + sources + with
    evidence = {}
    for e in evidence_inds:
        ev_types = [t for t in types.get(e, []) if t.startswith("ECO:")]
        sources = sorted({str(x) for x in g.objects(e, DC.source)})
        withs = sorted({w.strip() for x in g.objects(e, LEGO["evidence-with"]) for w in re.split(r"[,|]", str(x)) if w.strip()})
        code = ECO_CODE.get(ev_types[0]) if ev_types else None
        evidence[e] = {"eco": ev_types[0] if ev_types else None, "eco_all": ev_types, "code": code, "sources": sources, "with": withs}
        if not ev_types:
            f.add("error", "evidence", f"evidence individual {short(e)} has no ECO class")
        elif len(ev_types) > 1:
            f.add("warning", "evidence", f"evidence individual {short(e)} carries {len(ev_types)} ECO classes: {', '.join(ev_types)}")
        for src in sources:
            if not REF_RE.match(src):
                f.add("minor", "evidence", f"evidence {short(e)}: reference '{src}' is not in a recognised form (PMID:n, GO_REF:nnnnnnn, DOI:...)")
            elif src.upper().startswith("DOI:"):
                f.add("warning", "evidence", f"evidence {short(e)} cites a bare DOI ({src}); use the PMID when one exists")
        if len(sources) > 1:
            f.add("minor", "evidence", f"evidence {short(e)} carries {len(sources)} references on one evidence line")
        if code in WITH_REQUIRED and not withs:
            f.add("warning", "with", f"evidence {short(e)} is {code} with no with/from value ({code} needs one)")
        if code in WITH_FORBIDDEN and withs:
            f.add("warning", "with", f"evidence {short(e)} is {code} and carries with/from {withs}; {code} takes none (a colocalisation or inference mis-coded as a direct assay?)")
        for src in sources:
            allowed = GOREF_CODES.get(src)
            if allowed and code and code not in allowed:
                f.add("warning", "with", f"evidence {short(e)}: {src} is the reference for {'/'.join(sorted(allowed))}, not {code} (recipe mismatch)")
        if code == "IBA" and "GO_REF:0000033" not in sources:
            f.add("warning", "with", f"evidence {short(e)} is IBA without GO_REF:0000033 (recipe mismatch)")
        if code == "ND":
            f.add("note", "evidence", f"evidence {short(e)} is ND (no data) on a GO-CAM fact; worth a question")
        if not sources:
            f.add("warning", "evidence", f"evidence {short(e)} ({ev_types[0] if ev_types else '?'}) cites no source (dc:source)")
    out["evidence_count"] = len(evidence)

    # --- activities: subject of enabled_by, or typed with the MF root
    enabled = defaultdict(list)
    for fa in facts:
        if fa["p"] == "RO:0002333":
            enabled[fa["s"]].append(fa["o"])
    activities = set(enabled)
    for i in inds:
        if MF_ROOT in types[i]:
            activities.add(i)
    # with OLS we can also classify by namespace
    term_info: dict[str, dict] = {}

    def info(t):
        if t not in term_info:
            term_info[t] = terms.lookup(t) if t.split(":")[0] in ONTOLOGY_PREFIXES else {"id": t, "found": None}
        return term_info[t]

    unclassified = []
    for i in inds:
        if i in evidence_inds or i in activities:
            continue
        for t in types[i]:
            ti = info(t)
            if ti.get("namespace") == "molecular_function":
                activities.add(i)
            elif t.startswith("GO:") and ti.get("namespace") is None and ti.get("found") is not False:
                unclassified.append(i)
    out["activity_count"] = len(activities)
    # relations: unknown to the table, or obsolete
    for pcur in sorted({fa["p"] for fa in facts}):
        if pcur in OBSOLETE_REL:
            f.add("error", "terms", f"relation {pcur} ({REL[pcur]}) is obsolete; RO replaces it with {OBSOLETE_REL[pcur]} ({REL[OBSOLETE_REL[pcur]]})")
        elif pcur not in REL:
            f.add("info", "terms", f"relation {pcur} is not in this script's table; it is counted as context, check it by hand")

    def ctx(i, pred):
        return [fa["o"] for fa in facts if fa["s"] == i and fa["p"] == pred]

    def describe(i):
        ts = [t for t in types.get(i, []) if t != "owl:NamedIndividual"]
        return {"node": short(i), "types": ts, "labels": [info(t).get("label") for t in ts]}

    # A causal predicate from an activity to a NON-activity is the legacy
    # annotation form (acts upstream of or within a process): a process link,
    # not an activity-to-activity edge. Both are reported; only the latter
    # connects the causal graph.
    causal = [fa for fa in facts if fa["p"] in CAUSAL or fa["p"] in PROCESS]
    act_causal = [fa for fa in causal if fa["p"] in CAUSAL and fa["s"] in activities and fa["o"] in activities]
    process_links = defaultdict(list)
    regulators = defaultdict(list)
    for fa in facts:
        if fa["p"] in REGULATOR:
            regulators[fa["o"]].append(fa)
    for fa in causal:
        if fa["s"] in activities and fa["o"] not in activities:
            process_links[fa["s"]].append(fa)
        elif fa["p"] in PROCESS and fa["s"] not in activities:
            process_links[fa["s"]].append(fa)   # gene product acts upstream of a process: the GPAD form
            f.add("info", "causal", f"{short(fa['s'])} ({', '.join(types.get(fa['s'], [])) or '?'}) {REL[fa['p']]} {short(fa['o'])}: a gene-product-level annotation, not an activity")
        elif fa["s"] not in activities:
            f.add("warning", "causal", f"causal relation {REL.get(fa['p'], fa['p'])} from {short(fa['s'])} ({', '.join(types.get(fa['s'], [])) or '?'}), which is not an activity, to {short(fa['o'])}")

    acts = []
    for a in sorted(activities, key=str):
        acts.append({
            **describe(a),
            "enabled_by": [describe(x) for x in enabled.get(a, [])],
            "regulated_by": [{"relation": REL[fa["p"]], **describe(fa["s"])} for fa in regulators.get(a, [])],
            "part_of": [describe(x) for x in ctx(a, "BFO:0000050")],
            "process_links": [{"relation": REL.get(fa["p"], fa["p"]), **describe(fa["o"])} for fa in process_links.get(a, [])],
            "occurs_in": [describe(x) for x in ctx(a, "BFO:0000066")],
            "has_input": [describe(x) for x in ctx(a, "RO:0002233")],
            "has_output": [describe(x) for x in ctx(a, "RO:0002234")],
        })
        if a not in enabled:
            f.add("warning", "activity", f"activity {short(a)} ({', '.join(types[a])}) has no enabled_by")
        elif len(enabled[a]) > 1:
            f.add("info", "activity", f"activity {short(a)} has {len(enabled[a])} enablers: {', '.join(curie(x) for x in enabled[a])}")
        if not ctx(a, "BFO:0000050") and not process_links.get(a):
            f.add("warning", "activity", f"activity {short(a)} is linked to no biological process (no part_of, no causal link to a process)")
        elif not ctx(a, "BFO:0000050"):
            f.add("info", "activity", f"activity {short(a)} reaches its process only by '{process_links[a][0]['p'] and REL.get(process_links[a][0]['p'])}' (legacy annotation form), not part_of")
    out["activities"] = acts

    # --- causal edges between activities, orphans, components
    out["causal_edges"] = [{
        "s": short(fa["s"]), "p": fa["p"], "p_label": REL.get(fa["p"], fa["p"]), "o": short(fa["o"]),
        "evidence": [evidence.get(e, {}) for e in fa["evidence"]],
    } for fa in act_causal]
    connected = set()
    for fa in act_causal:
        connected.add(fa["s"]); connected.add(fa["o"])
    orphans = [a for a in activities if a not in connected]
    if len(activities) > 1:
        for a in orphans:
            f.add("warning", "causal", f"activity {short(a)} has no causal connection to another activity")
    if activities and not act_causal:
        f.add("warning" if len(activities) > 1 else "info", "causal", "no causal edge between activities (a GO-CAM is expected to connect its activities)")
    # components
    parent = {a: a for a in activities}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for fa in act_causal:
        parent[find(fa["s"])] = find(fa["o"])
    comps = defaultdict(list)
    for a in activities:
        comps[find(a)].append(short(a))
    out["causal_components"] = sorted(comps.values(), key=len, reverse=True)
    if len(comps) > 1:
        f.add("info", "causal", f"activities fall into {len(comps)} causal components (sizes {sorted((len(c) for c in comps.values()), reverse=True)})")

    # --- facts without evidence; multiply reified edges; disconnected individuals
    for fa in facts:
        if fa["p"] in CONTEXT or fa["p"] in CAUSAL or fa["p"] in PROCESS or fa["p"] in REGULATOR or fa["p"] not in REL:
            if not fa["evidence"]:
                f.add("error", "evidence", f"fact {short(fa['s'])} {REL.get(fa['p'], fa['p'])} {short(fa['o'])} has no evidence")
        tuples = [(evidence[e]["eco"], tuple(evidence[e]["sources"]), tuple(evidence[e]["with"])) for e in fa["evidence"] if e in evidence]
        if len(tuples) != len(set(tuples)):
            f.add("minor", "evidence", f"fact {short(fa['s'])} {REL.get(fa['p'], fa['p'])} {short(fa['o'])} carries the same evidence line more than once")
        if len(fa["axioms"]) > 1:
            f.add("error", "structure", f"edge {short(fa['s'])} {REL.get(fa['p'], fa['p'])} {short(fa['o'])} is reified {len(fa['axioms'])} times (noctua-models QC: multiply reified edge)")
    touched = set()
    for fa in facts:
        touched.add(fa["s"]); touched.add(fa["o"])
    touched |= evidence_inds
    for i in inds:
        if i not in touched:
            f.add("error", "structure", f"individual {short(i)} ({', '.join(types[i]) or 'untyped'}) is connected to nothing (noctua-models QC: disconnected individual)")
    # the real queries, if present
    if sparql_dir and sparql_dir.is_dir() and list(sparql_dir.glob("*.rq")):
        for q in sorted(sparql_dir.glob("*.rq")):
            try:
                rows = list(g.query(q.read_text()))
                if rows:
                    f.add("error", "sparql", f"{q.name}: {len(rows)} row(s) (a row may repeat per model contributor)")
                else:
                    f.add("info", "sparql", f"{q.name}: clean")
            except Exception as e:
                f.add("warning", "sparql", f"{q.name} failed to run: {e}")
    else:
        f.add("info", "sparql", "noctua-models queries not run (no --sparql-dir); the native equivalents above ran")

    # --- terms
    used_classes = sorted({t for ts in types.values() for t in ts if t.split(":")[0] in ONTOLOGY_PREFIXES})
    used_preds = sorted({fa["p"] for fa in facts})
    term_rows = []
    for t in used_preds:   # relations: labelled from the table, not checked in OLS (they are properties)
        term_rows.append({"id": t, "label": REL.get(t, "(relation not in this script's table)"), "namespace": "relation",
                          "obsolete": None, "subsets": [], "found": None})
        if t not in REL:
            f.add("info", "terms", f"relation {t} is not in this script's table; check it by hand")
    for t in used_classes:
        ti = info(t)
        term_rows.append({"id": t, "label": ti.get("label"), "namespace": ti.get("namespace"),
                          "obsolete": ti.get("obsolete"), "subsets": ti.get("subsets", []), "found": ti.get("found")})
        if ti.get("found") is False:
            f.add("error", "terms", f"{t} not found in OLS")
        if ti.get("obsolete"):
            f.add("error", "terms", f"{t} ({ti.get('label')}) is obsolete" + (f"; replaced by {ti.get('replaced_by')}" if ti.get("replaced_by") else ""))
        for sub in ti.get("subsets", []) or []:
            if "gocheck_do_not_annotate" in sub:
                f.add("error", "terms", f"{t} ({ti.get('label')}) is in gocheck_do_not_annotate")
            if "gocheck_obsoletion_candidate" in sub:
                f.add("warning", "terms", f"{t} ({ti.get('label')}) is an obsoletion candidate")
    out["terms"] = term_rows
    if terms.offline:
        f.add("info", "terms", "offline: term existence, labels, obsolescence and subsets were not checked")
        if unclassified:
            f.add("info", "terms", f"offline: {len(unclassified)} GO-typed individual(s) without an enabler could not be classified as activity or context: {', '.join(short(i) for i in unclassified)}")
    if terms.errors:
        f.add("warning", "terms", f"{len(terms.errors)} OLS lookup(s) failed; those terms were NOT checked for existence, obsolescence or subsets")
        for e in terms.errors[:5]:
            f.add("warning", "terms", f"OLS lookup failed: {e}")
    # --- per-fact evidence lines (the dump curators read), circular with, indexes
    fact_lines = []
    ref_index = defaultdict(list)
    with_values = defaultdict(list)
    for fa in facts:
        s_types = types.get(fa["s"], []); o_types = types.get(fa["o"], [])
        rel = REL.get(fa["p"], fa["p"])
        evs = []
        for e in fa["evidence"]:
            ev = evidence.get(e, {})
            evs.append(f"{ev.get('code') or ev.get('eco') or '?'} {' '.join(ev.get('sources', [])) or 'no-ref'}" + (f" with:{','.join(ev['with'])}" if ev.get("with") else ""))
            for src in ev.get("sources", []):
                ref_index[src].append(f"{short(fa['s'])} {rel} {short(fa['o'])}")
            for w in ev.get("with", []):
                with_values[w].append(f"{short(fa['s'])} {rel} {short(fa['o'])} ({ev.get('code')})")
                # circular with: the value is the term being supported, the subject's own type, or the subject's enabler
                enablers = {t for x in enabled.get(fa["s"], []) for t in types.get(x, [])}
                if w in o_types or w in s_types or w in enablers:
                    f.add("warning", "with", f"circular with/from on {short(fa['s'])} {rel} {short(fa['o'])}: {w} is the term or gene the fact itself concerns")
        fact_lines.append({"s": short(fa["s"]), "s_types": s_types, "rel": rel, "p": fa["p"], "o": short(fa["o"]), "o_types": o_types,
                           "evidence": evs, "contributors": fa["contributors"], "dates": fa["dates"]})
    out["facts"] = fact_lines
    out["references"] = {k: v for k, v in sorted(ref_index.items())}
    out["with_values"] = {k: v for k, v in sorted(with_values.items())}
    # IEP belongs on biological processes only
    for fa in facts:
        for e in fa["evidence"]:
            if evidence.get(e, {}).get("code") == "IEP":
                o_ns = [ns for ns in (info(t).get("namespace") for t in types.get(fa["o"], [])) if ns]
                if o_ns and "biological_process" not in o_ns:
                    f.add("warning", "with", f"IEP on {short(fa['s'])} {REL.get(fa['p'], fa['p'])} {short(fa['o'])}: expression evidence supports a process, not a {o_ns[0].replace('_', ' ')}")
    # species of the entities vs the model taxon (MOD prefixes only; UniProtKB needs a lookup)
    model_taxa = set(header["taxon"])
    if model_taxa:
        for i in inds:
            for t in types.get(i, []):
                pfx = t.split(":")[0]
                implied = MOD_TAXON.get(pfx)
                if implied and implied not in model_taxa:
                    f.add("warning", "species", f"{t} ({pfx}) implies {implied}; the model's taxon is {', '.join(sorted(model_taxa))} (host-pathogen models excepted)")
    if len(activities) == 1:
        f.add("warning", "structure", "single-activity model: GO does not accept a one-activity GO-CAM; it needs placing in a multi-activity flow")
    # evidence summary
    eco_counts = defaultdict(int)
    src_counts = defaultdict(int)
    for ev in evidence.values():
        for code in (ev["eco_all"] or ["?"]):
            eco_counts[code] += 1
        for s in ev["sources"]:
            src_counts[s] += 1
    out["evidence_codes"] = dict(sorted(eco_counts.items()))
    out["evidence_without_source"] = sum(1 for ev in evidence.values() if not ev["sources"])
    out["sources"] = dict(sorted(src_counts.items()))
    return out


def read_gpad(path: Path, f: Findings) -> dict:
    rows = [l for l in path.read_text().splitlines() if l and not l.startswith("!")]
    states = set(); nots = 0
    for l in rows:
        cols = l.split("\t")
        if len(cols) > 11:
            m = re.search(r"model-state=([a-z_]+)", cols[11])
            if m:
                states.add(m.group(1))
        if len(cols) > 2 and cols[2].startswith("NOT"):
            nots += 1
    if len(states) > 1:
        f.add("warning", "gpad", f"GPAD rows carry more than one model-state: {sorted(states)}")
    return {"rows": len(rows), "model_states": sorted(states), "not_qualifiers": nots}


HOSTS = {"production": "http://noctua.geneontology.org", "dev": "http://noctua-dev.berkeleybop.org"}


def markdown(out: dict, f: Findings, gpad: dict | None, src: Path, env: str) -> str:
    m = out["model"]
    L = []
    L.append(f"# Automated QC: {m['id']}")
    L.append("")
    L.append(f"Source: `{src.name}`, read {dt.date.today().isoformat()}. This is a read-only check; nothing was changed.")
    L.append("")
    L.append("## Model")
    L.append(f"- Noctua ({env}): {HOSTS.get(env, HOSTS['production'])}/workbench/noctua-visual-pathway-editor/?model_id=gomodel:{m['id']}")
    L.append(f"- Title: {m['title'] or '(none)'}")
    L.append(f"- Taxon: {', '.join(m['taxon']) or '(none)'}")
    if m["derived_from"]:
        L.append(f"- Derived from: {', '.join(m['derived_from'])}")
    L.append(f"- State: {m['state'] or '(none)'}")
    L.append(f"- Contributors: {', '.join(m['contributors']) or '(none)'}")
    L.append(f"- Provided by: {', '.join(m['providers']) or '(none)'}")
    L.append(f"- Dates on the model: {', '.join(m['dates']) or '(none)'}")
    L.append(f"- Individuals {out['individual_count']}, activities {out['activity_count']}, facts {out['fact_count']}, evidence items {out['evidence_count']}, causal edges between activities {len(out['causal_edges'])}")
    if gpad:
        L.append(f"- GPAD export: {gpad['rows']} rows, model-state {', '.join(gpad['model_states']) or '?'}, NOT qualifiers {gpad['not_qualifiers']}")
    L.append("")
    L.append("## Findings")
    for sev in ("error", "warning", "minor", "note", "info"):
        items = f.by(sev)
        L.append(f"### {sev} ({len(items)})")
        for it in items:
            L.append(f"- [{it['check']}] {it['message']}")
        L.append("")
    L.append("## Activities")
    L.append("")
    L.append("| activity | molecular function | enabled by | process (part of, or causal link) | occurs in | inputs / outputs / regulators |")
    L.append("|---|---|---|---|---|---|")

    def lab(d):
        return ", ".join(f"{t} {l or ''}".strip() for t, l in zip(d["types"], d["labels"])) or d["node"]
    for a in out["activities"]:
        L.append("| {} | {} | {} | {} | {} | {} |".format(
            a["node"], lab(a),
            "; ".join(lab(x) for x in a["enabled_by"]) or "—",
            "; ".join([lab(x) for x in a["part_of"]] + [f"{x['relation']}: {lab(x)}" for x in a["process_links"]]) or "—",
            "; ".join(lab(x) for x in a["occurs_in"]) or "—",
            "; ".join(["in: " + lab(x) for x in a["has_input"]] + ["out: " + lab(x) for x in a["has_output"]] + [f"{x['relation']}: {lab(x)}" for x in a["regulated_by"]]) or "—"))
    L.append("")
    L.append("## Causal edges")
    L.append("")
    if out["causal_edges"]:
        L.append("| from | relation | to | evidence |")
        L.append("|---|---|---|---|")
        for e in out["causal_edges"]:
            ev = "; ".join(f"{x.get('eco')} {' '.join(x.get('sources', []))}".strip() for x in e["evidence"]) or "none"
            L.append(f"| {e['s']} | {e['p_label']} ({e['p']}) | {e['o']} | {ev} |")
    else:
        L.append("(none)")
    L.append("")
    L.append(f"Causal components: {out['causal_components']}")
    L.append("")
    L.append("## Evidence")
    L.append(f"- Codes: {out['evidence_codes']}")
    L.append(f"- Evidence with no source: {out['evidence_without_source']}")
    L.append(f"- Sources: {out['sources']}")
    L.append("")
    L.append("## Facts (what each edge rests on)")
    L.append("")
    L.append("One line per fact: subject, relation, object, then each evidence line as `CODE reference [with:...]`.")
    L.append("")
    for fl in out["facts"]:
        L.append(f"- `{fl['s']}` {' '.join(fl['s_types'])} **{fl['rel']}** `{fl['o']}` {' '.join(fl['o_types'])} :: {'; '.join(fl['evidence']) or 'NO EVIDENCE'}")
    L.append("")
    L.append("## References, and the facts each supports")
    L.append("")
    for ref, fs in out["references"].items():
        L.append(f"- {ref}: {len(fs)} fact(s): {'; '.join(fs)}")
    if not out["references"]:
        L.append("(none)")
    L.append("")
    L.append("## with/from values")
    L.append("")
    for w, fs in out["with_values"].items():
        L.append(f"- {w}: {'; '.join(fs)}")
    if not out["with_values"]:
        L.append("(none)")
    L.append("")
    L.append("## Terms used")
    L.append("")
    L.append("| term | label | namespace | obsolete | subsets |")
    L.append("|---|---|---|---|---|")
    for t in out["terms"]:
        L.append(f"| {t['id']} | {t['label'] or ''} | {t['namespace'] or ''} | {'' if t['obsolete'] is None else t['obsolete']} | {', '.join(s.split('#')[-1] for s in t['subsets'])} |")
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ttl", type=Path)
    ap.add_argument("--gpad", type=Path)
    ap.add_argument("--offline", action="store_true", help="no OLS lookups")
    ap.add_argument("--sparql-dir", type=Path, help="directory of noctua-models *.rq queries to run as well")
    ap.add_argument("--json", type=Path, help="write the machine-readable result here")
    ap.add_argument("--markdown", type=Path, help="write the report here (default: stdout)")
    ap.add_argument("--env", choices=("production", "dev"), default="production", help="which Noctua the file came from (for the link in the report)")
    ap.add_argument("--facts-only", action="store_true", help="print one sorted line per fact without node handles, for diffing two versions or a parent model")
    a = ap.parse_args(argv)
    if not a.ttl.is_file():
        print(f"no such file: {a.ttl}", file=sys.stderr); return 2
    try:
        g = load(a.ttl)
    except Exception as e:
        print(f"{a.ttl} does not parse as Turtle: {e}", file=sys.stderr); return 2
    f = Findings()
    terms = Terms(offline=a.offline)
    out = analyse(g, terms, f, a.sparql_dir)
    terms.save()
    gpad = read_gpad(a.gpad, f) if a.gpad and a.gpad.is_file() else None
    out["gpad"] = gpad
    out["findings"] = f.items
    if a.facts_only:
        lines = sorted(f"{' '.join(fl['s_types'])} --{fl['rel']}--> {' '.join(fl['o_types'])} :: {'; '.join(sorted(fl['evidence']))}" for fl in out["facts"])
        print("\n".join(lines))
        return 0
    report = markdown(out, f, gpad, a.ttl, a.env)
    if a.json:
        def default(o):
            return str(o)
        a.json.write_text(json.dumps(out, indent=1, default=default))
    if a.markdown:
        a.markdown.write_text(report)
        print(f"report: {a.markdown}  (errors {len(f.by('error'))}, warnings {len(f.by('warning'))}, minor {len(f.by('minor'))}, notes {len(f.by('note'))}, info {len(f.by('info'))})")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
