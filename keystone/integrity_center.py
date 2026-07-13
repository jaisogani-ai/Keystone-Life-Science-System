"""
keystone.integrity_center
========================
Research Integrity Center — a UI-ready composition of integrity checks that
ALREADY EXIST in the codebase. It invents no new science; it surfaces, in one
place, what Keystone already computes:

  Cell Authentication   -> Cellosaurus 'problematic cell line' flag (real)
  Protocol Validation   -> deterministic/protocol.validate_protocol (real)
  Evidence Quality      -> the load-bearing moat + doubt on grounding (real)
  Publication Validation-> retraction_status / Retraction Watch (real)
  Dataset Validation    -> Tier 2, not wired (no GEO/SRA connector) — honest slot
  Antibody Validation   -> Tier 2, not wired (no antibody registry) — honest slot

Every check reports pass / warn / fail / not_wired with its real source; a
not-wired check is never silently 'passed'.
"""
from __future__ import annotations

from keystone.core import node_label
from keystone.workbench import run
from keystone.agents.reasoner import HeuristicReasoner
from keystone.connectors import registry as R
from keystone.deterministic.protocol import validate_protocol


def _check(name, tier, status, detail, source) -> dict:
    return {"name": name, "tier": tier, "status": status, "detail": detail,
            "source": source}


def _spec_and_builder(domain: str):
    if domain == "insulin":
        from keystone import insulin_spec as SPEC
        from keystone.data_insulin import build_insulin_graph as build
        return SPEC, build
    if domain == "ich":
        from keystone import ich_spec as SPEC
        from keystone.data_ich import build_ich_graph as build
        return SPEC, build
    if domain == "tcell":
        from keystone import tcell_spec as SPEC
        from keystone.data_tcell import build_tcell_graph as build
        return SPEC, build
    from keystone import gbm_spec as SPEC
    from keystone.data_gbm import build_gbm_graph as build
    return SPEC, build


def run_integrity_center(domain: str = "gbm") -> dict:
    spec, build = _spec_and_builder(domain)
    graph = build()
    ledger, hyp, review = run(spec.QUESTION, graph, HeuristicReasoner())
    checks = []

    # 1. Cell Authentication — real Cellosaurus problematic-line flag
    reagent = next((n for n in graph.nodes.values()
                    if n.node_type.value == "reagent"), None)
    if reagent is not None:
        prob = reagent.meta.get("problematic")
        checks.append(_check(
            "Known-misidentification flag (Cellosaurus/ICLAC)", 1, "fail" if prob else "pass",
            (f"{reagent.text.split(' — ')[0]} is flagged misidentified: "
             f"{(prob or '')[:90]}") if prob
            else f"{reagent.text.split(' — ')[0]} — no misidentification flag",
            reagent.source))
    else:
        checks.append(_check("Known-misidentification flag (Cellosaurus/ICLAC)", 1, "not_applicable",
                             "no reagent/cell-line node in this graph", "—"))

    # 2. Protocol Validation — real deterministic validator
    warns = validate_protocol(hyp.validation_experiment)
    checks.append(_check(
        "Protocol Validation", 1, "warn" if warns else "pass",
        (f"{len(warns)} issue(s): " + "; ".join(warns)) if warns
        else "controls, kill-condition, and grounded sample size all present",
        "deterministic/protocol.py"))

    # 3. Evidence Quality — the load-bearing moat + inherited doubt
    doubts = [n.doubt.point for n in graph.nodes.values()]
    high = [n for n in graph.nodes.values() if n.doubt.point >= 0.6]
    checks.append(_check(
        "Evidence Quality", 1, "warn" if high else "pass",
        (f"{len(high)} grounding/evidence node(s) carry high inherited doubt "
         f"({', '.join(node_label(n) for n in high)}); "
         f"mean doubt {sum(doubts)/len(doubts):.2f}")
        if high else f"mean inherited doubt {sum(doubts)/len(doubts):.2f}",
        "load-bearing classification (calibrated 0.818)"))

    # 4. Publication Validation — real Retraction Watch status
    retracted = [n for n in graph.nodes.values() if n.retracted]
    if retracted:
        r0 = retracted[0]
        # retraction_status handles a bare DOI or a full doi.org URL
        rec = R.retraction_status(r0.source) if "10." in r0.source else {}
        checks.append(_check(
            "Publication Validation", 1, "fail",
            f"{len(retracted)} node(s) rest on RETRACTED work "
            f"({', '.join(node_label(n) for n in retracted)}); "
            f"e.g. retracted {rec.get('retraction_date', 'yes')} via "
            f"{rec.get('via', 'retraction watch')}",
            "Retraction Watch (via Crossref)"))
    else:
        checks.append(_check("Publication Validation", 1, "pass",
                             "no cited work is retracted", "Retraction Watch"))

    # 5/6. Tier-2 honest slots — never silently passed
    checks.append(_check("Dataset Validation", 2, "not_wired",
                         "no GEO/SRA dataset connector wired — cannot validate "
                         "underlying datasets this build", "GEO/SRA (declared)"))
    checks.append(_check("Antibody Validation", 2, "not_wired",
                         "no antibody-registry connector wired — cannot validate "
                         "antibody provenance this build", "Antibody Registry (declared)"))

    tier1 = [c for c in checks if c["tier"] == 1 and c["status"] != "not_applicable"]
    passed = [c for c in tier1 if c["status"] == "pass"]
    failed = [c for c in tier1 if c["status"] == "fail"]
    return {
        "domain": domain, "question": spec.QUESTION,
        "graph_hash": ledger.graph_hash, "checks": checks,
        "summary": {
            "tier1_total": len(tier1), "passed": len(passed),
            "failed": len(failed),
            "warned": len([c for c in tier1 if c["status"] == "warn"]),
            "not_wired": len([c for c in checks if c["status"] == "not_wired"]),
            "verdict": ("integrity concerns — see failed checks" if failed
                        else "clean on wired checks" )},
    }
