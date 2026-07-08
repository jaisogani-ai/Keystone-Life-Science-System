"""
keystone.reasoning_panel
========================
Reasoning-transparency artifacts. All deterministic projections of the Ledger /
graph — no LLM, no fabricated numbers.

  1. why_panel               : the full reasoning chain behind a hypothesis
  3. future_experiments_tree : decision tree (if positive -> next; if negative ->
                               alternative), grounded in evidence nodes
  5. research_readiness      : HONEST readiness — computed ratios and intervals,
                               never fabricated percentages. Where a dimension
                               cannot be measured this week, it is labeled as a
                               qualitative estimate, not dressed up as a number.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from keystone.core import EvidenceGraph, Hypothesis, ReviewResult
from keystone.deterministic.protocol import REPRO_CHECKLIST


# ---------------------------------------------------------------------------
# 1. "Why did Keystone reach this conclusion?" panel
# ---------------------------------------------------------------------------
def why_panel(hyp: Hypothesis, review: ReviewResult,
              graph: EvidenceGraph) -> dict:
    """Faithful projection of the reasoning chain. Every field is grounded in
    an object that already exists — this panel invents nothing."""
    def describe(node_ids):
        return [{"id": nid,
                 "source": graph.nodes[nid].source if nid in graph.nodes else "?",
                 "doubt": round(graph.nodes[nid].doubt.point, 3)
                          if nid in graph.nodes else None,
                 "text": graph.nodes[nid].text if nid in graph.nodes else nid}
                for nid in node_ids]

    return {
        "hypothesis": hyp.statement,
        "supporting_evidence": describe(hyp.supporting_evidence),
        "contradicting_evidence": describe(hyp.contradicting_evidence),
        "confidence": {"point": hyp.confidence.point,
                       "interval": [hyp.confidence.low, hyp.confidence.high]},
        "reviewer_objection": {"verdict": review.verdict.value,
                               "weakness": review.weakness,
                               "adjusted_confidence": review.adjusted_confidence.point},
        "remaining_uncertainty": hyp.uncertainty_notes,
        "failure_modes": hyp.failure_modes,
        "suggested_next_experiment": {
            "perturbation": hyp.validation_experiment.perturbation,
            "kill_condition": hyp.validation_experiment.kill_condition,
            "required_n_per_arm": hyp.validation_experiment.required_n_per_arm,
        },
    }


# ---------------------------------------------------------------------------
# 3. Future Experiments decision tree
# ---------------------------------------------------------------------------
@dataclass
class ExperimentBranch:
    node_id: str
    description: str
    on_positive: Optional[str]   # id of the next experiment if this succeeds
    on_negative: Optional[str]   # id of the alternative path if this fails
    grounding: list[str]         # evidence node ids this branch references


def future_experiments_tree(hyp: Hypothesis, graph: EvidenceGraph
                            ) -> list[dict]:
    """A grounded decision tree: current hypothesis -> validation experiment ->
    (positive) confirmatory / (negative) alternative hypothesis. Branches
    reference real evidence nodes, so this is a research plan, not decoration."""
    ep = hyp.validation_experiment
    contra = hyp.contradicting_evidence[:1] or ["(none recorded)"]

    branches = [
        ExperimentBranch(
            node_id="E0",
            description=f"Validation experiment: {ep.perturbation} in {ep.system}",
            on_positive="E1_pos", on_negative="E1_neg",
            grounding=hyp.mechanism_path,
        ),
        ExperimentBranch(
            node_id="E1_pos",
            description=("Confirmatory: repeat in an independent isogenic panel + "
                         "rescue experiment (re-express target) to establish "
                         "specificity."),
            on_positive="E2_pos", on_negative="E1_neg",
            grounding=hyp.supporting_evidence,
        ),
        ExperimentBranch(
            node_id="E1_neg",
            description=("Alternative hypothesis: the observed effect is driven by "
                         "the contradicting-evidence mechanism; test that pathway "
                         "instead."),
            on_positive=None, on_negative=None,
            grounding=contra,
        ),
        ExperimentBranch(
            node_id="E2_pos",
            description=("Translational: test the target inhibitor + temozolomide "
                         "combination in patient-derived xenografts stratified by "
                         "MGMT status."),
            on_positive=None, on_negative="E1_neg",
            grounding=hyp.supporting_evidence,
        ),
    ]
    return [asdict(b) for b in branches]


# ---------------------------------------------------------------------------
# 5. Research Readiness — HONEST version
# ---------------------------------------------------------------------------
def research_readiness(hyp: Hypothesis, review: ReviewResult,
                       graph: EvidenceGraph) -> dict:
    """No fabricated percentages. Each dimension is computed, an interval, or an
    explicitly-labeled qualitative estimate with its basis."""

    # Evidence support: mean inverse-doubt of grounding nodes (COMPUTED, with CI).
    grounding = [graph.nodes[n] for n in hyp.mechanism_path if n in graph.nodes]
    if grounding:
        inv = [1.0 - g.doubt.point for g in grounding]
        inv_lo = [1.0 - g.doubt.high for g in grounding]
        inv_hi = [1.0 - g.doubt.low for g in grounding]
        evidence = {
            "metric": "mean inverse-doubt of grounding nodes",
            "value": round(sum(inv) / len(inv), 3),
            "interval": [round(sum(inv_lo) / len(inv_lo), 3),
                         round(sum(inv_hi) / len(inv_hi), 3)],
            "basis": f"{len(grounding)} grounding nodes",
        }
    else:
        evidence = {"metric": "evidence support", "value": None,
                    "basis": "no grounding nodes"}

    # Reproducibility: checklist completion ratio (COMPUTED, real).
    ep = hyp.validation_experiment
    met = 0
    total = len(REPRO_CHECKLIST)
    if ep.positive_controls: met += 1
    if ep.negative_controls: met += 1
    if "isogenic" in ep.system.lower() or "matched" in ep.system.lower(): met += 1
    if ep.required_n_per_arm is not None: met += 1
    if ep.assumed_effect_size is not None: met += 1
    reproducibility = {
        "metric": "reproducibility checklist completion",
        "value": f"{met}/{total} items addressable from current plan",
        "note": "remaining items are wet-lab execution details the scientist logs",
    }

    # Risk: derived from reviewer verdict + confidence interval width (COMPUTED).
    ci_width = hyp.confidence.high - hyp.confidence.low
    if review.verdict.value == "rejected":
        risk = "high"
    elif review.verdict.value == "downgraded" or ci_width > 0.3:
        risk = "medium"
    else:
        risk = "low"

    # Missing evidence: count of open gaps (COMPUTED).
    missing = []
    if ep.assumed_effect_size is None:
        missing.append("grounded effect size for power analysis")
    if not hyp.supporting_evidence:
        missing.append("direct supporting result")
    if not any(graph.nodes[n].node_type.value == "molecular_result"
               for n in hyp.mechanism_path if n in graph.nodes):
        missing.append("independent molecular corroboration")

    # Novelty: HONESTLY UNMEASURED this week — ordinal estimate + explicit basis.
    novelty = {
        "metric": "novelty",
        "estimate": "medium (qualitative)",
        "basis": ("hypothesis resolves a recorded contradiction rather than "
                  "restating consensus"),
        "caveat": ("A quantitative novelty score requires an embedding-similarity "
                   "search against the corpus — NOT computed this week. Shown as a "
                   "qualitative estimate to avoid fabricating a percentage."),
    }

    return {
        "evidence_support": evidence,
        "reproducibility": reproducibility,
        "risk": risk,
        "missing_evidence": {"count": len(missing), "items": missing},
        "novelty": novelty,
        "disclaimer": ("Readiness dimensions are computed from the evidence graph "
                       "or shown as intervals/qualitative estimates. No dimension "
                       "is a fabricated point percentage."),
    }
