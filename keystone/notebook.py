"""
keystone.notebook
================
Scientific Notebook — the composition the demo was missing:

  Protocol -> Evidence -> Comments -> Reviewer -> Version History -> Publication

It is NOT a free-text tool disconnected from the Ledger. Every section is a
projection of a real object: Protocol is the ExperimentPlan, Evidence is the
graph, Reviewer is the ReviewResult, Version History is replay.py's ordered
session steps plus ledger_index's prior runs, and Publication is report.py.
Comments are the one human element — attributed annotations pinned to this run's
graph_hash, so they travel with the reproducible record.
"""
from __future__ import annotations

from keystone.workbench import run
from keystone.agents.reasoner import HeuristicReasoner
from keystone.replay import record_session


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


def build_notebook(domain: str = "gbm", comments: list | None = None,
                   prior_runs: int = 0) -> dict:
    spec, build = _spec_and_builder(domain)
    graph = build()
    ledger, hyp, review = run(spec.QUESTION, graph, HeuristicReasoner())
    session = record_session(spec.QUESTION, graph, ledger, hyp, review)
    ep = hyp.validation_experiment

    return {
        "domain": domain, "question": spec.QUESTION,
        "graph_hash": ledger.graph_hash,
        "sections": {
            "protocol": {
                "perturbation": ep.perturbation, "system": ep.system,
                "positive_controls": ep.positive_controls,
                "negative_controls": ep.negative_controls,
                "readout": ep.readout, "kill_condition": ep.kill_condition,
                "n_per_arm": ep.required_n_per_arm, "stats_notes": ep.stats_notes,
                "reproducibility_checklist": ep.reproducibility_checklist},
            "evidence": [
                {"id": n.id, "type": n.node_type.value, "source": n.source,
                 "doubt": round(n.doubt.point, 3), "retracted": n.retracted,
                 "text": n.text}
                for n in graph.nodes.values()],
            "comments": comments or [],   # human, attributed, pinned to this hash
            "reviewer": {"verdict": review.verdict.value,
                         "weakness": review.weakness,
                         "adjusted_confidence": review.adjusted_confidence.point},
            "version_history": {
                "steps": [{"index": s.index, "stage": s.stage,
                           "summary": s.summary} for s in session.steps],
                "prior_runs_indexed": prior_runs,
                "note": "the Ledger's ordered stages ARE the version history "
                        "(replay.py); prior runs from ledger_index (scientific memory)"},
            "publication": {"report_available": True,
                            "endpoint": f"/api/report?domain={domain}",
                            "reproducibility_hash": ledger.graph_hash},
        },
    }


def make_comment(author: str, text: str, graph_hash: str) -> dict:
    """A human annotation pinned to a specific reproducible run."""
    import time
    return {"author": (author or "anonymous").strip(),
            "text": text.strip(),
            "at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pinned_to_hash": graph_hash}
