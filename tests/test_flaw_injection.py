"""
Flaw-injection + flaw-catch tests. Injection must be deterministic and
non-destructive; the eval must run the real agents and never raise a false alarm
on a benign change. Offline (KEYSTONE_OFFLINE=1).
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

from dataclasses import replace  # noqa: E402,F401

from keystone.data_gbm import build_gbm_graph                       # noqa: E402
from keystone.deterministic.flaw_injection import (                 # noqa: E402
    FlawType, FLAW_CATALOGUE, BENIGN_CATALOGUE, inject_flaw, apply_benign)
from keystone.agents.flaw_catch_eval import evaluate                # noqa: E402
from keystone.agents.reasoner import HeuristicReasoner              # noqa: E402


def test_injection_is_non_destructive():
    g = build_gbm_graph()
    before = g.snapshot_hash()
    contexts_before = {(e.src, e.dst): e.context for e in g.edges}
    for ft in FLAW_CATALOGUE:
        inject_flaw(g, ft)
    # original graph is untouched (never mutated in place)
    assert g.snapshot_hash() == before
    assert {(e.src, e.dst): e.context for e in g.edges} == contexts_before


def test_each_flaw_plants_a_grounded_field_change():
    g = build_gbm_graph()
    planted = {}
    for ft in FLAW_CATALOGUE:
        res = inject_flaw(g, ft)
        assert res.planted is not None, f"{ft} found no target"
        assert res.graph is not g                      # a NEW graph
        assert res.planted.clean_value != res.planted.flawed_value
        planted[ft] = res.planted
    # each flaw touched the real field it claims to
    assert planted[FlawType.FALSE_RETRACTION].field == "retracted"
    assert planted[FlawType.CORRUPT_CONTEXT].field == "context"
    assert "temporal" in planted[FlawType.HIDE_TEMPORAL].field
    assert "problematic" in planted[FlawType.HIDE_REAGENT_PROBLEM].field


def test_false_retraction_actually_flips_the_flag_on_a_clean_node():
    g = build_gbm_graph()
    res = inject_flaw(g, FlawType.FALSE_RETRACTION)
    tgt = res.planted.target
    assert g.nodes[tgt].retracted is False          # original clean
    assert res.graph.nodes[tgt].retracted is True   # flawed copy flipped


def test_corrupt_context_changes_the_citing_sentence():
    g = build_gbm_graph()
    res = inject_flaw(g, FlawType.CORRUPT_CONTEXT)
    src = res.planted.target.split("->")[0]
    orig = next(e for e in g.edges if e.src == src)
    flawed = next(e for e in res.graph.edges if e.src == src)
    assert flawed.context != orig.context


def test_injection_is_reproducible():
    g1, g2 = build_gbm_graph(), build_gbm_graph()
    for ft in FLAW_CATALOGUE:
        r1, r2 = inject_flaw(g1, ft), inject_flaw(g2, ft)
        assert r1.graph.snapshot_hash() == r2.graph.snapshot_hash()
        assert r1.planted.target == r2.planted.target


def test_benign_perturbations_do_not_change_agent_output():
    """The negative class must be truly benign — no false alarms."""
    from keystone.agents.flaw_catch_eval import _assessment
    r = HeuristicReasoner()
    base = _assessment(build_gbm_graph(), r)
    for bp in BENIGN_CATALOGUE:
        assert _assessment(apply_benign(build_gbm_graph(), bp), r) == base


def test_eval_beats_coin_flip_with_no_false_alarms():
    res = evaluate(HeuristicReasoner(), build_gbm_graph)
    assert res["accuracy"] > 0.5                    # beats a coin flip
    assert res["fp"] == 0                           # precision 1.0, no false alarms
    assert res["tp"] >= 1                           # catches at least one real flaw
    # corrupt_context must be caught (it directly hits Evidence-Quality)
    caught = {s["name"] for s in res["samples"] if s["flawed"] and s["detected"]}
    assert "corrupt_context" in caught


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all flaw-injection tests passed")
