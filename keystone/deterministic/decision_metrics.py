"""
keystone.deterministic.decision_metrics
=======================================
Score competing hypotheses on the Scientific Decision Board dimensions and RANK
them — deterministically. Every dimension is one of three honest kinds, never a
fabricated point value (CONTRIBUTING rule 1 / the Novelty precedent):

  computed    - read off the graph (evidence strength, contradiction engagement,
                reviewer confidence)
  estimate    - a transparent parametric model with its assumptions shown
                (information gain, cost, duration) — like the power analysis
  qualitative - an explicit ordinal with its basis (novelty, expected impact)

The priority score is a weighted composite of these, with the weights exposed, so
the ranking is auditable: a PI can see WHY one experiment outranks another.
"""
from __future__ import annotations

import math

from keystone.core import EvidenceGraph

# Priority weights — exposed so the ranking is inspectable, never a black box.
WEIGHTS = {"information_gain": 0.35, "evidence_strength": 0.20,
           "low_cost": 0.15, "low_risk": 0.15, "novelty": 0.15}
_RISK_ORD = {"low": 0.2, "medium": 0.5, "high": 0.85}
_NOV_ORD = {"low": 0.3, "medium": 0.6, "medium-high": 0.75, "high": 0.9}

# Cost model assumptions (planning estimate — a lab replaces these with its rates).
_COST = {"base_usd": 5000, "per_sample_usd": 400,
         "system_multiplier": {"single": 1.5, "isogenic": 2.0,
                               "replication": 3.0, "pdx": 8.0, "clinical": 20.0}}
_TIME = {"base_weeks": 6, "system_weeks": {"single": 1.0, "isogenic": 1.4,
         "replication": 2.0, "pdx": 6.0, "clinical": 26.0}}


def _metric(value, kind: str, basis: str, **extra) -> dict:
    return {"value": value, "kind": kind, "basis": basis, **extra}


def _system_class(system: str) -> str:
    s = system.lower()
    if any(k in s for k in ("clinical", "prospective", "randomiz", "cohort", "patient-derived xeno", "trial")):
        return "clinical"
    if "pdx" in s or "xenograft" in s or "in vivo" in s:
        return "pdx"
    if "replication" in s or "independent lab" in s:
        return "replication"
    if "isogenic" in s or "authenticated" in s or "stratified" in s:
        return "isogenic"
    return "single"


def _reach(graph: EvidenceGraph, node_ids) -> int:
    ids = set(node_ids)
    touched = set()
    for e in graph.edges:
        if e.src in ids or e.dst in ids:
            touched.add(e.src)
            touched.add(e.dst)
    return len(touched | ids)


def _grounding_doubt(graph, node_ids):
    d = [graph.nodes[n].doubt.point for n in node_ids if n in graph.nodes]
    return d


