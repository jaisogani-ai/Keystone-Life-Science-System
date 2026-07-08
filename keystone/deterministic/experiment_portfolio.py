"""
keystone.deterministic.experiment_portfolio
===========================================
Scientists rarely run one experiment. Turn the ranked competing hypotheses into a
PORTFOLIO — Quick Win / High Impact / High Risk / Cheap Validation / Mechanism
Validation / Clinical Translation / Negative Control — and say, for each, why it
comes before the others. Deterministic classification from the already-computed
decision metrics (no new numbers).
"""
from __future__ import annotations

BUCKETS = ["Negative Control", "Cheap Validation", "Quick Win",
           "Mechanism Validation", "High Impact", "High Risk",
           "Clinical Translation"]


def _bucket(scored: dict, cheapest_id: str) -> str:
    kind = scored["kind"]
    risk = scored["risk"]["value"]
    diff = scored["validation_difficulty"]["value"]
    eig = scored["information_gain"]["value"]
    if kind == "null":
        return "Negative Control"
    if kind in ("translational",) or diff == "high":
        return "Clinical Translation" if kind == "translational" else "High Risk"
    if scored["id"] == cheapest_id:
        return "Cheap Validation"
    if risk == "high":
        return "High Risk"
    if eig >= 0.5 and scored["expected_impact"]["value"] == "high":
        return "High Impact"
    if scored["cost_usd"]["value"] <= 60000 and scored["duration_weeks"]["value"] <= 12:
        return "Quick Win"
    return "Mechanism Validation"


def build_portfolio(ranked: list[dict]) -> list[dict]:
    """One entry per hypothesis, bucketed, with an explicit ordering rationale."""
    if not ranked:
        return []
    cheapest = min(ranked, key=lambda s: s["cost_usd"]["value"])["id"]
    out = []
    for s in ranked:
        bucket = _bucket(s, cheapest)
        why = (f"ranked #{s['rank']} of {len(ranked)} — chosen for "
               f"{', '.join(s['why'])}; "
               f"EIG {s['information_gain']['value']}, "
               f"~${s['cost_usd']['value']:,}, ~{s['duration_weeks']['value']}wk, "
               f"risk {s['risk']['value']}")
        out.append({
            "id": s["id"], "bucket": bucket, "rank": s["rank"],
            "statement": s["statement"],
            "kind": s["kind"], "comes_before_others_because": why})
    out.sort(key=lambda e: e["rank"])
    return out
