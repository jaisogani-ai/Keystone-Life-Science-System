"""
Production-surface tests: multi-agent orchestration trace, provenance guarantee
(no orphan values), and publication-ready report generation. Offline.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

from keystone.data_gbm import build_gbm_graph                       # noqa: E402
from keystone.workbench import run                                  # noqa: E402
from keystone.agents.reasoner import HeuristicReasoner              # noqa: E402
from keystone.orchestrator import orchestrate, build_trace          # noqa: E402
from keystone.deterministic.provenance import (build_provenance,    # noqa: E402
                                               assert_no_orphan_values)
from keystone.artifacts.report import research_report_html          # noqa: E402


def _run():
    g = build_gbm_graph()
    ledger, hyp, review = run("Q", g, HeuristicReasoner())
    return g, ledger, hyp, review


def test_orchestration_trace_is_multi_agent_and_provenanced():
    g, ledger, hyp, review = _run()
    trace = build_trace("Q", g, ledger, hyp, review)
    actors = {s["actor_type"] for s in trace}
    assert actors == {"agent", "tool"}                # both, interleaved
    # a real coordinated pipeline: planner first, reviewer + ledger last
    assert trace[0]["actor"] == "Scientific Planner"
    assert any(s["actor"] == "Reviewer Agent" for s in trace)
    # every step carries provenance and is ordered
    assert [s["step"] for s in trace] == list(range(1, len(trace) + 1))
    assert all("evidence" in s for s in trace)
    # AI is an assistant: the numbers come from tools, not agents
    ndoubt = next(s for s in trace if s["actor"] == "Doubt Propagation")
    assert ndoubt["actor_type"] == "tool"


def test_orchestrate_returns_trace_and_ledger():
    g = build_gbm_graph()
    trace, ledger, hyp, review = orchestrate("Q", g, HeuristicReasoner())
    assert trace and ledger.graph_hash


# --- deepened agents: every seat is a structured scientific artifact --------
_ARTIFACT_KEYS = ["evidence", "sources", "source_datasets", "supporting_publications",
                  "contradictions", "assumptions", "remaining_uncertainty",
                  "proposed_experiment", "failure_modes", "provenance", "artifacts"]


def test_every_seat_exposes_the_structured_artifact_schema():
    g, ledger, hyp, review = _run()
    trace = build_trace("Q", g, ledger, hyp, review)
    for s in trace:
        for k in _ARTIFACT_KEYS:
            assert k in s, f"{s['actor']} missing artifact field {k}"


def test_reviewer_visibly_reduces_confidence_and_states_its_challenge():
    g, ledger, hyp, review = _run()
    trace = build_trace("Q", g, ledger, hyp, review)
    rev = next(s for s in trace if s["actor"] == "Reviewer Agent")
    assert rev["confidence_before"] is not None and rev["confidence_after"] is not None
    assert rev["confidence_after"] < rev["confidence_before"]        # confidence removed
    assert round(rev["confidence_after"] - rev["confidence_before"], 3) == rev["confidence_delta"]
    assert rev["challenged_assumption"] and rev["why_disagrees"]     # challenge is explicit


def test_pi_synthesizes_last_without_fabricating():
    g, ledger, hyp, review = _run()
    trace = build_trace("Q", g, ledger, hyp, review)
    pi = trace[-1]
    assert pi["actor"] == "Principal Investigator" and pi["actor_type"] == "agent"
    # synthesis uses the reviewed confidence — no number the engine didn't produce
    assert pi["confidence_after"] == round(review.adjusted_confidence.point, 3)
    assert pi["proposed_experiment"] and pi["provenance"]


def test_decision_enriches_hypothesis_and_pi_with_expected_information_gain():
    from keystone.decision_engine import decide
    d, g, ledger, hyp, review = decide("gbm")
    trace = build_trace(d["question"], g, ledger, hyp, review, decision=d)
    hstep = next(s for s in trace if s["actor"] == "Hypothesis Agent")
    assert hstep["information_gain"] is not None                     # EIG cited when ranked
    assert trace[-1]["information_gain"] is not None


def test_provenance_has_no_orphan_values():
    g, ledger, hyp, review = _run()
    prov = build_provenance(g, ledger, hyp)
    assert_no_orphan_values(prov)                     # raises if any orphan
    cov = prov["coverage"]
    assert cov["nodes_resolved"] >= 1
    assert cov["nodes_resolved"] + cov["nodes_unresolved"] == cov["nodes_total"]
    # every grounding node of the hypothesis is provenanced to a source
    assert all(g["source"] for g in prov["hypothesis_grounding"])


def test_report_is_publication_ready_and_cites_real_dois():
    g, ledger, hyp, review = _run()
    html = research_report_html("Q", g, ledger, hyp, review)
    assert html.startswith("<!doctype html>")
    assert ledger.graph_hash in html                  # reproducibility hash
    assert "10.1038/sj.onc.1207616" in html           # a real cited DOI
    assert "Independent reviewer critique" in html     # auditable, not promo
    assert "Provenance appendix" in html


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all production tests passed")
