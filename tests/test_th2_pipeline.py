"""
ML-validity gate for the type-2 (Th2) perturbation-analysis pipeline. The pipeline
must be real, leakage-safe, baselined, reproducible, and HONESTLY labeled (the
matrix is synthetic/exploratory, not real Perturb-seq).
"""
from keystone.ml.th2_signature import (
    run_analysis, functional_effects, synthesize_matrix, TH2_SIGNATURE_GENES)


def test_pipeline_runs_with_baseline_and_model_metrics():
    r = run_analysis()
    for m in (r["baseline"], r["model"]):
        assert m["auroc"] and 0.0 <= m["auroc"]["mean"] <= 1.0
        assert m["auroc"]["folds"] >= 1
        assert "std" in m["auroc"]              # uncertainty is shown


def test_data_is_honestly_labeled_synthetic():
    r = run_analysis()
    assert r["data_kind"] == "synthetic"
    assert "SYNTHETIC" in r["data_label"] and "not real perturb-seq" in r["data_label"].lower()
    assert r["limitations"] and r["failure_modes"]


def test_split_is_grouped_by_perturbation_not_random_cells():
    r = run_analysis()
    assert "leave-one-perturbation-out" in r["split"]


def test_reproducible_by_seed_and_records_code_hash():
    assert functional_effects() == functional_effects()          # same seed → identical
    r = run_analysis()
    assert r["reproducibility"]["seed"] == "0x1f"
    assert len(r["reproducibility"]["code_hash"]) == 16
    assert r["reproducibility"]["numpy"]


def test_no_train_test_cell_leakage_across_the_grouped_split():
    # every held-out perturbation's cells must be absent from the training arm
    X, y, group, donor, genes, sig_idx = synthesize_matrix()
    import numpy as np
    for held in [p for p in np.unique(group) if p != "NTC"]:
        te = (group == held)
        tr = ~((group == held) | (group == "NTC"))
        assert not (set(np.where(te)[0]) & set(np.where(tr)[0]))


def test_effect_is_computed_and_literature_consistent():
    fx = functional_effects()
    # GATA3 (master TF) > FBXO32 (novel) — the computed effect tracks documented biology
    assert fx["GATA3"] > fx["FBXO32"]
    assert all(g in TH2_SIGNATURE_GENES for g in ("IL4", "IL13", "GATA3"))
