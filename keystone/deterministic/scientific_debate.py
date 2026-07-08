"""
keystone.deterministic.scientific_debate
========================================
Every hypothesis is argued by three roles — Proponent, Skeptic, Reviewer — and a
recommendation is issued ONLY after the disagreement is resolved by explicit
evidence, never by voting. Deterministic: each role's case is assembled from real
graph nodes (their text + doubt) and the resolution rule cites the specific
evidence that tips it.

The live ClaudeReasoner can voice these roles semantically; offline this is the
structured evidence confrontation, which is the honest, reproducible core.
"""
from __future__ import annotations

from keystone.core import EvidenceGraph


def _node_line(graph, nid):
    n = graph.nodes.get(nid)
    return (f"{nid} (doubt {n.doubt.point:.2f}): {n.text[:70]}"
            if n else f"{nid} (not in graph)")


def debate(cand, scored: dict, graph: EvidenceGraph) -> dict:
    proponent = {
        "role": "Proponent",
        "case": [_node_line(graph, nid) for nid in cand.supporting]
                or ["relies on the mechanism being real; no direct supporting node yet"],
        "claim": (f"worth testing: expected information gain "
                  f"{scored['information_gain']['value']}, evidence strength "
                  f"{scored['evidence_strength']['value']}")}

    skeptic_case = [_node_line(graph, nid) for nid in cand.contradicting]
    skeptic_case += [f"failure mode: {f}" for f in cand.failure_modes[:2]]
    high_doubt = [nid for nid in cand.mechanism_path
                  if nid in graph.nodes and graph.nodes[nid].doubt.point >= 0.6]
    skeptic = {
        "role": "Skeptic",
        "case": skeptic_case or ["no recorded contradiction — but absence of "
                                 "disconfirming tests is itself a weakness"],
        "claim": (f"grounding leans on high-doubt node(s) {high_doubt}"
                  if high_doubt else "no disqualifying doubt, but unproven")}

    reviewer = {
        "role": "Reviewer",
        "case": [scored["reviewer_confidence"]["basis"]],
        "claim": f"reviewer confidence {scored['reviewer_confidence']['value']}"}

    # --- resolution by explicit evidence (no voting) -------------------------
    ev = scored["evidence_strength"]["value"]
    rev = scored["reviewer_confidence"]["value"]
    kill = cand.experiment.kill_condition.strip()
    if not kill:
        verdict, reason = "not_recommended", "no falsifiable kill-condition"
    elif ev >= 0.5 and rev >= 0.35:
        verdict = "recommended_to_test"
        reason = (f"the supporting evidence (strength {ev}) and reviewer "
                  f"confidence ({rev}) clear the bar, and the Skeptic's objection "
                  f"is directly addressable by the kill-condition: \"{kill[:80]}\"")
    elif high_doubt:
        verdict = "test_but_reframe"
        reason = (f"the Skeptic wins on grounding: node(s) {high_doubt} carry "
                  f"disqualifying doubt. Recommend the reframed/null variant first "
                  f"so the doubtful foundation is tested before building on it")
    else:
        verdict = "recommended_to_test"
        reason = (f"weak but no disqualifying doubt; the kill-condition \"{kill[:60]}\" "
                  f"makes it cheap to falsify")

    return {"id": cand.id, "proponent": proponent, "skeptic": skeptic,
            "reviewer": reviewer,
            "resolution": {"verdict": verdict, "reason": reason,
                           "method": "explicit evidence, not voting"}}
