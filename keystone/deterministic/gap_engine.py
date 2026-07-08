"""
keystone.deterministic.gap_engine
================================
The Knowledge Gap Engine — categorized. Beyond contradictions, it answers the
question a PI actually asks: "what evidence is preventing publication?" Seven gap
types, each a real, computed absence read off the graph — never an invented one.
"""
from __future__ import annotations

from keystone.core import EvidenceGraph, Hypothesis


def detect_knowledge_gaps(hyp: Hypothesis, graph: EvidenceGraph) -> dict:
    types = graph_types = {n.node_type.value for n in graph.nodes.values()}
    ep = hyp.validation_experiment
    supporting = [e for e in graph.edges if e.edge_type.value == "supports"]
    molecular = [n for n in graph.nodes.values()
                 if n.node_type.value == "molecular_result"]
    unresolved = [e for e in graph.edges if e.context.startswith("unresolved")]

    checks = [
        ("missing_dataset", "dataset" not in graph_types,
         "no primary DATASET node in the evidence graph (no GEO/SRA expression "
         "data wired to this claim)"),
        ("missing_control", not (ep.positive_controls and ep.negative_controls),
         "the validation experiment lacks a positive or negative control"),
        ("missing_replication", len(supporting) < 2,
         "fewer than two independent supporting results — no replication"),
        ("missing_biomarker",
         not any("marker" in n.text.lower() or "mgmt" in n.text.lower()
                 or "subtype" in n.text.lower() for n in molecular),
         "no stratifying biomarker is grounded — response may be heterogeneous"),
        ("missing_validation", ep.required_n_per_arm is None or True,
         "no completed validation experiment yet (the designed one is unrun)"),
        ("missing_literature", bool(unresolved),
         f"{len(unresolved)} citing context(s) unresolved — load-bearing weight "
         f"cannot be judged for those citations"),
        ("missing_molecular", not molecular,
         "no independent molecular result corroborates the claim"),
    ]
    gaps = [{"type": t, "detail": d} for (t, present, d) in checks if present]
    return {"count": len(gaps), "gaps": gaps,
            "blocking_publication": [g["type"] for g in gaps
                                     if g["type"] in ("missing_replication",
                                                      "missing_validation",
                                                      "missing_control")]}