def score_candidate(cand, graph: EvidenceGraph, review, max_reach: int) -> dict:
    doubts = _grounding_doubt(graph, cand.mechanism_path)
    inv = [1 - d for d in doubts]
    evidence_strength = round(sum(inv) / len(inv), 3) if inv else 0.2

    total_contra = sum(1 for e in graph.edges if e.edge_type.value == "contradicts")
    engaged = 1 if (cand.kind == "alternative" or cand.contradicting) else 0
    contradiction_score = round(engaged / max(total_contra, 1), 3) if total_contra else 0.0

    # --- information gain: uncertainty x graph-stakes x decisiveness ---------
    uncertainty = round(sum(doubts) / len(doubts), 3) if doubts else 0.4
    reach = _reach(graph, cand.mechanism_path)
    stakes = round(reach / max(max_reach, 1), 3)
    ep = cand.experiment
    decisive = 1.0 if (ep.kill_condition.strip() and ep.positive_controls
                       and ep.negative_controls) else 0.6
    eig = round(uncertainty * (0.4 + 0.6 * stakes) * decisive, 3)

    # --- cost + duration: parametric planning estimates ----------------------
    sysc = _system_class(ep.system)
    n = ep.required_n_per_arm or 20
    cost = (_COST["base_usd"] + n * 2 * _COST["per_sample_usd"]
            * _COST["system_multiplier"][sysc])
    cost = int(round(cost, -3))
    weeks = int(round(_TIME["base_weeks"] + math.ceil(n / 10)
                      * _TIME["system_weeks"][sysc]))

    # --- risk / difficulty (ordinal, computed) -------------------------------
    max_doubt = max(doubts) if doubts else 0.4
    if max_doubt >= 0.9 or sysc == "clinical" or len(cand.failure_modes) >= 3:
        risk = "high"
    elif max_doubt >= 0.5 or sysc in ("pdx", "replication"):
        risk = "medium"
    else:
        risk = "low"
    difficulty = {"single": "low", "isogenic": "medium", "replication": "medium",
                  "pdx": "high", "clinical": "high"}[sysc]

    # --- reviewer confidence -------------------------------------------------
    if cand.kind == "primary":
        rev_conf = round(review.adjusted_confidence.point, 3)
        rev_basis = f"independent Reviewer verdict: {review.verdict.value}"
    else:
        rev_conf = round(max(0.1, evidence_strength - 0.15 * (max_doubt >= 0.9)), 3)
        rev_basis = "computed proxy from grounding doubt (not independently reviewed)"

    novelty = {"primary": "medium-high", "alternative": "medium-high",
               "null": "low", "reagent_confound": "medium",
               "translational": "medium", "druggability": "medium-high",
               "biomarker": "medium"}.get(cand.kind, "medium")
    impact = {"primary": "high", "alternative": "high", "null": "high",
              "reagent_confound": "medium", "translational": "high",
              "druggability": "high", "biomarker": "medium"}.get(cand.kind, "medium")

    return {
        "id": cand.id, "kind": cand.kind, "statement": cand.statement,
        "grounds_on": cand.grounds_on,
        "evidence_strength": _metric(evidence_strength, "computed",
                                     f"mean inverse-doubt of {len(doubts)} grounding node(s)"),
        "contradiction_score": _metric(contradiction_score, "computed",
                                       "fraction of recorded contradictions this engages"),
        "information_gain": _metric(eig, "estimate",
            "uncertainty x graph-stakes x decisiveness (structural proxy for "
            "expected uncertainty reduction; NOT a Bayesian posterior)",
            uncertainty=uncertainty, stakes=stakes, decisiveness=decisive),
        "cost_usd": _metric(cost, "estimate",
            "base + 2*n*per-sample*system-multiplier",
            assumptions=_COST, n_per_arm=n, system_class=sysc),
        "duration_weeks": _metric(weeks, "estimate",
            "base + n-scaling * system time-multiplier", assumptions=_TIME),
        "risk": _metric(risk, "computed",
                        "max grounding doubt + system complexity + failure modes"),
        "validation_difficulty": _metric(difficulty, "computed",
                                         f"experimental system class: {sysc}"),
        "novelty": _metric(novelty, "qualitative",
            "ordinal by hypothesis type; a quantitative score needs a corpus "
            "embedding search (Tier 3), not computed here"),
        "reviewer_confidence": _metric(rev_conf, "computed", rev_basis),
        "expected_impact": _metric(impact, "qualitative", "ordinal by hypothesis type"),
    }


def rank_candidates(cands, graph: EvidenceGraph, review) -> dict:
    max_reach = max((_reach(graph, c.mechanism_path) for c in cands), default=1)
    scored = [score_candidate(c, graph, review, max_reach) for c in cands]
    max_cost = max((s["cost_usd"]["value"] for s in scored), default=1) or 1
    # Normalize EIG across the candidate set so the most-informative experiment
    # gets full credit on the same 0-1 scale as the other terms (EIG drives the
    # decision — that is the product's whole claim).
    max_eig = max((s["information_gain"]["value"] for s in scored), default=1) or 1

    for s in scored:
        cost_norm = s["cost_usd"]["value"] / max_cost
        eig_norm = s["information_gain"]["value"] / max_eig
        priority = (
            WEIGHTS["information_gain"] * eig_norm +
            WEIGHTS["evidence_strength"] * s["evidence_strength"]["value"] +
            WEIGHTS["low_cost"] * (1 - cost_norm) +
            WEIGHTS["low_risk"] * (1 - _RISK_ORD[s["risk"]["value"]]) +
            WEIGHTS["novelty"] * _NOV_ORD[s["novelty"]["value"]])
        s["priority_score"] = _metric(round(priority, 3), "computed",
            "weighted composite of the dimensions below (weights shown)")
        # the human-readable "why this rank": the dominant contributions
        contribs = {
            "information gain": WEIGHTS["information_gain"] * eig_norm,
            "evidence strength": WEIGHTS["evidence_strength"] * s["evidence_strength"]["value"],
            "low cost": WEIGHTS["low_cost"] * (1 - cost_norm),
            "low risk": WEIGHTS["low_risk"] * (1 - _RISK_ORD[s["risk"]["value"]]),
            "novelty": WEIGHTS["novelty"] * _NOV_ORD[s["novelty"]["value"]]}
        s["why"] = [k for k, _ in sorted(contribs.items(), key=lambda kv: -kv[1])[:2]]

    scored.sort(key=lambda s: -s["priority_score"]["value"])
    for i, s in enumerate(scored, 1):
        s["rank"] = i
    return {"weights": WEIGHTS, "ranked": scored}
