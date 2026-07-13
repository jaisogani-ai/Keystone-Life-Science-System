"""
keystone.deterministic.hypothesis_space
=======================================
Generate a FAMILY of competing hypotheses from the evidence graph — not one.
Each candidate is grounded in a REAL graph element (a retracted node, a
contradiction edge, a doubtful reagent, the target, a molecular result), so the
space is defensible, not brainstormed. Deterministic; the semantic ClaudeReasoner
can enrich the primary statement live, but the competing set is derived
structurally so it is reproducible and needs no LLM (rule 7).

A scientist chooses among these. The decision board (decision_metrics.py) scores
them; the portfolio (experiment_portfolio.py) buckets their experiments.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from keystone.core import EvidenceGraph, ExperimentPlan, NodeType
from keystone.deterministic.stats import sample_size_two_arm


def _find_by_type(graph: EvidenceGraph, node_type: NodeType):
    """Return graph nodes of the requested type, ordered by lowest doubt first
    (most trusted first). Empty list is honest — the imported graph doesn't
    contain nodes of this type, so hypotheses that require them are simply
    skipped rather than fabricated against a stand-in."""
    return sorted((n for n in graph.nodes.values() if n.node_type == node_type),
                  key=lambda n: n.doubt.point)


def _name(node) -> str:
    """A short human-readable name for a node — used in hypothesis prose so the
    statement reads 'the retracted cathepsin B paper', never 'N_foundation'."""
    if node is None:
        return "the source"
    t = (node.text or "").split(" — ")[0].strip()
    t = t.replace("RETRACTED ARTICLE:", "").strip()
    return (t[:52] + "…") if len(t) > 53 else (t or getattr(node, "id", "the source"))


@dataclass(frozen=True)
class CandidateHypothesis:
    id: str
    kind: str            # primary | null | reagent_confound | alternative |
                         # translational | druggability | biomarker
    statement: str
    grounds_on: str      # the real graph element this hypothesis interrogates
    supporting: list
    contradicting: list
    mechanism_path: list
    experiment: ExperimentPlan
    assumptions: list = field(default_factory=list)
    failure_modes: list = field(default_factory=list)


def _experiment(perturbation: str, system: str, kill: str, effect: float,
                controls_pos: list, controls_neg: list, readout: str) -> ExperimentPlan:
    n, note = sample_size_two_arm(effect, 1.0)
    return ExperimentPlan(
        perturbation=perturbation, system=system,
        positive_controls=controls_pos, negative_controls=controls_neg,
        readout=readout, expected_outcome="see hypothesis",
        kill_condition=kill,
        effect_size_source=f"assumed Cohen's d={effect} (labeled planning "
                           f"assumption — replace with a measured prior)",
        assumed_effect_size=effect, assumed_sd=1.0, alpha=0.05, power=0.80,
        required_n_per_arm=n, stats_notes=note)


def generate_candidates(graph: EvidenceGraph, primary,
                        drug_info: dict | None = None) -> list[CandidateHypothesis]:
    """Return the competing hypotheses. ``primary`` is the reasoner's Hypothesis
    (kind='primary'); the rest are derived from graph structure.

    Nodes are looked up by ``NodeType`` (not by hardcoded id) so this function
    works on any evidence graph — the curated demo libraries or a scientist's
    imported ``.bib``. Hypotheses whose grounding is absent from the graph are
    silently skipped rather than fabricated against a stand-in."""
    targets = _find_by_type(graph, NodeType.TARGET)
    target = targets[0] if targets else None
    gene = (target.text.split(" — ")[0] if target else "the target")
    cands: list[CandidateHypothesis] = []

    # 1. Primary — the reasoner's hypothesis (context-dependence / reconciliation)
    cands.append(CandidateHypothesis(
        id="H1", kind="primary", statement=primary.statement,
        grounds_on="contradiction + grounding nodes",
        supporting=list(primary.supporting_evidence),
        contradicting=list(primary.contradicting_evidence),
        mechanism_path=list(primary.mechanism_path),
        experiment=primary.validation_experiment,
        assumptions=["the recorded contradiction is real, not a measurement artifact"],
        failure_modes=list(primary.failure_modes)))

    # 2. Null / artifact — grounded in any retracted node that is relied upon
    retracted = [n for n in graph.nodes.values() if n.retracted]
    if retracted:
        r = sorted(retracted, key=lambda n: n.id)[0]
        cands.append(CandidateHypothesis(
            id="H2", kind="null", grounds_on=r.id,
            statement=(f"NULL: the reported effect is an artifact of the "
                       f"compromised foundation ({_name(r)}); a clean, independent "
                       f"replication shows no {gene}-dependent effect."),
            supporting=[], contradicting=list(primary.supporting_evidence),
            mechanism_path=[r.id],
            experiment=_experiment(
                f"independent replication of the {gene} perturbation, blind to "
                f"the retracted result",
                "two independent labs, pre-registered", effect=0.8,
                kill="the effect replicates robustly across both labs "
                     "(refuting the artifact hypothesis)",
                controls_pos=["known positive perturbation"],
                controls_neg=["non-targeting control"],
                readout="pre-registered primary readout"),
            assumptions=["a clean replication is feasible without the retracted reagents"],
            failure_modes=["publication bias hides prior failed replications"]))

    # 3. Reagent confound — grounded in a flagged/doubtful reagent (if any)
    reagents = _find_by_type(graph, NodeType.REAGENT)
    reagent = next((r for r in reagents
                    if r.meta.get("problematic") or r.doubt.point >= 0.35),
                   None)
    if reagent:
        cands.append(CandidateHypothesis(
            id="H3", kind="reagent_confound", grounds_on=reagent.id,
            statement=(f"CONFOUND: the effect is driven by the identity problem in "
                       f"{reagent.text.split(' — ')[0]}, not by {gene}; it "
                       f"disappears in an authenticated isogenic line."),
            supporting=[], contradicting=list(primary.supporting_evidence),
            mechanism_path=[reagent.id],
            experiment=_experiment(
                f"{gene} perturbation in an STR-authenticated isogenic panel",
                "isogenic, STR-authenticated lines", effect=0.8,
                kill="the effect persists in the authenticated line "
                     "(refuting the reagent-confound hypothesis)",
                controls_pos=["authenticated parental line"],
                controls_neg=["scramble in the same authenticated line"],
                readout="matched invasion / functional assay"),
            assumptions=["an authenticated line for the relevant background exists"],
            failure_modes=["no authenticated line matches the original background"]))

    # 4. Alternative mechanism — grounded in each contradiction edge
    contra_edges = [e for e in graph.edges if e.edge_type.value == "contradicts"]
    for i, e in enumerate(contra_edges[:2]):
        alt = graph.nodes.get(e.src)
        cands.append(CandidateHypothesis(
            id=f"H4{'' if i == 0 else chr(97+i)}", kind="alternative",
            grounds_on=f"{e.src}->{e.dst}",
            statement=(f"ALTERNATIVE: the mechanism in {_name(alt)} is primary; "
                       f"blocking it — not {gene} — abolishes the phenotype."),
            supporting=[e.src], contradicting=list(primary.supporting_evidence),
            mechanism_path=[e.src],
            experiment=_experiment(
                f"epistasis: block the mechanism in {_name(alt)} with and without "
                f"{gene} perturbation",
                "isogenic lines, 2x2 factorial", effect=0.7,
                kill=f"blocking the mechanism in {_name(alt)} does not change the "
                     f"{gene} effect (refuting the alternative-mechanism hypothesis)",
                controls_pos=["single-pathway blockade"],
                controls_neg=["vehicle"], readout="factorial functional readout"),
            assumptions=["a specific inhibitor of the alternative mechanism exists"],
            failure_modes=["the two mechanisms are not separable"]))

    # 5. Translational — grounded in the target
    if target:
        cands.append(CandidateHypothesis(
            id="H5", kind="translational", grounds_on=target.id,
            statement=(f"TRANSLATIONAL: modulating {gene} improves outcome in a "
                       f"molecularly-stratified subset in vivo."),
            supporting=list(primary.supporting_evidence), contradicting=[],
            mechanism_path=[target.id],
            experiment=_experiment(
                f"{gene} modulation in subtype-stratified patient-derived "
                f"xenografts",
                "PDX, subtype-stratified", effect=0.6,
                kill="no survival/functional benefit in any stratum "
                     "(refuting translational value)",
                controls_pos=["standard-of-care arm"],
                controls_neg=["vehicle arm"],
                readout="survival + functional endpoint"),
            assumptions=["subtype-representative PDX models are available"],
            failure_modes=["PDX does not recapitulate the human microenvironment"]))

    # 6. Druggability — grounded in a real ChEMBL zero-drug finding
    if drug_info and drug_info.get("resolved") and drug_info.get("count") == 0 and target:
        cands.append(CandidateHypothesis(
            id="H6", kind="druggability", grounds_on=f"chembl:{gene}",
            statement=(f"DRUGGABILITY: {gene} is currently undrugged (0 approved "
                       f"mechanisms in ChEMBL); causality must be tested with a "
                       f"tool compound before any clinical claim."),
            supporting=[target.id], contradicting=[],
            mechanism_path=[target.id],
            experiment=_experiment(
                f"selective tool-compound inhibition of {gene} with a "
                f"dose-response + genetic rescue",
                "isogenic lines, dose-response", effect=0.8,
                kill="the tool compound has no on-target effect at tolerated doses "
                     "(refuting druggability)",
                controls_pos=["genetic knockdown (positive)"],
                controls_neg=["inactive analog"],
                readout="dose-response functional readout"),
            assumptions=["a selective tool compound exists or can be sourced"],
            failure_modes=["no selective chemical probe is available"]))

    # 7. Biomarker / stratification — grounded in a molecular result
    molecular = [n for n in graph.nodes.values()
                 if n.node_type.value == "molecular_result"]
    if molecular:
        m = sorted(molecular, key=lambda n: n.doubt.point)[0]
        cands.append(CandidateHypothesis(
            id="H7", kind="biomarker", grounds_on=m.id,
            statement=(f"BIOMARKER: response is stratified by a molecular marker "
                       f"({_name(m)}); unstratified trials fail while stratified "
                       f"trials succeed."),
            supporting=[m.id], contradicting=list(primary.contradicting_evidence),
            mechanism_path=[m.id],
            experiment=_experiment(
                "prospective biomarker-stratified randomization",
                "stratified, matched cohorts", effect=0.6,
                kill="response is identical across marker strata "
                     "(refuting the biomarker hypothesis)",
                controls_pos=["marker-high stratum"],
                controls_neg=["marker-low stratum"],
                readout="stratified response rate"),
            assumptions=["the stratifying marker is measurable pre-treatment"],
            failure_modes=["the marker is confounded by a co-occurring alteration"]))

    return cands
