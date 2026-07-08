"""
keystone.deterministic.provenance
================================
Provenance for every generated result. Builds, for a completed run, the audit
trail behind each claim: which real connector each node came from, which nodes a
hypothesis is grounded in, and a coverage report of what is resolved vs. honestly
``unresolved``. The guarantee (``assert_no_orphan_values``) is that nothing
displayed originates from nowhere — every value ties to a source or is explicitly
marked unresolved (never fabricated).
"""
from __future__ import annotations

from keystone.core import EvidenceGraph, Hypothesis


def _source_kind(source: str) -> str:
    if source.startswith("10."):
        return "DOI"
    if ":" in source:
        return source.split(":", 1)[0]
    return "unresolved" if source == "unresolved" else "other"


def build_provenance(graph: EvidenceGraph, ledger, hyp: Hypothesis) -> dict:
    nodes = {
        nid: {"source": n.source, "kind": _source_kind(n.source),
              "resolved": n.source not in ("", "unresolved"),
              "node_type": n.node_type.value,
              "doubt": round(n.doubt.point, 3)}
        for nid, n in graph.nodes.items()}

    edges = [{"src": e.src, "dst": e.dst, "type": e.edge_type.value,
              "context_resolved": not e.context.startswith("unresolved")}
             for e in graph.edges]

    grounding = [{"node": nid, "source": graph.nodes[nid].source}
                 for nid in hyp.mechanism_path if nid in graph.nodes]

    resolved = [nid for nid, p in nodes.items() if p["resolved"]]
    unresolved_ctx = [f"{e['src']}->{e['dst']}" for e in edges
                      if not e["context_resolved"]]

    return {
        "graph_hash": ledger.graph_hash,
        "reasoner_version": ledger.reasoner_version,
        "nodes": nodes,
        "edges": edges,
        "hypothesis_grounding": grounding,
        "coverage": {
            "nodes_total": len(nodes),
            "nodes_resolved": len(resolved),
            "nodes_unresolved": len(nodes) - len(resolved),
            "unresolved_contexts": unresolved_ctx,
            "source_kinds": sorted({p["kind"] for p in nodes.values()}),
        },
        "sources": ledger.sources,
    }


def assert_no_orphan_values(prov: dict) -> None:
    """Every node's provenance is either a real source or an explicit
    'unresolved' marker — never blank, never invented. Raises on violation."""
    for nid, p in prov["nodes"].items():
        if not p["source"]:
            raise ValueError(f"orphan value: node {nid} has no source and is not "
                             f"marked unresolved")
