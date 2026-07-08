"""Smoke tests: the workbench runs, is reproducible, and enforces its rules."""

from keystone.data_gbm import build_gbm_graph
from keystone.workbench import run
from keystone.agents.reasoner import HeuristicReasoner
from keystone.core import Hypothesis, ExperimentPlan, Interval


def test_pipeline_runs_and_is_reproducible():
    r = HeuristicReasoner()
    g1 = build_gbm_graph()
    l1, h1, rv1 = run("Q", g1, r)
    g2 = build_gbm_graph()
    l2, h2, rv2 = run("Q", g2, r)
    assert l1.graph_hash == l2.graph_hash, "run not reproducible"
    assert l1.contradictions == l2.contradictions


def test_load_bearing_discriminates():
    r = HeuristicReasoner()
    g = build_gbm_graph()
    run("Q", g, r)
    lb = {e.src: e.load_bearing.point for e in g.edges}
    # load-bearing citer must outrank incidental citer
    assert lb["N_dep_A"] > lb["N_dep_B"]


def test_rule3_enforced():
    # a hypothesis without failure modes must be rejected
    bad = Hypothesis(
        id="X", statement="s", mechanism_path=["a"],
        supporting_evidence=["a"], contradicting_evidence=["b"],
        confidence=Interval(0.5, 0.4, 0.6), uncertainty_notes="",
        validation_experiment=ExperimentPlan(
            perturbation="p", system="isogenic", positive_controls=["c"],
            negative_controls=["n"], readout="r", expected_outcome="e",
            kill_condition="this refutes the claim clearly",
            effect_size_source="a", assumed_effect_size=0.8, assumed_sd=1.0,
            alpha=0.05, power=0.8, required_n_per_arm=25,
            reproducibility_checklist=[]),
        expected_outcome="e", failure_modes=[])
    try:
        bad.validate()
        assert False, "rule 3 not enforced"
    except ValueError:
        pass


def test_power_analysis_refuses_without_grounded_effect():
    from keystone.deterministic.stats import sample_size_two_arm
    n, note = sample_size_two_arm(None, None)
    assert n is None and "cannot be computed" in note


def test_readiness_never_fabricates_percentages():
    """The honest-readiness guarantee: no dimension is a fabricated point %."""
    from keystone.reasoning_panel import research_readiness
    r = HeuristicReasoner()
    g = build_gbm_graph()
    _, hyp, review = run("Q", g, r)
    rr = research_readiness(hyp, review, g)
    # novelty must be qualitative, not a number
    assert "estimate" in rr["novelty"] and "%" not in str(rr["novelty"]["estimate"])
    # evidence support must carry an interval (uncertainty), not a bare score
    assert "interval" in rr["evidence_support"]
    # reproducibility is a ratio string, not a fake percentage
    assert "/" in rr["reproducibility"]["value"]


def test_future_tree_branches_on_outcome():
    from keystone.reasoning_panel import future_experiments_tree
    r = HeuristicReasoner()
    g = build_gbm_graph()
    _, hyp, _ = run("Q", g, r)
    tree = future_experiments_tree(hyp, g)
    root = tree[0]
    assert root["on_positive"] and root["on_negative"]  # both branches exist


def test_session_replay_is_ordered_and_complete():
    from keystone.replay import record_session
    r = HeuristicReasoner()
    g = build_gbm_graph()
    ledger, hyp, review = run("Q", g, r)
    s = record_session("Q", g, ledger, hyp, review)
    stages = [step.stage for step in s.steps]
    assert stages == ["PLAN", "COLLECT", "ANALYZE", "HYPOTHESIS",
                      "EXPERIMENT", "REVIEW", "LEDGER"]


if __name__ == "__main__":
    test_pipeline_runs_and_is_reproducible()
    test_load_bearing_discriminates()
    test_rule3_enforced()
    test_power_analysis_refuses_without_grounded_effect()
    test_readiness_never_fabricates_percentages()
    test_future_tree_branches_on_outcome()
    test_session_replay_is_ordered_and_complete()
    print("all smoke tests passed")
