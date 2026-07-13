"""
keystone.orchestrator
====================
Explicit multi-agent orchestration, in the Claude Science style: a central
Planner coordinates specialist agents, each verified against deterministic tools,
and a Principal Investigator synthesizes them into ONE evidence-backed
recommendation at the end. This makes the "AI as assistant, not centerpiece"
principle concrete — every semantic agent's output is checked by, or handed to, a
deterministic tool that produces the actual numbers.

The orchestrator does not re-implement the loop; it runs it and records a
faithful, provenance-bearing TRACE of who did what. Each seat — agent OR tool —
exposes the SAME structured scientific artifact (never chat):

    Evidence · Source datasets · Supporting publications · Contradicting
    evidence · Assumptions · Remaining uncertainty · Confidence · Proposed
    experiment · Failure modes · Expected information gain · Provenance

Every field is a projection of an object the engine already produced; a field is
empty only when the underlying evidence is honestly absent (e.g. no dataset node
is wired), never to hide a fabrication. The Reviewer additionally exposes the
assumption it challenges and the confidence it removes (before -> after -> delta),
so a scientist can WATCH confidence evolve as the evidence is criticised.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field

from keystone.core import node_label
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
    # the same structured scientific artifact every seat exposes — narration of
    # real objects, no second schema per agent type. Empty only when the evidence
    # is honestly absent, never to mask a fabrication.
    sources: list = field(default_factory=list)
    source_datasets: list = field(default_factory=list)
    supporting_publications: list = field(default_factory=list)
    contradictions: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    remaining_uncertainty: str = ""
    proposed_experiment: str = ""
    failure_modes: list = field(default_factory=list)
    information_gain: float | None = None
    provenance: list = field(default_factory=list)
    artifacts: list = field(default_factory=list)
    # Reviewer-only: the challenge made explicit and the confidence removed.
    challenged_assumption: str = ""
    why_disagrees: str = ""
    confidence_before: float | None = None
    confidence_after: float | None = None
    confidence_delta: float | None = None


# --- projection helpers (pure; every value is read off the graph/ledger) -----
def _doi_sources(graph, node_ids) -> list:
    """Real publication DOIs backing the given nodes (paper / molecular results)."""
    out = []
    for nid in node_ids:
        n = graph.nodes.get(nid)
        if n and n.source and n.source != "unresolved" and (
                n.source.startswith("10.") or n.source.startswith("DOI:")):
            out.append(n.source)
    return sorted(set(out))


def _dataset_sources(graph) -> list:
    """Sources of DATASET nodes. Honestly empty when none is wired (this is a
    real finding the Gap Engine also flags — never padded with a placeholder)."""
    return sorted({n.source for n in graph.nodes.values()
                   if n.node_type.value == "dataset"
                   and n.source and n.source != "unresolved"})


def _provenance(graph, node_ids, ledger) -> list:
    """id:source pairs for the cited nodes, plus the reproducibility hash."""
    prov = [f"{nid}:{graph.nodes[nid].source}"
            for nid in node_ids if nid in graph.nodes]
    prov.append(f"graph_hash:{ledger.graph_hash}")
    prov.append(f"reasoner:{ledger.reasoner_version}")
    return prov


def _experiment_summary(ep) -> str:
    n = ep.required_n_per_arm
    return (f"{ep.perturbation} in {ep.system} — falsify if: "
            f"{ep.kill_condition}"
            + (f"; n/arm {n}" if n is not None else "; n withheld (ungrounded effect size)"))


def _primary_eig(decision) -> float | None:
    """The primary hypothesis's expected information gain, when the decision
    ranking is available (front door). None in the standalone pipeline view."""
    if not decision:
        return None
    ranked = decision.get("competing_hypotheses") or []
    primary = next((c for c in ranked if c.get("kind") == "primary"),
                   ranked[0] if ranked else None)
    if primary:
        return primary.get("information_gain", {}).get("value")
    return None


def build_trace(question, graph, ledger, hyp, review, decision=None) -> list[dict]:
    """Reconstruct the faithful orchestration trace from a completed run. Every
    seat exposes the full structured artifact. ``decision`` (optional) lets the
    Hypothesis + PI seats cite the ranked recommendation / EIG; without it those
    fields are honestly labelled as not-ranked-in-this-view."""
    lb = {f"{e.src}->{e.dst}": round(e.load_bearing.point, 2) for e in graph.edges
          if e.edge_type.value in ("cites", "depends_on")}
    # human-readable rendering of the load-bearing weights for the trace — names
    # the findings, never internal node ids (spec: human-readable nodes only)
    def _lbl(nid: str) -> str:
        return node_label(graph.nodes[nid], 30) if nid in graph.nodes else "a source"
    lb_human = "; ".join(
        f"“{_lbl(k.split('->')[0])}” → “{_lbl(k.split('->')[1])}”: {v:.2f}"
        for k, v in sorted(lb.items(), key=lambda kv: -kv[1])[:3]) or \
        "no scored citation links"
    contradictions = mine_contradictions(graph)
    gaps = detect_gaps(hyp, review, graph)
    sources = sorted({n.source for n in graph.nodes.values()
                      if n.source and n.source != "unresolved"})

    ep = hyp.validation_experiment
    grounding = list(hyp.mechanism_path)
    ds = _dataset_sources(graph)
    pubs = _doi_sources(graph, grounding)
    eig = _primary_eig(decision)
    exp = _experiment_summary(ep)
    prov = _provenance(graph, grounding, ledger)
    high_doubt = sorted(
        (nid for nid in grounding
         if nid in graph.nodes and graph.nodes[nid].doubt.point >= 0.6),
        key=lambda nid: -graph.nodes[nid].doubt.point)

    conf_before = round(hyp.confidence.point, 3)
    conf_after = round(review.adjusted_confidence.point, 3)
    conf_delta = round(conf_after - conf_before, 3)

    steps = [
        AgentStep(
            1, "Scientific Planner", "agent",
            "decompose the question into a bounded plan",
            question[:80],
            f"intent={ledger.plan.get('intent')}, "
            f"connectors={len(ledger.plan.get('connectors', []))}",
            evidence=[question[:60]],
            assumptions=[f"scope: {ledger.plan.get('scope', 'single question')}",
                         f"depth: {ledger.plan.get('depth', '?')}"],
            remaining_uncertainty="the plan is a scope commitment, not a result; "
            "every downstream number is produced by a deterministic tool",
            provenance=[f"plan.connectors:{','.join(ledger.plan.get('connectors', []))[:60]}"],
            artifacts=["Plan"]),
        AgentStep(
            2, "Connectors", "tool",
            "collect real evidence into the graph",
            "planned connectors",
            f"{len(graph.nodes)} nodes, {len(graph.edges)} edges",
            evidence=sources[:8],
            source_datasets=ds,
            supporting_publications=_doi_sources(graph, list(graph.nodes)),
            remaining_uncertainty=("no primary dataset (GEO/SRA) connector wired — "
                                   "dataset evidence is honestly absent")
            if not ds else "",
            provenance=[f"sources:{len(sources)}", f"graph_hash:{ledger.graph_hash}"],
            artifacts=["EvidenceGraph"]),
        AgentStep(
            3, "Evidence-Quality Agent", "agent",
            "classify each citation load-bearing vs incidental (the moat)",
            "citing sentences", f"load-bearing weights — top links: {lb_human}",
            evidence=[e.src for e in graph.edges if e.edge_type.value == "cites"],
            supporting_publications=_doi_sources(
                graph, [e.src for e in graph.edges if e.edge_type.value == "cites"]),
            assumptions=["load-bearing cue lexicon; ~70.5% human-agreement band"],
            remaining_uncertainty="unresolved citing sentences cannot be scored and "
            "default to 0.5 (shown as such)",
            provenance=[f"reasoner:{ledger.reasoner_version}"],
            artifacts=["load-bearing Interval per edge"]),
        AgentStep(
            4, "Doubt Propagation", "tool",
            "propagate doubt from doubtful nodes (graph math)",
            "load-bearing weights",
            "doubt propagated; retracted nodes stay fully doubted",
            evidence=[n.id for n in graph.nodes.values() if n.doubt.point >= 0.6],
            contradictions=[f"{nid} inexcusable (post-retraction reliance)"
                            for nid, n in graph.nodes.items() if n.inexcusable],
            assumptions=["doubt = 1-(1-prior)*prod(1-transfer); transfer<=0.60*weight"],
            provenance=[f"{nid}:doubt={graph.nodes[nid].doubt.point:.2f}"
                        for nid in high_doubt] or [f"graph_hash:{ledger.graph_hash}"],
            artifacts=["doubt Interval per node"]),
        AgentStep(
            5, "Contradiction Mining", "tool",
            "surface contradiction edges as discovery opportunities",
            "evidence graph", f"{len(contradictions)} contradiction(s)",
            evidence=[c["against"] for c in contradictions],
            contradictions=[f"{c['claim']} contradicts {c['against']}"
                            f"{' (retracted)' if c['against_retracted'] else ''}"
                            for c in contradictions],
            supporting_publications=_doi_sources(
                graph, [c["claim"] for c in contradictions]),
            provenance=[f"graph_hash:{ledger.graph_hash}"],
            artifacts=["contradiction records"]),
        AgentStep(
            6, "Gap Detection", "tool",
            "count missing-evidence items", "evidence graph + hypothesis",
            f"{gaps['count']} gap(s)", evidence=gaps["gaps"][:3],
            remaining_uncertainty="; ".join(gaps["gaps"][:3]),
            provenance=[f"graph_hash:{ledger.graph_hash}"],
            artifacts=["gap list"]),
        AgentStep(
            7, "Hypothesis Agent", "agent",
            "generate a rule-3-complete, falsifiable hypothesis",
            "contradictions + grounding", hyp.statement[:80],
            evidence=list(hyp.supporting_evidence),
            confidence=conf_before,
            sources=[graph.nodes[n].source for n in grounding if n in graph.nodes],
            source_datasets=ds,
            supporting_publications=pubs,
            contradictions=list(hyp.contradicting_evidence),
            assumptions=[hyp.uncertainty_notes],
            remaining_uncertainty=hyp.uncertainty_notes,
            proposed_experiment=exp,
            failure_modes=list(hyp.failure_modes),
            information_gain=eig,
            provenance=prov,
            artifacts=["Hypothesis", "ExperimentPlan"]),
        AgentStep(
            8, "Experiment Design Agent", "agent",
            "propose a design with a named kill-condition",
            "hypothesis", ep.perturbation[:70],
            evidence=[ep.kill_condition[:60]],
            assumptions=[ep.effect_size_source],
            remaining_uncertainty="effect size is a labelled placeholder until a "
            "measured invasion-assay effect replaces it (rule 7)",
            proposed_experiment=exp,
            failure_modes=list(hyp.failure_modes[:2]),
            provenance=[f"n/arm:{ep.required_n_per_arm}", f"alpha:{ep.alpha}",
                        f"power:{ep.power}"],
            artifacts=["ExperimentPlan (falsifiable kill-condition)"]),
        AgentStep(
            9, "Statistics + Protocol", "tool",
            "power analysis + protocol validation (refuses to fabricate n)",
            "experiment design",
            f"n/arm={ep.required_n_per_arm}; "
            f"{len(ledger.protocol_warnings)} warning(s)",
            evidence=[ep.effect_size_source[:60]],
            assumptions=[f"two-arm, alpha={ep.alpha}, power={ep.power}"],
            contradictions=list(ledger.protocol_warnings),
            provenance=[f"n/arm:{ep.required_n_per_arm}"],
            artifacts=["required sample size", "protocol warnings"]),
        AgentStep(
            10, "Reviewer Agent", "agent",
            "independently challenge the hypothesis and remove unearned confidence",
            "hypothesis + grounding doubt",
            f"{review.verdict.value}: confidence {conf_before} -> {conf_after} "
            f"(delta {conf_delta:+.3f})",
            evidence=review.objections,
            confidence=conf_after,
            contradictions=[review.weakness],
            challenged_assumption=(
                f"the finding “{node_label(graph.nodes[high_doubt[0]])}” carries "
                f"{graph.nodes[high_doubt[0]].doubt.point:.2f} inherited doubt"
                if high_doubt else "no grounding node carries disqualifying doubt"),
            why_disagrees=review.weakness,
            confidence_before=conf_before,
            confidence_after=conf_after,
            confidence_delta=conf_delta,
            remaining_uncertainty=hyp.uncertainty_notes,
            provenance=_provenance(graph, high_doubt or grounding, ledger),
            artifacts=["ReviewResult (verdict + adjusted confidence)"]),
        AgentStep(
            11, "Evidence Ledger", "tool",
            "emit the reproducible, content-hashed artifact",
            "the whole run", f"hash={ledger.graph_hash}",
            evidence=sources[:4],
            supporting_publications=_doi_sources(graph, list(graph.nodes)),
            source_datasets=ds,
            provenance=[f"graph_hash:{ledger.graph_hash}",
                        f"reasoner:{ledger.reasoner_version}",
                        f"sources:{len(sources)}"],
            artifacts=["Ledger (JSON, reproducible)"]),
        _pi_step(question, graph, ledger, hyp, review, decision,
                 grounding, ds, pubs, exp, prov, eig, conf_before, conf_after,
                 conf_delta, contradictions),
    ]
    return [asdict(s) for s in steps]


def _pi_step(question, graph, ledger, hyp, review, decision, grounding, ds, pubs,
             exp, prov, eig, conf_before, conf_after, conf_delta,
             contradictions) -> AgentStep:
    """The Principal Investigator seat: synthesize the specialists into ONE
    evidence-backed recommendation. It introduces NO new number — it composes the
    Hypothesis Agent's proposal, the Reviewer's adjusted confidence, and (when the
    decision board is available) the ranked #1 with its EIG. This is the
    coordinator's closing synthesis, not a new specialist (rule: add no agents)."""
    if decision:
        rec = decision.get("recommendation", {})
        why = ", ".join(rec.get("why_first", []) or []) or "highest weighted priority"
        output = (f"RUN {rec.get('hypothesis_id', 'H1')} ({rec.get('kind', 'primary')}): "
                  f"priority {rec.get('priority_score')}, EIG {rec.get('information_gain')}, "
                  f"reviewed confidence {conf_after} (was {conf_before}); "
                  f"chosen for {why}")
        info_gain = rec.get("information_gain", eig)
        prop = _experiment_summary(hyp.validation_experiment)
        assumptions = [f"over the runner-up: {rec.get('over_alternatives', 'n/a')}"]
    else:
        output = (f"RUN the primary hypothesis: reviewed confidence {conf_after} "
                  f"(was {conf_before}, delta {conf_delta:+.3f}); falsify by "
                  f"{hyp.validation_experiment.kill_condition[:70]}")
        info_gain = None
        prop = exp
        assumptions = ["full competing-hypothesis ranking is shown on the "
                       "decision board; this pipeline view synthesizes the primary"]
    return AgentStep(
        12, "Principal Investigator", "agent",
        "synthesize the specialists into one evidence-backed recommendation",
        "all specialist artifacts", output,
        evidence=list(hyp.supporting_evidence) + grounding,
        confidence=conf_after,
        sources=[graph.nodes[n].source for n in grounding if n in graph.nodes],
        source_datasets=ds,
        supporting_publications=pubs,
        contradictions=[c["claim"] + " vs " + c["against"] for c in contradictions],
        assumptions=assumptions,
        remaining_uncertainty=hyp.uncertainty_notes,
        proposed_experiment=prop,
        failure_modes=list(hyp.failure_modes),
        information_gain=info_gain,
        confidence_before=conf_before,
        confidence_after=conf_after,
        confidence_delta=conf_delta,
        provenance=prov,
        artifacts=["Recommendation (human-gated)"])


def orchestrate(question, graph, reasoner, decision=None):
    """Run the coordinated pipeline and return (trace, ledger, hyp, review)."""
    ledger, hyp, review = run(question, graph, reasoner)
    trace = build_trace(question, graph, ledger, hyp, review, decision)
    return trace, ledger, hyp, review
