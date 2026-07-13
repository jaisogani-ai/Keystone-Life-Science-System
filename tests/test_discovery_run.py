"""
Tests for the discovery-run cross-wire — the self-correcting loop that ties
the Literature Pattern Miner, the Decision Engine, and the Laboratory Agent
into one system. Runs offline.

The claims under test:
  1. a literature contradiction becomes a rankable Decision Engine hypothesis
     (kind='literature_contradiction'), scored by the SAME auditable scorer;
  2. a failing validation plate downgrades the recommendation's confidence;
  3. an unsupported plate format is refused, not fabricated;
  4. the run is reproducible (same inputs -> same run_hash);
  5. an empty corpus adds no literature hypotheses but still ranks the graph
     ones (no fabrication of a contradiction that isn't there).
"""
import os
os.environ["KEYSTONE_OFFLINE"] = "1"

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from keystone.discovery_run import run_discovery  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]


def _corpus():
    return json.loads(
        (_ROOT / "examples" / "pattern_corpora" / "gbm_cathepsin_b.json").read_text())


def _plate(name):
    return (_ROOT / "examples" / "bench_data" / name).read_text()


def test_literature_contradiction_becomes_a_ranked_hypothesis():
    c = _corpus()
    r = run_discovery(c["records"], domain="gbm", question=c["question"],
                      seed_doi=c["seed_doi"])
    assert r["contradictions_found"] >= 1
    assert r["n_literature_hypotheses"] >= 1
    # at least one ranked hypothesis is literature-sourced, and it is scored on
    # the same board as the graph hypotheses (has a priority_score)
    lit = [s for s in r["competing_hypotheses"] if s["source"] == "literature"]
    assert lit and all("priority_score" in s for s in lit)
    assert r["top_literature_hypothesis"] is not None
    # its grounding cites the real DOI pair (no fabrication)
    assert " vs " in r["top_literature_hypothesis"]["grounds_on"]


def test_failing_plate_downgrades_the_recommendation_confidence():
    c = _corpus()
    r = run_discovery(c["records"], domain="gbm", bench_csv=_plate("bad_plate.csv"))
    b = r["bench_review"]
    assert b["reviewed"] is True
    assert b["verdict"] == "rejected"
    assert b["downgraded"] is True
    assert b["adjusted_confidence"] < b["base_confidence"]
    assert b["applies_to"] == r["recommendation"]["hypothesis_id"]


def test_clean_plate_does_not_downgrade():
    c = _corpus()
    r = run_discovery(c["records"], domain="gbm", bench_csv=_plate("clean_plate.csv"))
    b = r["bench_review"]
    assert b["verdict"] == "supported"
    assert b["downgraded"] is False


def test_unsupported_plate_format_is_refused():
    c = _corpus()
    r = run_discovery(c["records"], domain="gbm",
                      bench_csv="n/a", bench_fmt="western_blot")
    assert r["bench_review"]["verdict"] == "refused"
    assert "refused" in r["bench_review"]["reason"].lower()


def test_run_hash_is_reproducible():
    c = _corpus()
    a = run_discovery(c["records"], domain="gbm")
    b = run_discovery(c["records"], domain="gbm")
    assert a["run_hash"] == b["run_hash"]


def test_empty_corpus_adds_no_literature_hypotheses_but_still_ranks_graph():
    r = run_discovery([], domain="gbm")
    assert r["contradictions_found"] == 0
    assert r["n_literature_hypotheses"] == 0
    assert r["top_literature_hypothesis"] is None
    # the graph hypotheses still rank — the loop degrades honestly
    assert r["n_graph_hypotheses"] >= 1
    assert r["competing_hypotheses"] and r["recommendation"]["hypothesis_id"]


def test_reasoning_receipt_makes_the_deterministic_fable_human_split_auditable():
    """The reasoning receipt labels WHO reasoned WHAT: the engine owns the
    numbers (covered by the hash), Fable 5 owns advisory prose (not hashed),
    and a human must sign off. Offline, the reasoner label is honest."""
    c = _corpus()
    r = run_discovery(c["records"], domain="gbm", question=c["question"])
    rc = r["receipt"]
    assert rc["title"] == "Reasoning receipt"
    assert rc["run_hash"] == r["run_hash"] and rc["graph_hash"] == r["graph_hash"]
    steps = {s["n"]: s for s in rc["steps"]}
    # the two engine steps are covered by the reproducibility hash
    assert steps[1]["owner"] == "deterministic engine" and steps[1]["covered_by_hash"]
    assert steps[2]["owner"] == "deterministic engine" and steps[2]["covered_by_hash"]
    # the reasoning step is advisory prose — NOT hashed — and offline is labelled honestly
    assert steps[3]["step"] == "Reasoning" and steps[3]["covered_by_hash"] is False
    assert rc["reasoner"] == "deterministic template"
    assert steps[3]["narrative"] is None            # no Claude offline
    # a human gates release
    assert steps[4]["owner"] == "principal investigator"
    assert steps[4]["status"] == "pending"
    assert "scientists decide" in rc["discipline"]


def test_receipt_narrative_is_advisory_only_and_never_changes_the_hash():
    """Rule 7 at the boundary: Fable 5 writes prose, never numbers. Passing a
    reasoner must not move the run_hash — the deterministic decision layer, and
    the hash covering it, are identical with or without a semantic reasoner."""
    from keystone.agents.reasoner import HeuristicReasoner
    from keystone.reasoning_receipt import reasoning_narrative
    c = _corpus()
    without = run_discovery(c["records"], domain="gbm")
    withdet = run_discovery(c["records"], domain="gbm", reasoner=HeuristicReasoner())
    assert without["run_hash"] == withdet["run_hash"]      # hash unmoved
    # the deterministic reasoner yields no narrative (no fabricated Fable prose)
    assert reasoning_narrative(without, HeuristicReasoner()) is None
    assert reasoning_narrative(without, None) is None


if __name__ == "__main__":
    test_literature_contradiction_becomes_a_ranked_hypothesis()
    test_failing_plate_downgrades_the_recommendation_confidence()
    test_clean_plate_does_not_downgrade()
    test_unsupported_plate_format_is_refused()
    test_run_hash_is_reproducible()
    test_empty_corpus_adds_no_literature_hypotheses_but_still_ranks_graph()
    print("all discovery-run tests passed")
