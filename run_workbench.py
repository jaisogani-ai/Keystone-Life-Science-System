"""
Keystone Workbench — end-to-end demo runner.

Runs the full loop offline with HeuristicReasoner. Set KEYSTONE_LIVE=1 and
ANTHROPIC_API_KEY to run with the real ClaudeReasoner instead — nothing else
changes.
"""

import os
import sys

from keystone.data_gbm import build_gbm_graph
from keystone.workbench import run
from keystone.reasoning_panel import (
    why_panel, future_experiments_tree, research_readiness,
)
from keystone.replay import record_session
from keystone.gbm_spec import QUESTION


def _write(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def get_reasoner():
    if os.environ.get("KEYSTONE_LIVE") == "1":
        from keystone.agents.claude_reasoner import ClaudeReasoner
        return ClaudeReasoner()
    from keystone.agents.reasoner import HeuristicReasoner
    return HeuristicReasoner()


def main():
    reasoner = get_reasoner()
    graph = build_gbm_graph()

    print("=" * 74)
    print("KEYSTONE — AI Scientific Research Workbench")
    print("=" * 74)
    print(f"\nQ: {QUESTION}\n")

    ledger, hyp, review = run(QUESTION, graph, reasoner)

    print(f"PLAN      {ledger.plan.get('intent')} | "
          f"connectors={len(ledger.plan.get('connectors', []))}")
    print(f"COLLECT   {len(graph.nodes)} nodes, {len(graph.edges)} edges | "
          f"hash={ledger.graph_hash}\n")

    print("ANALYZE   doubt propagated (load-bearing weighted):")
    for e in graph.edges:
        if e.edge_type.value in ("cites", "depends_on"):
            dn = graph.nodes[e.src].doubt.point
            print(f"          {e.src:8s}->{e.dst:14s} w={e.load_bearing.point:.2f} "
                  f"{e.temporal.value:11s} inherited_doubt={dn:.2f}")
    print(f"          contradictions: {ledger.contradictions}\n")

    print("HYPOTHESIS (rule-3 complete):")
    print(f"          {hyp.statement}")
    print(f"          support={hyp.supporting_evidence} "
          f"contra={hyp.contradicting_evidence}")
    print(f"          confidence={hyp.confidence.point:.2f} "
          f"[{hyp.confidence.low:.2f},{hyp.confidence.high:.2f}]")
    print(f"          failure_modes={len(hyp.failure_modes)}\n")

    ep = hyp.validation_experiment
    print("EXPERIMENT PLAN (actionable):")
    print(f"          perturbation: {ep.perturbation}")
    print(f"          system:       {ep.system}")
    print(f"          +controls:    {ep.positive_controls}")
    print(f"          -controls:    {ep.negative_controls}")
    print(f"          kill:         {ep.kill_condition}")
    print(f"          n/arm:        {ep.required_n_per_arm}  "
          f"(effect src: {ep.effect_size_source})")
    print(f"          stats:        {ep.stats_notes}")
    if ledger.protocol_warnings:
        print(f"          WARNINGS:     {ledger.protocol_warnings}\n")
    else:
        print()

    print("REVIEW (independent challenge, rule 4):")
    print(f"          verdict: {review.verdict.value.upper()}")
    print(f"          weakness: {review.weakness}")
    print(f"          adjusted confidence: {review.adjusted_confidence.point:.2f}\n")

    print("TIMELINE:")
    for ev in ledger.timeline:
        print(f"          {ev['date']}  {ev['kind']:13s} {ev['label']}")

    # --- Enhancement 1: Why-panel (the reasoning chain) --------------------
    wp = why_panel(hyp, review, graph)
    print("\nWHY PANEL (reasoning chain):")
    print(f"          support={[e['id'] for e in wp['supporting_evidence']]} "
          f"contra={[e['id'] for e in wp['contradicting_evidence']]}")
    print(f"          reviewer: {wp['reviewer_objection']['verdict']} -> "
          f"conf {wp['reviewer_objection']['adjusted_confidence']}")

    # --- Enhancement 3: Future experiments decision tree -------------------
    print("\nFUTURE EXPERIMENTS (decision tree):")
    for b in future_experiments_tree(hyp, graph):
        print(f"          {b['node_id']:7s} +{b['on_positive'] or 'end'}"
              f" / -{b['on_negative'] or 'end'}: {b['description'][:52]}")

    # --- Enhancement 5: Research readiness (HONEST, no fake %) --------------
    rr = research_readiness(hyp, review, graph)
    print("\nRESEARCH READINESS (computed / interval / qualitative — never faked):")
    print(f"          evidence_support: {rr['evidence_support']['value']} "
          f"{rr['evidence_support'].get('interval')}")
    print(f"          reproducibility:  {rr['reproducibility']['value']}")
    print(f"          risk:             {rr['risk']}")
    print(f"          missing_evidence: {rr['missing_evidence']['count']} "
          f"{rr['missing_evidence']['items']}")
    print(f"          novelty:          {rr['novelty']['estimate']} "
          f"(quantitative score is roadmap)")

    import os as _os
    out = "demo_out"
    _os.makedirs(out, exist_ok=True)
    with open(f"{out}/ledger.json", "w") as f:
        f.write(ledger.to_json())
    print(f"\nEMIT      {out}/ledger.json written (auditable artifact)")

    # --- Native artifacts (rule 5): every artifact tied to its reasoning ----
    from keystone.artifacts.reasoning_render import (why_panel_html,
                                                     future_experiments_svg)
    from keystone.artifacts.render import (evidence_graph_svg, timeline_svg,
                                           protein_viewer_html)
    _write(f"{out}/why_panel.html", why_panel_html(wp))
    _write(f"{out}/future_experiments.svg",
           future_experiments_svg(future_experiments_tree(hyp, graph)))
    _write(f"{out}/evidence_graph.svg", evidence_graph_svg(graph))
    _write(f"{out}/timeline.svg", timeline_svg(ledger.timeline))
    _write(f"{out}/protein.html",
           protein_viewer_html(graph.nodes["N_target"].meta.get("pdb", "1HUC"),
                               graph.nodes["N_target"].text))
    print(f"EMIT      {out}/ {{why_panel.html, future_experiments.svg, "
          f"evidence_graph.svg, timeline.svg, protein.html}}")

    # --- Enhancement 4: Session replay -------------------------------------
    session = record_session(QUESTION, graph, ledger, hyp, review)
    with open(f"{out}/session.json", "w") as f:
        f.write(session.to_json())
    session.replay()

    g2 = build_gbm_graph()
    assert g2.snapshot_hash() == graph.snapshot_hash()
    print(f"REPRO     re-run hash identical ({g2.snapshot_hash()})")
    print("=" * 74)


if __name__ == "__main__":
    sys.exit(main())
