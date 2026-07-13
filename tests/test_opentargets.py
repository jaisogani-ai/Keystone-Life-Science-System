"""Open Targets connector: real disease-association scores, offline from pinned
fixtures, wired into the target ranking's disease-relevance component."""
import os

from keystone.connectors.opentargets import type2_association
from keystone.deterministic.target_ranking import rank_targets

os.environ.setdefault("KEYSTONE_OFFLINE", "1")  # deterministic: fixtures only


def test_connector_returns_real_type2_scores_from_fixtures():
    gata3 = type2_association("GATA3")
    assert gata3 is not None and gata3["source"] == "Open Targets"
    assert 0.0 < gata3["score"] <= 1.0
    assert "asthma" in (gata3["disease"] or "").lower()
    assert gata3["disease_id"]  # a real ontology id (MONDO/EFO/HP)


def test_gene_with_no_type2_association_resolves_to_zero_not_fabricated():
    fbxo32 = type2_association("FBXO32")
    assert fbxo32 is not None
    assert fbxo32["score"] == 0.0
    assert fbxo32["disease"] is None
    assert "no type-2" in fbxo32["note"].lower()


def test_unknown_gene_returns_none_never_fabricates():
    assert type2_association("NOT_A_GENE") is None


def test_ranking_disease_relevance_is_sourced_from_open_targets():
    ranking = rank_targets()["ranking"]
    for cand in ranking:
        dr = cand["components"]["disease_relevance"]
        assert "Open Targets" in dr["source"]
        assert dr["label"] == "Literature-supported"
    # FBXO32's real 0.0 type-2 association is a meaningful negative signal
    fbxo32 = next(c for c in ranking if c["gene"] == "FBXO32")
    assert fbxo32["components"]["disease_relevance"]["value"] == 0.0
