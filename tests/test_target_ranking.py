"""
Target Trust release-gate tests — the 8-component ranking contract, the exact
provenance labels, the exposed weights (no opaque score), the degrader-honesty
labels, and the counterfactual recompute.
"""
from keystone.deterministic.target_ranking import (
    rank_targets, WEIGHTS, EVIDENCE_LABELS, TRACTABILITY_LABELS)

_PREPRINT = "https://www.biorxiv.org/content/10.64898/2025.12.23.696273v1"
_EIGHT = {"functional_effect", "activation_specificity", "type2_pathway",
          "disease_relevance", "tractability", "safety_risk", "integrity_risk",
          "missing_evidence"}


def test_every_candidate_exposes_all_eight_components():
    for c in rank_targets()["ranking"]:
        assert set(c["components"]) == _EIGHT, c["gene"]


def test_every_component_carries_an_exact_provenance_label():
    for c in rank_targets()["ranking"]:
        for key, comp in c["components"].items():
            if key == "missing_evidence":
                continue
            assert comp["label"] in EVIDENCE_LABELS or comp["label"] in TRACTABILITY_LABELS, \
                (c["gene"], key, comp["label"])
            # every component is self-describing (spec contract)
            for field in ("source", "formula", "input", "version", "uncertainty", "limitation"):
                assert comp.get(field), (c["gene"], key, field)


def test_tractability_uses_only_the_allowed_degrader_labels():
    for c in rank_targets()["ranking"]:
        assert c["components"]["tractability"]["label"] in TRACTABILITY_LABELS


def test_composite_is_a_weighted_sum_with_weights_shown():
    out = rank_targets()
    assert out["weights"] == WEIGHTS                      # weights exposed, not hidden
    for c in out["ranking"]:
        assert "weighted_parts" in c and len(c["weighted_parts"]) == len(WEIGHTS)
        # composite ≈ sum of the shown weighted parts (auditable, not opaque)
        assert abs(c["composite"] - sum(c["weighted_parts"].values())) < 1e-6


def test_excluding_the_preprint_recomputes_the_ranking():
    before = {c["gene"]: c["composite"] for c in rank_targets()["ranking"]}
    after_out = rank_targets(excluded_sources=[_PREPRINT])
    after = {c["gene"]: c["composite"] for c in after_out["ranking"]}
    # FBXO32 rests on the preprint → its composite must drop when it is excluded
    assert after["FBXO32"] < before["FBXO32"]
    # and its preprint-backed components become Unknown / insufficient evidence
    # (functional_effect is now COMPUTED by the pipeline, so the preprint-sourced
    # components are activation_specificity / type2_pathway)
    fbxo32 = next(c for c in after_out["ranking"] if c["gene"] == "FBXO32")
    assert fbxo32["components"]["activation_specificity"]["label"] == "Unknown / insufficient evidence"
    assert fbxo32["components"]["type2_pathway"]["label"] == "Unknown / insufficient evidence"


def test_excluding_by_the_preprint_token_matches_excluding_by_url():
    """The counterfactual must be robust to whichever handle a caller uses to
    exclude the preprint — the concrete URL or the human-facing ``PREPRINT`` token
    surfaced in the source field. Both must recompute identically (no silent no-op)."""
    by_url = {c["gene"]: c["composite"]
              for c in rank_targets(excluded_sources=[_PREPRINT])["ranking"]}
    by_token = {c["gene"]: c["composite"]
                for c in rank_targets(excluded_sources=["PREPRINT"])["ranking"]}
    baseline = {c["gene"]: c["composite"] for c in rank_targets()["ranking"]}
    assert by_token == by_url
    assert by_token["FBXO32"] < baseline["FBXO32"]


def test_exclusion_is_robust_to_every_canonical_doi_form():
    """Red-to-green audit fix: excluding the preprint by ANY canonical handle — the
    bioRxiv URL, the bare DOI, a ``DOI:`` prefix, a ``doi.org`` URL, or the token —
    must recompute identically. Before the id-normalization fix, only the exact URL
    matched and the canonical DOI silently no-op'd."""
    forms = [
        _PREPRINT,
        "10.64898/2025.12.23.696273",
        "DOI:10.64898/2025.12.23.696273",
        "https://doi.org/10.64898/2025.12.23.696273",
        "PREPRINT",
    ]
    baseline = next(c["composite"] for c in rank_targets()["ranking"] if c["gene"] == "FBXO32")
    results = {round(next(c["composite"] for c in rank_targets(excluded_sources=[f])["ranking"]
                          if c["gene"] == "FBXO32"), 6) for f in forms}
    assert len(results) == 1, f"id forms diverged: {results}"
    assert results.pop() < baseline, "every form must drop FBXO32"
    # a bogus id must NOT match anything (no false-positive exclusion)
    bogus = next(c["composite"] for c in rank_targets(excluded_sources=["DOI:10.9999/nope"])["ranking"]
                 if c["gene"] == "FBXO32")
    assert bogus == baseline


def test_custom_weights_reorder_normalize_and_never_mutate_components():
    """A scientist can re-weight the components and watch the ranking recompute —
    transparently. Weights renormalize to 1.0, invalid input falls back to defaults,
    weights compose with exclusion, and re-weighting NEVER changes a component's
    underlying evidence value or label (only how much it counts)."""
    base = rank_targets()
    assert base["weights_customized"] is False
    # crank functional_effect → GATA3 (highest measured effect) rises past RARA
    up = rank_targets(weights={"functional_effect": 0.85})
    assert up["weights_customized"] is True
    assert abs(sum(up["weights"].values()) - 1.0) < 1e-6
    base_order = [r["gene"] for r in base["ranking"]]
    up_order = [r["gene"] for r in up["ranking"]]
    assert base_order != up_order, "re-weighting must be able to reorder"
    # invalid / unknown weights → defaults (not customized)
    assert rank_targets(weights={"bogus": 9, "functional_effect": "x"})["weights_customized"] is False
    # composes with exclusion
    combo = rank_targets(excluded_sources=["PREPRINT"], weights={"integrity": 0.4})
    assert combo["weights_customized"] is True
    # components (evidence) are untouched by re-weighting
    b = {c["gene"]: c["components"] for c in base["ranking"]}
    u = {c["gene"]: c["components"] for c in up["ranking"]}
    for g in b:
        for k in ("functional_effect", "tractability", "integrity_risk"):
            assert b[g][k]["value"] == u[g][k]["value"]
            assert b[g][k]["label"] == u[g][k]["label"]


def test_no_trained_model_or_causal_claim_is_made():
    note = rank_targets()["note"].lower()
    assert "not a trained model" in note and "causal" in note
