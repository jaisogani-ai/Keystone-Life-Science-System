"""
Scientific Decision Engine tests. The engine must generate COMPETING hypotheses,
rank them reproducibly, and — the trust guarantee — score every dimension as a
computed / estimate / qualitative value with a stated basis, never a fabricated
number. Offline.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

from keystone.decision_engine import decide                         # noqa: E402

_ALLOWED_KINDS = {"computed", "estimate", "qualitative"}
_METRIC_FIELDS = ["evidence_strength", "contradiction_score", "information_gain",
                  "cost_usd", "duration_weeks", "risk", "validation_difficulty",
                  "novelty", "reviewer_confidence", "expected_impact",
                  "priority_score"]


def test_generates_multiple_competing_hypotheses():
    d, *_ = decide("gbm")
    assert 5 <= len(d["competing_hypotheses"]) <= 20
    kinds = {h["kind"] for h in d["competing_hypotheses"]}
    assert "primary" in kinds and "null" in kinds        # not one hypothesis


def test_ranking_is_reproducible_and_sorted():
    d1, *_ = decide("gbm")
    d2, *_ = decide("gbm")
    order1 = [h["id"] for h in d1["competing_hypotheses"]]
    assert order1 == [h["id"] for h in d2["competing_hypotheses"]]
    scores = [h["priority_score"]["value"] for h in d1["competing_hypotheses"]]
    assert scores == sorted(scores, reverse=True)
    assert d1["competing_hypotheses"][0]["rank"] == 1


def test_every_metric_is_labeled_never_fabricated():
    d, *_ = decide("gbm")
    for h in d["competing_hypotheses"]:
        for f in _METRIC_FIELDS:
            m = h[f]
            assert m["kind"] in _ALLOWED_KINDS, f"{f} has un-labeled kind"
            assert m["basis"], f"{f} has no basis"
        # novelty is qualitative, never a fabricated percentage
        assert h["novelty"]["kind"] == "qualitative"
        assert "%" not in str(h["novelty"]["value"])
        # cost/duration/EIG are transparent estimates with assumptions shown
        assert h["cost_usd"]["kind"] == "estimate" and "assumptions" in h["cost_usd"]
        assert h["information_gain"]["kind"] == "estimate"


def test_recommendation_says_what_and_why_and_how_to_falsify():
    d, *_ = decide("gbm")
    rec = d["recommendation"]
    assert rec["hypothesis_id"] == d["competing_hypotheses"][0]["id"]
    assert rec["why_first"] and rec["how_to_falsify"].strip()
    assert rec["over_alternatives"]                       # explains vs the runner-up


def test_portfolio_buckets_every_hypothesis():
    d, *_ = decide("gbm")
    ids = {h["id"] for h in d["competing_hypotheses"]}
    assert {p["id"] for p in d["portfolio"]} == ids
    assert any(p["bucket"] == "Negative Control" for p in d["portfolio"])
    assert all(p["comes_before_others_because"] for p in d["portfolio"])


def test_debate_resolves_by_evidence_not_voting():
    d, *_ = decide("gbm")
    for dbt in d["debates"]:
        assert {r["role"] for r in
                (dbt["proponent"], dbt["skeptic"], dbt["reviewer"])} == \
               {"Proponent", "Skeptic", "Reviewer"}
        assert dbt["resolution"]["method"] == "explicit evidence, not voting"
        assert dbt["resolution"]["verdict"] and dbt["resolution"]["reason"]


def test_knowledge_gaps_are_categorized():
    d, *_ = decide("gbm")
    allowed = {"missing_dataset", "missing_control", "missing_replication",
               "missing_biomarker", "missing_validation", "missing_literature",
               "missing_molecular"}
    assert d["knowledge_gaps"]["gaps"]
    assert all(g["type"] in allowed for g in d["knowledge_gaps"]["gaps"])


def test_hypothesis_space_adapts_to_the_domain_honestly():
    gbm, *_ = decide("gbm")
    ins, *_ = decide("insulin")
    gbm_kinds = {h["kind"] for h in gbm["competing_hypotheses"]}
    ins_kinds = {h["kind"] for h in ins["competing_hypotheses"]}
    # cathepsin B is undrugged -> a druggability hypothesis; insulin receptor is
    # drugged -> none. Not fabricated for parity.
    assert "druggability" in gbm_kinds and "druggability" not in ins_kinds


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all decision-engine tests passed")
