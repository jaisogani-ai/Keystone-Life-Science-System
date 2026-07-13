"""
Tests for Frontier Guard — Keystone's responsible-AI layer for two frontiers.
Verifies the ACTIVE assessments (phage biosafety vet, organoid rigor score),
the refusals, and the "never generate / never predict" guarantee. Offline.
"""
import os
os.environ["KEYSTONE_OFFLINE"] = "1"

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from keystone.frontier_guard import (  # noqa: E402
    vet_phage_candidate, score_organoid_study, score_aging_study,
    assess_frontier, frontier_catalogue, ORGANOID_RIGOR, AGING_RIGOR,
)

_ROOT = Path(__file__).resolve().parents[1]


def test_phage_vet_flags_toxin_gene_as_no_go():
    r = vet_phage_candidate(genes=["major capsid protein", "stx2",
                                    "tail fiber protein"])
    assert r["verdict"] == "no-go"
    toxin = next(c for c in r["checks"] if c["category"] == "toxin genes")
    assert toxin["hit"] is True and toxin["markers"]
    # the screen is explicitly NOT clearance and NOT a generator
    assert "not" in r["refusal"].lower() and "generate" in r["refusal"].lower()


def test_phage_vet_flags_lysogeny_and_amr():
    lyso = vet_phage_candidate(genes=["capsid", "integrase", "tail fiber"])
    assert lyso["verdict"] == "no-go"
    amr = vet_phage_candidate(genes=["capsid", "blaKPC", "tail fiber"])
    assert amr["verdict"] == "no-go"
    assert any(c["category"] == "AMR genes" and c["hit"] for c in amr["checks"])


def test_phage_vet_clean_lytic_with_host_range_is_go():
    r = vet_phage_candidate(genes=["major capsid protein", "DNA polymerase",
                                    "tail fiber protein", "lysin",
                                    "receptor binding protein"])
    assert r["verdict"] == "go"


def test_phage_vet_clean_without_host_range_is_caution():
    r = vet_phage_candidate(genes=["major capsid protein", "DNA polymerase",
                                    "terminase large subunit"])
    assert r["verdict"] == "caution"


def test_organoid_score_high_risk_on_gappy_study():
    r = score_organoid_study({"passage_recorded": True})
    assert r["verdict"] == "high"
    assert r["critical_gaps"] >= 1        # authentication + matched-normal missing
    assert len(r["fixes"]) == r["n_gaps"]
    # refusal is explicit about no patient prediction / no patient data
    assert "patient" in r["refusal"].lower()


def test_organoid_score_low_risk_on_rigorous_study():
    full = {key: True for key, *_ in ORGANOID_RIGOR}
    r = score_organoid_study(full)
    assert r["verdict"] == "low"
    assert r["n_gaps"] == 0 and r["fixes"] == []


def test_assess_frontier_composes_active_evidence_rigor():
    corpus = json.loads(
        (_ROOT / "examples" / "frontier_corpora" / "phage_pseudomonas.json").read_text())
    r = assess_frontier("phage_design",
                        genes=["capsid", "stx2", "integrase"],
                        records=corpus["records"], question=corpus["question"])
    assert r["active"]["verdict"] == "no-go"
    assert r["evidence"]["report"]["hits"]          # >= 1 literature pattern
    assert len(r["rigor_checklist"]) >= 5
    assert len(r["refuses"]) >= 2


def test_phage_refuses_treatment_prediction_explicitly():
    """The phage-therapy brief asks to 'predict the optimal phage combination'.
    Keystone must refuse that clinical recommendation on the record."""
    r = assess_frontier("phage_design", genes=["capsid", "tail fiber"])
    joined = " ".join(r["refuses"]).lower()
    assert "predict" in joined and "phage" in joined
    assert "prescribe" in joined or "clinician" in joined or "irb" in joined


def test_aging_clock_scores_rigor_and_benchmarks_published_clocks():
    r = assess_frontier("aging_clock",
                        study={"clock_selection_justified": True,
                               "batch_corrected": True})
    a = r["active"]
    assert a["input_kind"] == "aging_study"
    assert a["verdict"] == "high"                 # a critical item is missing
    assert a["critical_gaps"] >= 1
    # the published-clock benchmark table is real + cited
    clocks = {c["clock"] for c in a["benchmark_clocks"]}
    assert "Horvath multi-tissue" in clocks and "GrimAge" in clocks
    assert all(c["citation"] for c in a["benchmark_clocks"])


def test_aging_clock_refuses_patient_computation():
    r = assess_frontier("aging_clock", study={})
    joined = (" ".join(r["refuses"]) + " " + r["active"]["refusal"]).lower()
    assert "biological age" in joined
    assert "patient" in joined and ("phi" in joined or "scrna" in joined)


def test_aging_clock_low_risk_on_rigorous_study():
    full = {key: True for key, *_ in AGING_RIGOR}
    r = score_aging_study(full)
    assert r["verdict"] == "low" and r["n_gaps"] == 0


def test_unknown_frontier_is_refused():
    r = assess_frontier("design_a_virus")
    assert r["refused"] is True
    assert "unknown frontier" in r["reason"].lower()
    # catalogue lists exactly the THREE supported frontiers, never the unsafe one
    fr = {c["frontier"] for c in frontier_catalogue()}
    assert fr == {"phage_design", "organoid_response", "aging_clock"}


if __name__ == "__main__":
    test_phage_vet_flags_toxin_gene_as_no_go()
    test_phage_vet_flags_lysogeny_and_amr()
    test_phage_vet_clean_lytic_with_host_range_is_go()
    test_phage_vet_clean_without_host_range_is_caution()
    test_organoid_score_high_risk_on_gappy_study()
    test_organoid_score_low_risk_on_rigorous_study()
    test_assess_frontier_composes_active_evidence_rigor()
    test_unknown_frontier_is_refused()
    print("all frontier-guard tests passed")
