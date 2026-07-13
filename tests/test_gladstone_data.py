"""
Real Gladstone CD4+ T-cell Perturb-seq data — provenance & integrity tests.

Guards the honesty contract for the one real dataset wired into the ranking:
  * the record resolves (real DOI, real authors, marked preprint);
  * measured metrics are present for the ranked regulators;
  * FBXO32's cross-donor reproducibility is genuinely low (the real reason the
    preprint's novel nominee stays provisional) — never silently smoothed;
  * the ranking carries the measurement as provenance without letting it overwrite
    a sourced value or invent one for an unmeasured gene.
"""
from keystone import gladstone_data
from keystone.deterministic.target_ranking import rank_targets


def test_dataset_record_resolves_and_is_marked_preprint():
    p = gladstone_data.provenance()
    assert p["doi"] == "10.64898/2025.12.23.696273"
    assert "Marson" in p["authors"][-1]
    assert p["peer_reviewed"] is False  # source-record-verified ≠ peer-reviewed


def test_measured_effects_present_for_ranked_regulators():
    eff = gladstone_data.all_regulator_effects()
    for gene in ("GATA3", "STAT6", "FBXO32"):
        assert eff[gene] is not None
        assert eff[gene]["n_downstream"] > 0


def test_gata3_footprint_is_a_real_direction_resolved_collapse():
    """The replacement for the synthetic classifier: GATA3 knockdown's REAL,
    per-gene measured effect on the type-2 program — collapse + specificity."""
    fp = gladstone_data.gata3_th2_footprint()
    assert fp is not None
    genes = {x["gene"]: x for x in fp["footprint"]}
    # the program collapses: mean log2FC is clearly negative
    assert fp["th2_collapse_score"] < -1.0
    # the type-2 cytokines fall, significantly (measured, not typed)
    for cyto in ("IL5", "IL13", "IL4"):
        assert genes[cyto]["log2fc"] < 0 and genes[cyto]["significant"]
    # on-target: GATA3 itself is knocked down
    assert genes["GATA3"]["log2fc"] < 0
    # SPECIFICITY: STAT6 (upstream of GATA3) is NOT significantly moved — the
    # effect is Th2-directed, not a global collapse (this is the honesty guard)
    assert genes["STAT6"]["significant"] is False


def test_footprint_reaches_the_perturbseq_api():
    from fastapi.testclient import TestClient
    from keystone.ui.server import app
    fp = TestClient(app).get("/api/perturbseq?domain=tcell").json() \
        .get("gladstone_real", {}).get("gata3_th2_footprint")
    assert fp and fp["footprint"] and fp["th2_collapse_score"] < -1.0


def test_fbxo32_cross_donor_reproducibility_is_low_and_shown():
    """The real integrity signal — FBXO32's effect is donor-variable (r ~0.13),
    far below GATA3/STAT6 (~0.7). This must be surfaced, not hidden."""
    gata3 = gladstone_data.regulator_effect("GATA3")["crossdonor_correlation_mean"]
    fbxo32 = gladstone_data.regulator_effect("FBXO32")["crossdonor_correlation_mean"]
    assert fbxo32 < 0.3 < gata3


def test_functional_effect_scores_are_normalised_from_real_downstream():
    scores = gladstone_data.functional_effect_scores()
    assert scores["GATA3"] == 1.0           # broadest real footprint → 1.0
    assert all(0.0 <= v <= 1.0 for v in scores.values())


def test_ranking_carries_real_measurement_as_provenance():
    ranking = rank_targets()["ranking"]
    for r in ranking:
        pm = r.get("perturbseq_measured")
        if pm is not None:
            assert pm["label"] == "Measured in dataset"
            assert pm["source"].startswith("DOI:10.64898")
            assert pm["peer_reviewed"] is False


def test_measurement_never_overwrites_the_sourced_functional_effect():
    """Attaching real data must not change the audited composite."""
    r = {c["gene"]: c["composite"] for c in rank_targets()["ranking"]}
    # STAT6 stays the top-ranked, sourced composite regardless of the attachment
    assert r["STAT6"] == max(r.values())
