"""
keystone.workbench
=================
The orchestrator: Plan -> Collect -> Analyze -> Hypothesize -> Design Experiment
-> Review -> Ledger. The proposer is always semantic (the Reasoner), the checker
is always deterministic (stats / propagation / protocol). Human approval (rule 1)
is applied to the returned Ledger by the caller/UI, not fabricated here.
"""
from __future__ import annotations

from keystone.core import EvidenceGraph, Ledger
from keystone.deterministic.propagation import propagate_doubt
from keystone.deterministic.protocol import validate_protocol


def _build_timeline(graph: EvidenceGraph) -> list:
    events = []
    for n in graph.nodes.values():
        if n.date:
            events.append({"date": n.date, "kind": n.node_type.value,
                           "label": n.text[:70]})
        if n.retracted and n.meta.get("retraction_date"):
            via = n.meta.get("retraction_via") or "retraction watch"
            events.append({"date": n.meta["retraction_date"], "kind": "retraction",
                           "label": f"RETRACTED ({via}) — {n.text[:44]}"})
    events.sort(key=lambda e: e["date"])
    return events


def run(question: str, graph: EvidenceGraph, reasoner):
    """Run the full loop. Returns ``(Ledger, Hypothesis, ReviewResult)``.
    Mutates only the *container* (swaps nodes/edges for recomputed immutable
    copies); it never mutates a Node or Edge value in place."""
    # PLAN (semantic)
    plan = reasoner.plan(question)

    # ANALYZE: the Evidence-Quality agent classifies each reliance edge, then
    # doubt propagates deterministically.
    for i, e in enumerate(graph.edges):
        if e.edge_type.value in ("cites", "depends_on"):
            graph.replace_edge(i, load_bearing=reasoner.classify_load_bearing(e.context))
    propagate_doubt(graph)

    # LITERATURE: contradictions are a graph operation (a discovery opportunity).
    contradictions = [[e.src, e.dst] for e in graph.edges
                      if e.edge_type.value == "contradicts"]

    # HYPOTHESIZE (semantic, rule-3 enforced inside generate_hypothesis)
    hyp = reasoner.generate_hypothesis(graph)

    # DESIGN + deterministic validation
    warnings = validate_protocol(hyp.validation_experiment)

    # REVIEW (independent challenge, rule 4)
    review = reasoner.review(hyp, graph)

    # LEDGER (deterministic, reproducible artifact — rule 5/6)
    sources = sorted({n.source for n in graph.nodes.values()
                      if n.source and n.source != "unresolved"})
    ledger = Ledger(
        question=question, reasoner_version=getattr(reasoner, "version", "?"),
        graph_hash=graph.snapshot_hash(), plan=plan,
        contradictions=contradictions, timeline=_build_timeline(graph),
        protocol_warnings=warnings, sources=sources,
        hypothesis_statement=hyp.statement,
        hypothesis_grounding=list(hyp.mechanism_path))
    return ledger, hyp, review
