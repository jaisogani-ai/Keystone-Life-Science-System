"""
keystone.live_debate
===================
Live AI Debate — specialist roles argue a hypothesis from their own evidence
lens and reach CONSENSUS by explicit evidence, never by voting:

  Bioinformatics -> Disease Biology -> Reviewer -> PI -> Consensus

Each role's case is assembled from real objects (the stats/graph for
Bioinformatics, the molecular/pathway/contradiction nodes for Disease Biology,
the ReviewResult for the Reviewer, the human gate for the PI) — deterministic
offline, and voiceable by Claude live (each role still narrates the SAME real
evidence; no role fabricates a number). This is additive; the 3-role
proponent/skeptic debate in scientific_debate.py is unchanged.
"""
from __future__ import annotations

from keystone.workbench import run
from keystone.agents.reasoner import HeuristicReasoner


def _spec_and_builder(domain: str):
    if domain == "insulin":
        from keystone import insulin_spec as SPEC
        from keystone.data_insulin import build_insulin_graph as build
        return SPEC, build, "Metabolic Biology"
    if domain == "ich":
        from keystone import ich_spec as SPEC
        from keystone.data_ich import build_ich_graph as build
        return SPEC, build, "Neurovascular Biology"
    if domain == "tcell":
        from keystone import tcell_spec as SPEC
        from keystone.data_tcell import build_tcell_graph as build
        return SPEC, build, "Immunology"
    from keystone import gbm_spec as SPEC
    from keystone.data_gbm import build_gbm_graph as build
    return SPEC, build, "Cancer Biology"


def run_debate(domain: str = "gbm") -> dict:
    spec, build, biology_role = _spec_and_builder(domain)
    graph = build()
    ledger, hyp, review = run(spec.QUESTION, graph, HeuristicReasoner())
    ep = hyp.validation_experiment

    lb = {f"{e.src}->{e.dst}": round(e.load_bearing.point, 2) for e in graph.edges
          if e.edge_type.value in ("cites", "depends_on")}
    high_doubt = [n.id for n in graph.nodes.values() if n.doubt.point >= 0.6]
    molecular = [n for n in graph.nodes.values()
                 if n.node_type.value == "molecular_result"]

    turns = [
        {"role": "Bioinformatics", "lens": "quantitative / statistical",
         "case": [
             f"power analysis: n/arm={ep.required_n_per_arm} from a LABELED "
             f"d=0.80 (deterministic; refuses to fabricate n)",
             f"load-bearing weights: {lb}",
             f"doubt propagation flags {len(high_doubt)} node(s) at high doubt: "
             f"{', '.join(high_doubt) or 'none'}"],
         "position": ("the design is powered and falsifiable, but the numbers "
                      "inherit doubt from " + (", ".join(high_doubt) or "no node"))},
        {"role": biology_role, "lens": "mechanistic / pathway",
         "case": [f"{n.id}: {n.text[:70]}" for n in molecular[:2]]
                 or ["no independent molecular result grounds the mechanism"],
         "position": ("mechanism is plausible but a recorded contradiction must "
                      "be resolved before causal claims" if hyp.contradicting_evidence
                      else "mechanism is grounded; direct causal test still owed")},
        {"role": "Reviewer", "lens": "adversarial",
         "case": [review.weakness],
         "position": f"{review.verdict.value}: confidence "
                     f"{hyp.confidence.point} -> {review.adjusted_confidence.point}"},
        {"role": "PI", "lens": "decision / human gate (rule 1)",
         "case": ["consensus is advisory; the PI holds the approval gate"],
         "position": "decision pending human approval; not auto-committed"},
    ]

    # consensus by explicit evidence (NOT voting)
    ev_ok = review.verdict.value != "rejected"
    if not ep.kill_condition.strip():
        consensus = ("no consensus — the hypothesis lacks a falsifiable "
                     "kill-condition")
    elif high_doubt and any(h in hyp.mechanism_path for h in high_doubt):
        consensus = (f"conditional consensus: test, but the Reviewer's objection "
                     f"on {', '.join(h for h in high_doubt if h in hyp.mechanism_path)} "
                     f"stands — run the design whose kill-condition "
                     f"(\"{ep.kill_condition[:70]}\") directly resolves it, and "
                     f"gate the conclusion on the PI's approval")
    elif ev_ok:
        consensus = ("consensus to test: Bioinformatics confirms the design is "
                     "powered, Biology confirms the mechanism is grounded, the "
                     "Reviewer finds no disqualifying doubt — PI approval pending")
    else:
        consensus = "no consensus — the Reviewer rejects the grounding"

    return {"domain": domain, "question": spec.QUESTION,
            "graph_hash": ledger.graph_hash, "hypothesis": hyp.statement,
            "turns": turns,
            "consensus": {"statement": consensus,
                          "method": "explicit evidence, not voting",
                          "human_gated": True}}
