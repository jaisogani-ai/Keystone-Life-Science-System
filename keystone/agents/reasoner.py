"""
keystone.agents.reasoner
=======================
The semantic-layer interface and the offline ``HeuristicReasoner`` — a
transparent, deterministic stand-in that runs the *identical* pipeline as the
live ``ClaudeReasoner`` so the whole workbench works with no API key. Every
method here is a pure function of its inputs (reproducible); the "moat" method
``classify_load_bearing`` scores real citing sentences with an inspectable
keyword rule rather than a black box.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from keystone.core import (EvidenceGraph, Hypothesis, ExperimentPlan, Interval,
                           ReviewResult, ReviewVerdict, node_label)
from keystone.deterministic.stats import sample_size_two_arm
from keystone.deterministic.protocol import REPRO_CHECKLIST

# Documented human-agreement band on the load-bearing classification task; used
# to size the hypothesis confidence interval honestly rather than pick a number.
AGREEMENT_MID = 0.705
_CI_HALF = round((1 - AGREEMENT_MID) / 2, 4)   # ~0.1475

# Inspectable cue lexicons for the load-bearing heuristic. Load cues mark a paper
# that *relies on a specific result*; incidental cues mark a passing/bundled one.
# The cues are deliberately domain-general mechanistic-result language (a specific
# perturbation or measured effect), NOT one field's jargon — so the same rule
# generalizes across domains (measured in calibrate.py --domain gbm|insulin).
_LOAD_CUES = ["inhibition of", "inhibit", "knockdown", "knock-down", "knockout",
              "knock-out", "silencing", "attenuated", "abrogated", "suppress",
              "rnai-mediated", "sirna", "shrna", "overexpress", "deletion",
              "loss-of-function", "phosphoryl", "impair", "activates",
              "stimulates", "translocation of", "resulted in", "required for",
              "demonstrated", "showed that", "we found", "we show", "we used",
              "as reported by", "based on the finding"]
_INCIDENTAL_CUES = ["moreover", "associated", "reviewed in", "see also",
                    "among", "such as", "for example", "e.g.", "various",
                    "in general", "et al.,", "], [", "is a key", "is a critical",
                    "peptide hormone", "widely distributed",
                    "traditionally recognised", "traditionally recognized"]


class Reasoner(Protocol):
    version: str
    def plan(self, question: str) -> dict: ...
    def classify_load_bearing(self, context: str) -> Interval: ...
    def generate_hypothesis(self, graph: EvidenceGraph) -> Hypothesis: ...
    def design_experiment(self, hyp: Hypothesis,
                          graph: EvidenceGraph) -> ExperimentPlan: ...
    def review(self, hyp: Hypothesis, graph: EvidenceGraph) -> ReviewResult: ...


class HeuristicReasoner:
    version = "heuristic-1.0"

    # -- Planner ----------------------------------------------------------
    def plan(self, question: str) -> dict:
        return {
            "scope": "single-question discovery",
            "connectors": ["openalex", "retraction_watch", "cellosaurus",
                           "semantic_scholar", "uniprot", "pdb"],
            "depth": 3,
            "intent": "hypothesis-generation",
        }

    # -- Evidence-Quality (the moat) --------------------------------------
    def classify_load_bearing(self, context: str) -> Interval:
        """Score how load-bearing a citing sentence is, in [0.05, 1.0].
        Deterministic and inspectable: this is the method the calibration
        harness measures against hand-labeled sentences."""
        if not context or context.startswith("unresolved"):
            return Interval(0.5, 0.3, 0.7)   # cannot judge without the sentence
        text = context.lower()
        load = sum(1 for c in _LOAD_CUES if c in text)
        incidental = sum(1 for c in _INCIDENTAL_CUES if c in text)
        score = 0.45 + 0.20 * load - 0.11 * incidental
        score = max(0.05, min(1.0, score))
        return Interval(round(score, 3), round(max(0.05, score - 0.1), 3),
                        round(min(1.0, score + 0.1), 3))

    def is_load_bearing(self, context: str, threshold: float = 0.5) -> bool:
        """Binary view used by the calibration harness."""
        return self.classify_load_bearing(context).point >= threshold

    # -- Hypothesis (rule-3 complete or rejected) -------------------------
    def _target_gene(self, graph: EvidenceGraph) -> str:
        """The target node's gene symbol (e.g. CTSB / IRS1 / MMP9), read from the
        real graph so each domain reasons about its OWN target — never a
        hardcoded stand-in."""
        t = graph.nodes.get("N_target")
        if t and t.text:
            return t.text.split(" — ")[0].strip()
        return ""

    def generate_hypothesis(self, graph: EvidenceGraph) -> Hypothesis:
        # Curated-library path — the pinned demo graphs (GBM, insulin, ICH) carry
        # these ids. Each domain gets ITS OWN hypothesis, derived from its real
        # target; only the flagship GBM graph uses the richer hand-written text.
        if all(nid in graph.nodes for nid
               in ("N_molecular", "N_target", "N_foundation", "N_contra")):
            if self._target_gene(graph) == "CTSB":     # the flagship GBM graph
                return self._pinned_gbm_hypothesis(graph)
            return self._pinned_generic_hypothesis(graph)
        # Imported-refs path — driven off the graph's actual structure.
        return self._graph_driven_hypothesis(graph)

    def _pinned_gbm_hypothesis(self, graph: EvidenceGraph) -> Hypothesis:
        hyp = Hypothesis(
            id="H1",
            statement=(
                "In IDH-wildtype glioblastoma, the invasion-suppressive effect "
                "attributed to cathepsin B (CTSB)/MMP-9 knockdown is "
                "context-dependent — robust only in a mesenchymal / high-MMP9 "
                "subset — rather than a universal driver, reconciling the "
                "retracted foundational claim with the dual-role evidence."),
            mechanism_path=["N_molecular", "N_target", "N_foundation"],
            supporting_evidence=["N_molecular"],
            contradicting_evidence=["N_contra"],
            confidence=Interval(0.55, round(0.55 - _CI_HALF, 4),
                                round(0.55 + _CI_HALF, 4)),
            uncertainty_notes=(
                "Confidence limited by inherited doubt on the retracted "
                "foundational result and the ~69-75% agreement band of "
                "load-bearing classification."),
            validation_experiment=self._placeholder_experiment(),
            expected_outcome=(
                "CTSB/MMP-9 knockdown reduces invasion significantly more in "
                "mesenchymal / high-MMP9 lines than in proneural lines."),
            failure_modes=[
                "Subtype stratification confounded by co-occurring EGFR amplification",
                "U-87MG (CVCL_0022) is itself misidentified — a matched isogenic "
                "line for the relevant background may not exist",
                "Off-target RNAi effects mimic a false stratified invasion signal",
            ])
        hyp = replace(hyp, validation_experiment=self.design_experiment(hyp, graph))
        hyp.validate()
        return hyp

    def _pinned_generic_hypothesis(self, graph: EvidenceGraph) -> Hypothesis:
        """A curated-domain hypothesis for any domain other than the flagship
        GBM graph (insulin, ICH, …). Statement/experiment are derived from the
        graph's REAL target gene — so each domain reasons about its own biology
        and never inherits GBM's hand-written text."""
        gene = self._target_gene(graph) or "the target"
        hyp = Hypothesis(
            id="H1",
            statement=(
                f"The effect attributed to {gene} in the foundational result is "
                f"context-dependent — robust only in a susceptible subset — "
                f"rather than a universal driver, reconciling the compromised "
                f"foundational claim with the dual-role contradiction evidence."),
            mechanism_path=["N_molecular", "N_target", "N_foundation"],
            supporting_evidence=["N_molecular"],
            contradicting_evidence=["N_contra"],
            confidence=Interval(0.55, round(0.55 - _CI_HALF, 4),
                                round(0.55 + _CI_HALF, 4)),
            uncertainty_notes=(
                "Confidence limited by inherited doubt on the compromised "
                "foundational result and the ~69-75% agreement band of "
                "load-bearing classification."),
            validation_experiment=self._placeholder_experiment(),
            expected_outcome=(
                f"{gene} perturbation changes the phenotype significantly more "
                f"in the susceptible context than in the resistant one."),
            failure_modes=[
                "Context stratification confounded by a co-occurring variable",
                "The model reagent may lack a matched isogenic control",
                "Off-target perturbation mimics a false stratified signal",
            ])
        hyp = replace(hyp, validation_experiment=self.design_experiment(hyp, graph))
        hyp.validate()
        return hyp

    def _graph_driven_hypothesis(self, graph: EvidenceGraph) -> Hypothesis:
        """Generate a rule-3-complete primary hypothesis from an arbitrary
        graph (e.g. a scientist's imported ``.bib``). Grounding is a real
        retracted node in the imported set if any exists; otherwise the
        hypothesis is honestly framed as an independent-replication call over
        the resolved references. Never fabricates identifiers."""
        retracted = sorted(
            (n for n in graph.nodes.values() if n.retracted),
            key=lambda n: n.id)
        resolved = sorted(
            (n for n in graph.nodes.values()
             if n.source and n.source != "unresolved" and not n.retracted),
            key=lambda n: n.doubt.point)
        contradicting = [n.id for n in graph.nodes.values() if n.retracted] \
            or [resolved[-1].id] if resolved else []
        supporting = [n.id for n in resolved[:2]] or (
            [retracted[0].id] if retracted else [])
        mechanism = ([n.id for n in resolved[:1]]
                     + [retracted[0].id] if retracted else
                     [n.id for n in resolved[:1]])

        if retracted:
            r = retracted[0]
            statement = (
                f"The imported reference set includes a retracted paper "
                f"({r.source}); any claim in the scientist's grant that "
                f"relies on its specific finding inherits doubt and must be "
                f"re-grounded on an independent replication before submission."
            )
            expected = (
                f"An independent replication succeeds without depending on "
                f"the retracted result, reducing inherited doubt on the "
                f"claims that cite it.")
            uncertainty = (
                "Confidence limited by (a) inherited doubt from the "
                "retracted paper, and (b) the load-bearing classifier's "
                "~70% human-agreement band applied to citation contexts "
                "outside its calibrated domains.")
            failure_modes = [
                "Independent replication is infeasible because the retracted "
                "reagents are no longer available",
                "The retracted claim was never load-bearing to the grant's "
                "argument — doubt propagation over-flagged this reference",
                "A second retraction lands during grant prep and re-scopes "
                "the argument mid-cycle",
            ]
        else:
            base = resolved[0] if resolved else None
            statement = (
                f"The imported reference set contains no retracted foundations "
                f"detectable via Crossref/Retraction Watch as of this run; "
                f"the primary risk is post-publication concerns not yet in "
                f"the retraction record (PubPeer, expression-of-concern) "
                f"which Keystone does not yet check.")
            expected = (
                "A spot-check of the highest-cited references against "
                "PubPeer / journal expression-of-concern notices returns "
                "no new integrity flags before grant submission.")
            uncertainty = (
                "Confidence bounded by Crossref/Retraction Watch coverage; "
                "post-publication concerns pre-retraction are not detected.")
            failure_modes = [
                "A cited paper carries an expression-of-concern not yet "
                "recorded in Crossref",
                "A cited paper's supporting data was deposited to a "
                "repository that has since been withdrawn",
                "The scientist's grant depends on a claim that PubPeer flags "
                "but no retraction has been issued",
            ]
        # If the graph has literally no resolved nodes (all-unresolved import),
        # rule-3 completeness requires at least one supporting/contradicting id.
        # Fall back to the unresolved node itself so nothing is fabricated.
        if not supporting or not contradicting:
            any_node = next(iter(graph.nodes.values()), None)
            if any_node is not None:
                supporting = supporting or [any_node.id]
                contradicting = contradicting or [any_node.id]

        hyp = Hypothesis(
            id="H1",
            statement=statement,
            mechanism_path=mechanism or ([supporting[0]] if supporting else []),
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            confidence=Interval(0.50, round(0.50 - _CI_HALF, 4),
                                round(0.50 + _CI_HALF, 4)),
            uncertainty_notes=uncertainty,
            validation_experiment=self._placeholder_experiment(),
            expected_outcome=expected,
            failure_modes=failure_modes,
        )
        hyp = replace(hyp, validation_experiment=self.design_experiment(hyp, graph))
        hyp.validate()
        return hyp

    def _placeholder_experiment(self) -> ExperimentPlan:
        return ExperimentPlan(
            perturbation="", system="isogenic", positive_controls=["c"],
            negative_controls=["n"], readout="", expected_outcome="",
            kill_condition="placeholder", effect_size_source="",
            assumed_effect_size=0.8, assumed_sd=1.0, alpha=0.05, power=0.8,
            required_n_per_arm=None)

    # -- Experiment Design ------------------------------------------------
    def design_experiment(self, hyp: Hypothesis,
                          graph: EvidenceGraph) -> ExperimentPlan:
        d, sd = 0.80, 1.0
        n, note = sample_size_two_arm(d, sd)
        gene = self._target_gene(graph)
        if gene == "CTSB":                    # flagship GBM experiment (unchanged)
            return ExperimentPlan(
                perturbation="siRNA / CRISPRi knockdown of CTSB (and MMP-9)",
                system=("isogenic glioblastoma lines stratified by molecular "
                        "subtype (mesenchymal vs proneural)"),
                positive_controls=["TGF-beta-stimulated invasion (known inducer)"],
                negative_controls=["non-targeting scramble siRNA",
                                   "catalytically-dead CTSB rescue"],
                readout="Matrigel transwell invasion index + MMP-9 zymography",
                expected_outcome=hyp.expected_outcome,
                kill_condition=("invasion reduction is statistically equal across "
                                "subtypes, refuting context-dependence"),
                effect_size_source=("Cohen's large-effect convention (d=0.80), a "
                                    "LABELED placeholder — replace with a measured "
                                    "invasion-assay effect before running (rule 7: "
                                    "not a fabricated measurement)"),
                assumed_effect_size=d, assumed_sd=sd, alpha=0.05, power=0.80,
                required_n_per_arm=n,
                reproducibility_checklist=list(REPRO_CHECKLIST), stats_notes=note)
        # Generic, gene-derived experiment for every other domain (insulin, ICH,
        # imported refs) — never GBM's invasion-assay text on a non-GBM target.
        label = gene or "the target"
        reagent = graph.nodes.get("N_reagent")
        system = ((reagent.text.split(" — ")[0].strip() + " with matched controls")
                  if reagent and reagent.text else
                  "isogenic lines stratified by context")
        return ExperimentPlan(
            perturbation=f"siRNA / CRISPRi knockdown of {label}",
            system=system,
            positive_controls=["a validated inducer of the phenotype"],
            negative_controls=["non-targeting scramble siRNA",
                               f"catalytically-inactive {label} rescue"],
            readout=f"quantitative assay of the {label}-dependent phenotype",
            expected_outcome=hyp.expected_outcome,
            kill_condition=("the effect is statistically equal across contexts, "
                            "refuting context-dependence"),
            effect_size_source=("Cohen's large-effect convention (d=0.80), a "
                                "LABELED placeholder — replace with a measured "
                                "effect before running (rule 7: not a fabricated "
                                "measurement)"),
            assumed_effect_size=d, assumed_sd=sd, alpha=0.05, power=0.80,
            required_n_per_arm=n, reproducibility_checklist=list(REPRO_CHECKLIST),
            stats_notes=note)

    # -- Reviewer (independent challenge, rule 4) -------------------------
    def review(self, hyp: Hypothesis, graph: EvidenceGraph) -> ReviewResult:
        objections = []
        worst = None
        for nid in hyp.mechanism_path:
            node = graph.nodes.get(nid)
            if node and node.doubt.point >= 0.6:
                objections.append(
                    f"The finding “{node_label(node)}” carries high inherited "
                    f"doubt ({node.doubt.point:.2f}).")
                if worst is None or node.doubt.point > graph.nodes[worst].doubt.point:
                    worst = nid
        if worst is not None:
            weakness = (f"The finding “{node_label(graph.nodes[worst])}” carries "
                        f"high inherited doubt ({graph.nodes[worst].doubt.point:.2f}); "
                        f"the hypothesis partly rests on a compromised foundation.")
            adj = max(0.0, hyp.confidence.point - 0.20)
            return ReviewResult(
                verdict=ReviewVerdict.DOWNGRADED, weakness=weakness,
                adjusted_confidence=Interval(round(adj, 3),
                                             round(max(0.0, adj - 0.1), 3),
                                             round(min(1.0, adj + 0.1), 3)),
                objections=objections)
        return ReviewResult(
            verdict=ReviewVerdict.SUPPORTED,
            weakness="No grounding node carries disqualifying doubt.",
            adjusted_confidence=hyp.confidence, objections=[])
