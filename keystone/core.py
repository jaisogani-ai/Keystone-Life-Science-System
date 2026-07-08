"""
keystone.core
=============
The trust primitives: the data model, the rule-3-enforced Hypothesis, and the
auditable Ledger. Everything here is deterministic and immutable — nodes, edges,
intervals and experiment plans are frozen; a "change" produces a new object
(``dataclasses.replace``), never an in-place mutation. Only the ``EvidenceGraph``
container holds mutable dict/list of otherwise-immutable values, so the
orchestrator can swap in recomputed nodes without ever mutating one.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace, asdict
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enumerations (each exposes ``.value`` — the surface files rely on this)
# ---------------------------------------------------------------------------
class NodeType(Enum):
    PAPER = "paper"
    REAGENT = "reagent"
    MOLECULAR_RESULT = "molecular_result"
    TARGET = "target"
    DATASET = "dataset"
    CLINICAL = "clinical"
    UNRESOLVED = "unresolved"


class EdgeType(Enum):
    CITES = "cites"
    DEPENDS_ON = "depends_on"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    TARGETS = "targets"


class TemporalRelation(Enum):
    PRE_RETRACTION = "pre_retraction"
    POST_RETRACTION = "post_retraction"
    CONCURRENT = "concurrent"
    NA = "n/a"


class ReviewVerdict(Enum):
    SUPPORTED = "supported"
    DOWNGRADED = "downgraded"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Interval — a point estimate that always carries its uncertainty
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Interval:
    """A value that never travels without its band. Used for confidence, doubt
    and load-bearing weight so the system can never present a bare number."""
    point: float
    low: float
    high: float

    def clamp(self) -> "Interval":
        lo, hi = max(0.0, self.low), min(1.0, self.high)
        return Interval(min(max(0.0, self.point), 1.0), min(lo, hi), max(lo, hi))


# ---------------------------------------------------------------------------
# Evidence graph
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Node:
    id: str
    node_type: NodeType
    source: str                 # provenance: DOI / accession / "unresolved"
    text: str
    doubt: Interval             # 0 = fully trusted, 1 = fully doubted
    date: str = ""              # ISO date, for the timeline projection
    retracted: bool = False
    inexcusable: bool = False   # post-retraction reliance flag
    meta: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    edge_type: EdgeType
    load_bearing: Interval      # how load-bearing the src->dst reliance is
    temporal: TemporalRelation = TemporalRelation.NA
    context: str = ""           # the citing sentence, when resolvable
    rationale: str = ""


class EvidenceGraph:
    """Mutable container of immutable Nodes/Edges. The container may be updated
    (swap a node for a recomputed copy); the values themselves are never
    mutated. Content-hashed over the *evidence* (ids/sources/text/structure),
    not the derived doubt, so re-runs of the same evidence hash identically."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)

    def copy(self) -> "EvidenceGraph":
        """A new container over the same immutable Nodes/Edges. Mutating the copy
        (via replace_node/replace_edge) leaves the original untouched — the basis
        for non-destructive flaw injection."""
        g = EvidenceGraph()
        g.nodes = dict(self.nodes)
        g.edges = list(self.edges)
        return g

    def replace_node(self, node_id: str, **changes) -> None:
        self.nodes[node_id] = replace(self.nodes[node_id], **changes)

    def replace_edge(self, index: int, **changes) -> None:
        self.edges[index] = replace(self.edges[index], **changes)

    def incoming_dependencies(self, node_id: str) -> list[Edge]:
        """Edges where ``node_id`` relies on another node (cites/depends_on)."""
        dep = (EdgeType.CITES, EdgeType.DEPENDS_ON)
        return [e for e in self.edges if e.src == node_id and e.edge_type in dep]

    def snapshot_hash(self) -> str:
        payload = {
            "nodes": sorted(
                [f"{n.id}|{n.node_type.value}|{n.source}|{n.text}|{n.date}|{n.retracted}"
                 for n in self.nodes.values()]),
            "edges": sorted(
                [f"{e.src}|{e.dst}|{e.edge_type.value}|{e.temporal.value}"
                 for e in self.edges]),
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Experiment plan
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ExperimentPlan:
    perturbation: str
    system: str
    positive_controls: list
    negative_controls: list
    readout: str
    expected_outcome: str
    kill_condition: str
    effect_size_source: str
    assumed_effect_size: Optional[float]
    assumed_sd: Optional[float]
    alpha: float
    power: float
    required_n_per_arm: Optional[int]
    reproducibility_checklist: list = field(default_factory=list)
    stats_notes: str = ""


# ---------------------------------------------------------------------------
# Hypothesis — rule 3 is enforced here, not aspired to
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Hypothesis:
    id: str
    statement: str
    mechanism_path: list
    supporting_evidence: list
    contradicting_evidence: list
    confidence: Interval
    uncertainty_notes: str
    validation_experiment: ExperimentPlan
    expected_outcome: str
    failure_modes: list = field(default_factory=list)

    def validate(self) -> None:
        """Rule 3: every hypothesis carries supporting + contradicting evidence,
        a confidence interval, remaining uncertainty, a falsifiable validation
        experiment with a named kill-condition, an expected outcome, and failure
        modes. Any omission is a hard rejection (raises ValueError)."""
        problems = []
        if not self.statement.strip():
            problems.append("empty statement")
        if not self.supporting_evidence:
            problems.append("no supporting evidence")
        if not self.contradicting_evidence:
            problems.append("no contradicting evidence recorded")
        if self.confidence.high <= self.confidence.low:
            problems.append("confidence has no interval")
        if not self.uncertainty_notes.strip():
            problems.append("no remaining-uncertainty note")
        if not self.failure_modes:
            problems.append("no failure modes")
        ep = self.validation_experiment
        if not ep.kill_condition.strip():
            problems.append("validation experiment has no kill-condition")
        if not ep.positive_controls or not ep.negative_controls:
            problems.append("validation experiment missing controls")
        if not self.expected_outcome.strip():
            problems.append("no expected outcome")
        if problems:
            raise ValueError("Hypothesis fails rule 3: " + "; ".join(problems))


# ---------------------------------------------------------------------------
# Reviewer result
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ReviewResult:
    verdict: ReviewVerdict
    weakness: str
    adjusted_confidence: Interval
    objections: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Ledger — the auditable artifact (rule 5)
# ---------------------------------------------------------------------------
@dataclass
class Ledger:
    question: str
    reasoner_version: str
    graph_hash: str
    plan: dict
    contradictions: list
    timeline: list
    protocol_warnings: list
    sources: list = field(default_factory=list)
    human_decision: Optional[str] = None
    human_signoff: Optional[str] = None
    # Additive (Tier-0 extend-by-addition): lets ledger_index answer "has this
    # hypothesis, or one grounded in the same evidence, been tried before?"
    hypothesis_statement: Optional[str] = None
    hypothesis_grounding: list = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)
