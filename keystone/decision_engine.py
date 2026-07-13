"""
keystone.decision_engine
=======================
The Scientific Decision Engine — Keystone's reason to exist. It does NOT show
"what information exists"; it answers "what should the scientist do next, and
why". The workflow is the product:

  Research Question -> Evidence -> Contradictions -> Knowledge gaps ->
  Competing hypotheses -> Reviewer critique -> Experiments designed ->
  Expected information gain -> Experiment ranking -> Scientist decision

Deterministic composition of the decision modules; every score is computed or
labeled (never fabricated). Returns a Decision + the underlying objects.
"""
from __future__ import annotations

from keystone.workbench import run
from keystone.agents.reasoner import HeuristicReasoner
from keystone.connectors import clinical as C
from keystone.deterministic.contradiction_mining import mine_contradictions
from keystone.deterministic.gap_engine import detect_knowledge_gaps
from keystone.deterministic.hypothesis_space import generate_candidates
from keystone.deterministic.decision_metrics import rank_candidates
from keystone.deterministic.experiment_portfolio import build_portfolio
from keystone.deterministic.scientific_debate import debate

_TIMELINE = ["Question", "Evidence", "Contradiction", "Gap", "Hypothesis",
             "Reviewer", "Experiment", "Scientist Decision", "Ledger"]


def _spec_and_builder(domain: str):
    if domain == "insulin":
        from keystone import insulin_spec as SPEC
        from keystone.data_insulin import build_insulin_graph as build
        return SPEC, build
    if domain == "ich":
        from keystone import ich_spec as SPEC
        from keystone.data_ich import build_ich_graph as build
        return SPEC, build
    if domain == "tcell":
        from keystone import tcell_spec as SPEC
        from keystone.data_tcell import build_tcell_graph as build
        return SPEC, build
    from keystone import gbm_spec as SPEC
    from keystone.data_gbm import build_gbm_graph as build
    return SPEC, build


def _experiment_view(ep) -> dict:
    return {"perturbation": ep.perturbation, "system": ep.system,
            "kill_condition": ep.kill_condition,
            "n_per_arm": ep.required_n_per_arm,
            "controls": {"positive": ep.positive_controls,
                         "negative": ep.negative_controls}}


def decide(domain: str = "gbm", reasoner=None,
           graph=None, question: str | None = None,
           chembl_query: str | None = None):
    """Produce the decision. Returns (decision_dict, graph, ledger, hyp, review).

    Two modes:
      * curated library — pass ``domain`` ('gbm' or 'insulin'); the graph and
        question are built from the pinned spec, and ChEMBL is queried for the
        target's known drugs.
      * scientist's imported refs — pass ``graph`` (built via
        ``ingest/references.build_graph_from_dois``) and optionally
        ``question`` + ``chembl_query``. When ``chembl_query`` is not supplied,
        ChEMBL is skipped honestly (drug_info stays empty)."""
    reasoner = reasoner or HeuristicReasoner()
    if graph is None:
        spec, build = _spec_and_builder(domain)
        graph = build()
        question = question or spec.QUESTION
        chembl_query = chembl_query or spec.CHEMBL_QUERY
    else:
        question = question or "Imported reference set"
    ledger, hyp, review = run(question, graph, reasoner)

    drug_info = C.chembl_drugs(chembl_query) if chembl_query else {
        "resolved": False, "count": 0, "drugs": []}
    contradictions = mine_contradictions(graph)
    gaps = detect_knowledge_gaps(hyp, graph)
    cands = generate_candidates(graph, hyp, drug_info)
    ranking = rank_candidates(cands, graph, review)
    ranked = ranking["ranked"]
    portfolio = build_portfolio(ranked)
    by_id = {c.id: c for c in cands}
    debates = [debate(by_id[s["id"]], s, graph) for s in ranked]

    top = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    top_cand = by_id[top["id"]]
    over = None
    if runner_up:
        over = (f"ranked above {runner_up['id']} ({runner_up['kind']}) because "
                f"priority {top['priority_score']['value']} > "
                f"{runner_up['priority_score']['value']} — driven by "
                f"{', '.join(top['why'])}")

    recommendation = {
        "hypothesis_id": top["id"], "kind": top["kind"],
        "statement": top["statement"],
        "why_first": top["why"],
        "priority_score": top["priority_score"]["value"],
        "information_gain": top["information_gain"]["value"],
        "cost_usd": top["cost_usd"]["value"],
        "duration_weeks": top["duration_weeks"]["value"],
        "risk": top["risk"]["value"],
        "experiment": _experiment_view(top_cand.experiment),
        "how_to_falsify": top_cand.experiment.kill_condition,
        "over_alternatives": over}

    workflow = [
        {"stage": "Research Question", "value": question},
        {"stage": "Evidence collected", "value": f"{len(graph.nodes)} nodes, "
         f"{len(graph.edges)} edges from real connectors"},
        {"stage": "Contradictions detected", "value": len(contradictions)},
        {"stage": "Knowledge gaps discovered", "value": gaps["count"]},
        {"stage": "Competing hypotheses generated", "value": len(cands)},
        {"stage": "Reviewer critique", "value": f"{review.verdict.value} -> "
         f"{review.adjusted_confidence.point}"},
        {"stage": "Experiments designed", "value": len(cands)},
        {"stage": "Expected information gain", "value": "computed per hypothesis"},
        {"stage": "Experiment ranking", "value": f"#1 = {top['id']} "
         f"(priority {top['priority_score']['value']})"},
        {"stage": "Scientist decision", "value": "human-gated"},
    ]

    decision = {
        "domain": domain, "question": question,
        "graph_hash": ledger.graph_hash,
        "workflow": workflow,
        "contradictions": contradictions,
        "knowledge_gaps": gaps,
        "competing_hypotheses": ranked,
        "weights": ranking["weights"],
        "portfolio": portfolio,
        "debates": debates,
        "decision_timeline": _TIMELINE,
        "recommendation": recommendation,
    }
    return decision, graph, ledger, hyp, review


def main() -> int:
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="Keystone Scientific Decision Engine")
    ap.add_argument("--domain", choices=["gbm", "insulin", "ich"], default="gbm")
    args = ap.parse_args()
    d, *_ = decide(args.domain)
    print("=" * 74)
    print(f"KEYSTONE DECISION ENGINE — {args.domain}")
    print("=" * 74)
    print(f"Q: {d['question']}\n")
    print(f"{len(d['competing_hypotheses'])} competing hypotheses "
          f"| {d['knowledge_gaps']['count']} knowledge gaps "
          f"| {len(d['contradictions'])} contradiction(s)\n")
    print("RANKED (priority | EIG | cost | risk | kind):")
    for s in d["competing_hypotheses"]:
        print(f"  #{s['rank']} {s['id']:5s} {s['priority_score']['value']:.3f} | "
              f"EIG {s['information_gain']['value']:.2f} | "
              f"${s['cost_usd']['value']:>7,} | {s['risk']['value']:6s} | {s['kind']}")
    r = d["recommendation"]
    print(f"\n>> RUN NEXT: {r['hypothesis_id']} ({r['kind']}) — "
          f"why: {', '.join(r['why_first'])}")
    print(f"   experiment: {r['experiment']['perturbation']}")
    print(f"   falsify by: {r['how_to_falsify']}")
    print(f"   over alternatives: {r['over_alternatives']}")
    return sys.exit(0)


if __name__ == "__main__":
    main()
