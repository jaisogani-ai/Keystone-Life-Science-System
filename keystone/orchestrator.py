"""
keystone.orchestrator
====================
Explicit multi-agent orchestration, in the Claude Science style: a central
Planner coordinates specialist agents, each verified against deterministic tools,
with an independent Reviewer at the end. This makes the "AI as assistant, not
centerpiece" principle concrete — every semantic agent's output is checked by, or
handed to, a deterministic tool that produces the actual numbers.

The orchestrator does not re-implement the loop; it runs it and records a
faithful, provenance-bearing TRACE of who did what. Each step declares whether it
was an ``agent`` (semantic, Claude/heuristic) or a ``tool`` (deterministic), its
inputs, outputs, the evidence it relied on, and a confidence where one exists.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field

from keystone.workbench import run
from keystone.deterministic.contradiction_mining import mine_contradictions
from keystone.deterministic.gap_detection import detect_gaps


@dataclass(frozen=True)
class AgentStep:
    step: int
    actor: str
    actor_type: str        # "agent" (semantic) | "tool" (deterministic)
    role: str
    inputs: str
    output: str
    evidence: list = field(default_factory=list)     # provenance ids / sources
    confidence: float | None = None
    # the same structured schema every seat exposes (Hypothesis/ReviewResult) —
    # narration of real objects, no second schema per agent type
    sources: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    failure_modes: list = field(default_factory=list)
    artifacts: list = field(default_factory=list)


def build_trace(question, graph, ledger, hyp, review) -> list[dict]:
    """Reconstruct the faithful orchestration trace from a completed run."""
    lb = {f"{e.src}->{e.dst}": round(e.load_bearing.point, 2) for e in graph.edges
          if e.edge_type.value in ("cites", "depends_on")}
    contradictions = mine_contradictions(graph)
    gaps = detect_gaps(hyp, review, graph)
    sources = sorted({n.source for n in graph.nodes.values()
                      if n.source and n.source != "unresolved"})

    steps = [
        AgentStep(1, "Scientific Planner", "agent",
                  "decompose the question into a bounded plan",
                  question[:80], f"intent={ledger.plan.get('intent')}, "
                  f"connectors={len(ledger.plan.get('connectors', []))}",
                  evidence=[question[:60]]),
        AgentStep(2, "Connectors", "tool",
                  "collect real evidence into the graph",
                  "planned connectors",
                  f"{len(graph.nodes)} nodes, {len(graph.edges)} edges",
                  evidence=sources[:8]),
        AgentStep(3, "Evidence-Quality Agent", "agent",
                  "classify each citation load-bearing vs incidental (the moat)",
                  "citing sentences", f"load-bearing weights: {lb}",
                  evidence=[e.src for e in graph.edges
                            if e.edge_type.value == "cites"]),
        AgentStep(4, "Doubt Propagation", "tool",
                  "propagate doubt from doubtful nodes (graph math)",
                  "load-bearing weights",
                  "doubt propagated; retracted nodes stay fully doubted",
                  evidence=[n.id for n in graph.nodes.values()
                            if n.doubt.point >= 0.6]),
        AgentStep(5, "Contradiction Mining", "tool",
                  "surface contradiction edges as discovery opportunities",
                  "evidence graph",
                  f"{len(contradictions)} contradiction(s)",
                  evidence=[c["against"] for c in contradictions]),
        AgentStep(6, "Gap Detection", "tool",
                  "count missing-evidence items", "evidence graph + hypothesis",
                  f"{gaps['count']} gap(s)", evidence=gaps["gaps"][:3]),
        AgentStep(7, "Hypothesis Agent", "agent",
                  "generate a rule-3-complete, falsifiable hypothesis",
                  "contradictions + grounding", hyp.statement[:80],
                  evidence=list(hyp.supporting_evidence),
                  confidence=hyp.confidence.point,
                  sources=[graph.nodes[n].source for n in hyp.mechanism_path
                           if n in graph.nodes],
                  contradictions=list(hyp.contradicting_evidence),
                  assumptions=[hyp.uncertainty_notes],
                  failure_modes=list(hyp.failure_modes),
                  artifacts=["Hypothesis", "ExperimentPlan"]),
        AgentStep(8, "Experiment Design Agent", "agent",
                  "propose a design with a named kill-condition",
                  "hypothesis", hyp.validation_experiment.perturbation[:70],
                  evidence=[hyp.validation_experiment.kill_condition[:60]],
                  assumptions=[hyp.validation_experiment.effect_size_source],
                  artifacts=["ExperimentPlan (falsifiable kill-condition)"]),
        AgentStep(9, "Statistics + Protocol", "tool",
                  "power analysis + protocol validation (refuses to fabricate n)",
                  "experiment design",
                  f"n/arm={hyp.validation_experiment.required_n_per_arm}; "
                  f"{len(ledger.protocol_warnings)} warning(s)",
                  evidence=[hyp.validation_experiment.effect_size_source[:60]]),
        AgentStep(10, "Reviewer Agent", "agent",
                  "independently challenge the hypothesis (rule 4)",
                  "hypothesis + grounding doubt",
                  f"{review.verdict.value}: confidence "
                  f"{hyp.confidence.point} -> {review.adjusted_confidence.point}",
                  evidence=review.objections,
                  confidence=review.adjusted_confidence.point,
                  contradictions=[review.weakness],
                  artifacts=["ReviewResult"]),
        AgentStep(11, "Evidence Ledger", "tool",
                  "emit the reproducible, content-hashed artifact",
                  "the whole run", f"hash={ledger.graph_hash}",
                  evidence=sources[:4]),
    ]
    return [asdict(s) for s in steps]


def orchestrate(question, graph, reasoner):
    """Run the coordinated pipeline and return (trace, ledger, hyp, review)."""
    ledger, hyp, review = run(question, graph, reasoner)
    trace = build_trace(question, graph, ledger, hyp, review)
    return trace, ledger, hyp, review
