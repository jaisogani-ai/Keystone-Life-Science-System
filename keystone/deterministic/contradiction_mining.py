"""
keystone.deterministic.contradiction_mining
===========================================
Contradiction Mining, promoted to a named loop stage — but it is NOT a new agent.
It is a deterministic pass over the ``EdgeType.CONTRADICTS`` edges already modeled
in ``core.py`` (rule 7). It surfaces, for each recorded contradiction, the two
sides, their doubt, and whether one side is compromised (retracted) — a discovery
opportunity, computed, not reasoned.
"""
from __future__ import annotations

from keystone.core import EvidenceGraph


def mine_contradictions(graph: EvidenceGraph) -> list[dict]:
    """Project every contradiction edge into an inspectable record. Deterministic;
    the same graph yields the same list every run."""
    out = []
    for e in graph.edges:
        if e.edge_type.value != "contradicts":
            continue
        src = graph.nodes.get(e.src)
        dst = graph.nodes.get(e.dst)
        out.append({
            "claim": e.src,
            "against": e.dst,
            "claim_text": src.text if src else e.src,
            "against_text": dst.text if dst else e.dst,
            "claim_doubt": round(src.doubt.point, 3) if src else None,
            "against_doubt": round(dst.doubt.point, 3) if dst else None,
            "against_retracted": bool(dst.retracted) if dst else False,
            "context": e.context,
            # a contradiction against a retracted/high-doubt node is the strongest
            # discovery opportunity — flag it deterministically
            "opportunity": bool(dst and (dst.retracted or dst.doubt.point >= 0.6)),
        })
    out.sort(key=lambda r: (not r["opportunity"], r["claim"]))
    return out
