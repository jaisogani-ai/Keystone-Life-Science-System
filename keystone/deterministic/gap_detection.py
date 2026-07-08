"""
keystone.deterministic.gap_detection
===================================
Gap Detection, promoted to a named loop stage — again NOT a new agent. It reuses
``reasoning_panel.research_readiness``'s already-computed missing-evidence count
and adds two structural gaps read straight off the graph: citations whose
context could not be resolved, and grounding nodes with no independent
corroboration. Every gap is a real, countable absence — never a fabricated one.
"""
from __future__ import annotations

from keystone.core import EvidenceGraph, Hypothesis, ReviewResult
from keystone.reasoning_panel import research_readiness


def detect_gaps(hyp: Hypothesis, review: ReviewResult,
                graph: EvidenceGraph) -> dict:
    readiness = research_readiness(hyp, review, graph)
    gaps = list(readiness["missing_evidence"]["items"])

    unresolved = [f"{e.src}->{e.dst}" for e in graph.edges
                  if e.context.startswith("unresolved")
                  and e.edge_type.value in ("cites", "depends_on")]
    if unresolved:
        gaps.append(f"{len(unresolved)} citing context(s) unresolved "
                    f"(cannot judge load-bearing): {', '.join(unresolved)}")

    # a grounding node that nothing else supports is a corroboration gap
    supported = {e.dst for e in graph.edges if e.edge_type.value == "supports"}
    for nid in hyp.mechanism_path:
        node = graph.nodes.get(nid)
        if node and node.node_type.value == "target" and nid not in supported:
            gaps.append(f"target {nid} lacks an independent supporting result")

    return {"stage": "gap_detection", "count": len(gaps), "gaps": gaps,
            "readiness_missing": readiness["missing_evidence"]["count"]}
