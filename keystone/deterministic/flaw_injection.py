"""
keystone.deterministic.flaw_injection
=====================================
Plant ONE known flaw into an evidence graph, deterministically and structurally —
no LLM (rule 7 / CONTRIBUTING). Given a graph and a flaw type, return a NEW graph
(the original is never mutated — see ``EvidenceGraph.copy`` + ``replace_node`` /
``replace_edge``) together with the ground truth of exactly what was planted.

The catalogue is fixed and each flaw is grounded in a real ``Node``/``Edge``
field. Injection only corrupts data; deciding whether an agent *catches* the flaw
is a separate step (``keystone.agents.flaw_catch_eval``) and is the only place an
LLM may run.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional

from keystone.core import EvidenceGraph, Interval, NodeType, TemporalRelation


class FlawType(str, Enum):
    FALSE_RETRACTION = "false_retraction"          # flip retracted on a clean paper
    CORRUPT_CONTEXT = "corrupt_context"            # misrepresent a citing sentence
    HIDE_TEMPORAL = "hide_temporal"                # post-retraction -> pre (hide it)
    HIDE_REAGENT_PROBLEM = "hide_reagent_problem"  # clear a Cellosaurus misID flag


FLAW_CATALOGUE = [FlawType.FALSE_RETRACTION, FlawType.CORRUPT_CONTEXT,
                  FlawType.HIDE_TEMPORAL, FlawType.HIDE_REAGENT_PROBLEM]

# A fixed, misrepresenting replacement sentence (structural, no LLM). It recasts a
# load-bearing citation as unrelated background — a real way citations get abused.
_MISREPRESENTING_CONTEXT = ("The cited study is noted only in passing as general "
                            "background and is unrelated to the present result "
                            "[4, 7, 12].")


@dataclass(frozen=True)
class PlantedFlaw:
    flaw_type: str
    target: str
    field: str
    clean_value: object
    flawed_value: object
    description: str
    expected_signal: str   # which agent should react, and how


@dataclass(frozen=True)
class FlawResult:
    graph: EvidenceGraph
    planted: Optional[PlantedFlaw]   # None if no eligible target existed


# ---------------------------------------------------------------------------
# Deterministic target selection (graph-only, so it generalizes across domains)
# ---------------------------------------------------------------------------
def _clean_grounding_node(graph: EvidenceGraph):
    """A clean bibliographic node the conclusion actually rests on — the source
    of a SUPPORTS edge — so a planted retraction here is conclusion-relevant
    (missing it would be genuinely confident-wrong). Falls back to the
    lowest-doubt clean result if the graph records no supporting evidence."""
    supporting = {e.src for e in graph.edges if e.edge_type.value == "supports"}
    cand = [n for n in graph.nodes.values()
            if n.node_type in (NodeType.MOLECULAR_RESULT, NodeType.PAPER)
            and not n.retracted]
    grounded = [n for n in cand if n.id in supporting]
    pool = grounded or cand
    if not pool:
        return None
    return sorted(pool, key=lambda n: (n.doubt.point, n.id))[0]


def _top_load_bearing_cite(graph: EvidenceGraph):
    cites = [(i, e) for i, e in enumerate(graph.edges)
             if e.edge_type.value in ("cites", "depends_on")
             and not e.context.startswith("unresolved")]
    if not cites:
        return None
    return sorted(cites, key=lambda ie: (-ie[1].load_bearing.point, ie[1].src))[0]


def _inexcusable_node(graph: EvidenceGraph):
    cand = [n for n in graph.nodes.values() if n.inexcusable]
    return sorted(cand, key=lambda n: n.id)[0] if cand else None


def _reagent_with_problem(graph: EvidenceGraph):
    cand = [n for n in graph.nodes.values()
            if n.node_type == NodeType.REAGENT and n.meta.get("problematic")]
    return sorted(cand, key=lambda n: n.id)[0] if cand else None


# ---------------------------------------------------------------------------
# Injection
# ---------------------------------------------------------------------------
def inject_flaw(graph: EvidenceGraph, flaw_type: FlawType) -> FlawResult:
    """Return a copy of ``graph`` with one planted flaw + its ground truth."""
    g = graph.copy()

    if flaw_type == FlawType.FALSE_RETRACTION:
        node = _clean_grounding_node(graph)
        if node is None:
            return FlawResult(g, None)
        g.replace_node(node.id, retracted=True,
                       doubt=Interval(0.97, 0.9, 1.0),
                       meta={**node.meta, "planted": "false_retraction"})
        return FlawResult(g, PlantedFlaw(
            flaw_type.value, node.id, "retracted", False, True,
            f"planted a false retraction (+doubt spike) on clean grounding node "
            f"{node.id}",
            "Reviewer should downgrade harder now that a supporting node is "
            "retracted / high-doubt"))

    if flaw_type == FlawType.CORRUPT_CONTEXT:
        hit = _top_load_bearing_cite(graph)
        if hit is None:
            return FlawResult(g, None)
        idx, edge = hit
        g.replace_edge(idx, context=_MISREPRESENTING_CONTEXT,
                       rationale=edge.rationale + " [planted:corrupt_context]")
        return FlawResult(g, PlantedFlaw(
            flaw_type.value, f"{edge.src}->{edge.dst}", "context",
            edge.context, _MISREPRESENTING_CONTEXT,
            f"misrepresented the load-bearing citing sentence on "
            f"{edge.src}->{edge.dst}",
            "Evidence-Quality should score this edge much less load-bearing"))

    if flaw_type == FlawType.HIDE_TEMPORAL:
        node = _inexcusable_node(graph)
        if node is None:
            return FlawResult(g, None)
        g.replace_node(node.id, inexcusable=False,
                       meta={**node.meta, "planted": "hide_temporal"})
        for i, e in enumerate(g.edges):
            if e.src == node.id and e.temporal == TemporalRelation.POST_RETRACTION:
                g.replace_edge(i, temporal=TemporalRelation.PRE_RETRACTION)
        return FlawResult(g, PlantedFlaw(
            flaw_type.value, node.id, "inexcusable/temporal", True, False,
            f"relabelled the post-retraction citation {node.id} as "
            f"pre-retraction and cleared its inexcusable flag",
            "an integrity-aware Reviewer should still flag the post-retraction "
            "reliance"))

    if flaw_type == FlawType.HIDE_REAGENT_PROBLEM:
        node = _reagent_with_problem(graph)
        if node is None:
            return FlawResult(g, None)
        g.replace_node(node.id, doubt=Interval(0.1, 0.05, 0.15),
                       meta={**node.meta, "problematic": None,
                             "planted": "hide_reagent_problem"})
        return FlawResult(g, PlantedFlaw(
            flaw_type.value, node.id, "meta.problematic/doubt",
            node.meta.get("problematic"), None,
            f"hid the Cellosaurus misidentification on reagent {node.id} "
            f"(cleared flag, dropped doubt)",
            "a reagent-aware Reviewer should still distrust the misidentified "
            "line"))

    return FlawResult(g, None)


# ---------------------------------------------------------------------------
# Benign controls (negatives for the eval — must NOT change any agent output)
# ---------------------------------------------------------------------------
class BenignPerturbation(str, Enum):
    REORDER_EDGES = "reorder_edges"
    ADD_META = "add_meta"
    SHIFT_NONBOUNDARY_DATE = "shift_nonboundary_date"


BENIGN_CATALOGUE = list(BenignPerturbation)


def apply_benign(graph: EvidenceGraph, kind: BenignPerturbation) -> EvidenceGraph:
    """A change no correct integrity check should react to — used as the negative
    class. None of these touch a field the agents read."""
    g = graph.copy()
    if kind == BenignPerturbation.REORDER_EDGES:
        g.edges = list(reversed(g.edges))
    elif kind == BenignPerturbation.ADD_META:
        nid = sorted(g.nodes)[0]
        g.replace_node(nid, meta={**g.nodes[nid].meta, "note": "reviewed"})
    elif kind == BenignPerturbation.SHIFT_NONBOUNDARY_DATE:
        # bump a target/reagent date (agents read doubt/context, never date)
        for nid, n in g.nodes.items():
            if n.node_type == NodeType.TARGET:
                g.replace_node(nid, date="1999-01-01")
                break
    return g
