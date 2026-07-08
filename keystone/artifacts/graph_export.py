"""
keystone.artifacts.graph_export
==============================
Serialize an EvidenceGraph to a plain JSON-able dict for the Evidence Graph
Browser — a pure PROJECTION (rule 3 / CONTRIBUTING). No doubt is computed, no
interval is derived here; every value is copied straight off the already-computed
Node/Edge. The round-trip (``graph_to_dict`` -> ``graph_from_dict``) is lossless,
which the test asserts.

The browser is presentation only: it reads this dict and renders it. If anything
downstream needs a *new* number, that belongs in ``keystone/deterministic/`` and
must be re-exported, never computed in the browser.
"""
from __future__ import annotations

from keystone.core import (EvidenceGraph, Node, Edge, Interval, NodeType,
                           EdgeType, TemporalRelation)


def _interval(iv: Interval) -> dict:
    return {"point": iv.point, "low": iv.low, "high": iv.high}


def graph_to_dict(graph: EvidenceGraph) -> dict:
    """Project the graph to a JSON-serializable dict. Nodes keep their NodeType
    (the browser's 'layer' axis), doubt interval and integrity flags; edges keep
    their load-bearing interval, temporal relation and citing context."""
    return {
        "hash": graph.snapshot_hash(),
        "node_types": [t.value for t in NodeType],   # the layer axis, in order
        "nodes": [
            {"id": n.id, "node_type": n.node_type.value, "source": n.source,
             "text": n.text, "doubt": _interval(n.doubt), "date": n.date,
             "retracted": n.retracted, "inexcusable": n.inexcusable,
             "meta": n.meta}
            for n in graph.nodes.values()],
        "edges": [
            {"src": e.src, "dst": e.dst, "edge_type": e.edge_type.value,
             "load_bearing": _interval(e.load_bearing),
             "temporal": e.temporal.value, "context": e.context,
             "rationale": e.rationale}
            for e in graph.edges],
    }


def graph_from_dict(data: dict) -> EvidenceGraph:
    """Reconstruct an EvidenceGraph from ``graph_to_dict`` output (lossless)."""
    g = EvidenceGraph()
    for n in data["nodes"]:
        g.add_node(Node(
            id=n["id"], node_type=NodeType(n["node_type"]), source=n["source"],
            text=n["text"], doubt=Interval(**n["doubt"]), date=n.get("date", ""),
            retracted=n.get("retracted", False),
            inexcusable=n.get("inexcusable", False), meta=n.get("meta", {})))
    for e in data["edges"]:
        g.add_edge(Edge(
            src=e["src"], dst=e["dst"], edge_type=EdgeType(e["edge_type"]),
            load_bearing=Interval(**e["load_bearing"]),
            temporal=TemporalRelation(e["temporal"]),
            context=e.get("context", ""), rationale=e.get("rationale", "")))
    return g
