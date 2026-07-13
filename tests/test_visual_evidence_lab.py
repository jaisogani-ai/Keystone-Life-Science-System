"""
Visual Evidence Lab acceptance tests — the honesty contract for the Cell-State Atlas.

  1. atlas coordinates originate from a real run or a clearly labeled fixture
  2. selected clusters link to real claim/node ids and run ids
  3. synthetic/illustrative visuals cannot become ranking evidence
  4. a missing visual dataset produces an honest disabled/empty state
  5. every visual panel displays provenance
  6. visual interaction produces a real (logged) state change
  7. export includes dataset/model/code/run metadata for the atlas
  8. no clinical diagnosis or patient-specific claim is possible
"""
import io
import json
import zipfile

import pytest

from keystone.ml.cell_atlas import compute_atlas, cluster_detail
from keystone.deterministic.target_ranking import rank_targets


# 1 --------------------------------------------------------------------------
def test_atlas_coordinates_come_from_a_clearly_labeled_run():
    a = compute_atlas("tcell")
    assert a["available"] and a["cells"]
    # the matrix is synthetic and MUST say so, with a reproducible receipt
    assert a["data_kind"] == "synthetic"
    assert "SYNTHETIC" in a["data_label"] and "illustrative" in a["data_label"].lower()
    repro = a["reproducibility"]
    assert repro["seed"] and repro["code_hash"] and repro["data_version"]
    assert a["run_id"].startswith("atlas_")


# 2 --------------------------------------------------------------------------
def test_selected_cluster_links_to_real_node_and_run_ids():
    real_nodes = {r["gene"]: r["node_id"] for r in rank_targets()["ranking"]}
    d = cluster_detail("tcell", "GATA3")
    assert d["found"]
    assert d["detail"]["linkage"]["node_id"] == real_nodes["GATA3"]
    assert d["detail"]["linkage"]["rank"] == next(
        r["rank"] for r in rank_targets()["ranking"] if r["gene"] == "GATA3")
    assert d["selection_run_id"].startswith("atlas_")
    assert d["atlas_run_id"].startswith("atlas_")


# 3 --------------------------------------------------------------------------
def test_illustrative_visuals_cannot_become_ranking_evidence():
    a = compute_atlas("tcell")
    assert all(arm["affects_ranking"] is False for arm in a["arms"])
    # and the Research Cell reviewer must reject the atlas claim from ranking support
    from keystone.deterministic.research_cell_run import run_research_cell
    r = run_research_cell("tcell")
    admitted = {c["id"] for c in r["admitted_to_ranking"]}
    rejected = {c["id"] for c in r["rejected"]}
    assert "atlas:embedding" not in admitted
    assert "atlas:embedding" in rejected


# 4 --------------------------------------------------------------------------
def test_missing_visual_dataset_is_an_honest_disabled_state():
    a = compute_atlas("gbm")
    assert a["available"] is False
    assert a["cells"] == [] and a["arms"] == []
    assert "tcell" in a["note"] or "T-cell" in a["note"]


# 5 --------------------------------------------------------------------------
def test_every_visual_panel_shows_provenance():
    a = compute_atlas("tcell")
    assert a["provenance_tag"] and a["does_not_prove"] and a["not_clinical"]
    for arm in a["arms"]:
        assert arm["computed"]["label"].startswith("Computed analysis")
        assert "affects_ranking" in arm
        if arm["measured"] is not None:
            assert arm["measured"]["label"] == "Measured data"
            assert arm["measured"]["source"].startswith("DOI:")
        if arm["linkage"] is not None:
            assert arm["linkage"]["label"] == "Literature-backed biology"


# 6 --------------------------------------------------------------------------
def test_selection_triggers_a_real_logged_state_change():
    g = cluster_detail("tcell", "GATA3")
    s = cluster_detail("tcell", "STAT6")
    # each selection is a distinct, content-addressed server computation
    assert g["selection_run_id"] != s["selection_run_id"]
    assert g["selection_run_id"] != g["atlas_run_id"]
    # and it returns freshly computed per-arm stats (not a static blob)
    assert g["detail"]["computed"]["delta_vs_control"] != s["detail"]["computed"]["delta_vs_control"]


# 7 --------------------------------------------------------------------------
def test_export_includes_atlas_dataset_model_code_run_metadata():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    import keystone.ui.server as server
    from keystone.decision_engine import decide
    from keystone.agents.reasoner import HeuristicReasoner
    server._DECISION_CACHE["tcell"] = decide("tcell", reasoner=HeuristicReasoner())
    client = TestClient(server.app)
    r = client.get("/api/export/bundle?domain=tcell")
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert "atlas-run.json" in z.namelist()
    m = json.loads(z.read("atlas-run.json"))
    for k in ("run_id", "data_kind", "data_label", "embedding", "reproducibility", "arms"):
        assert k in m, f"atlas-run.json missing {k}"
    assert m["reproducibility"]["code_hash"]


# 8 --------------------------------------------------------------------------
def test_no_clinical_or_patient_claim_is_possible():
    a = compute_atlas("tcell")
    d = cluster_detail("tcell", "FBXO32")
    # the atlas carries an explicit non-clinical disclaimer
    assert "Not a clinical" in a["not_clinical"]
    assert "Not a clinical" in d["not_clinical"]
    # and the data-bearing panels contain no clinical/diagnostic language
    forbidden = ["diagnos", "patient", "tumor", "radiolog", "lesion", "treatment plan"]
    blob = (json.dumps(a["arms"]) + json.dumps(d["detail"])).lower()
    for term in forbidden:
        assert term not in blob, f"clinical term '{term}' leaked into atlas data"


# Regulator Effect Map — the PRIMARY, real measured-data layer -----------------
def test_regulator_map_is_real_measured_data_not_synthetic():
    from keystone.ml.cell_atlas import regulator_map
    from keystone import gladstone_data
    m = regulator_map("tcell")
    assert m["available"] and m["provenance_tag"] == "Measured data"
    assert m["source"] == f"DOI:{gladstone_data.provenance()['doi']}"
    # every point's numbers come verbatim from the pinned Gladstone metrics
    real = gladstone_data.all_regulator_effects()
    for p in m["points"]:
        e = real[p["gene"]]
        assert p["n_downstream_de"] == e["n_downstream"]
        assert p["ontarget_kd"] == e["ontarget_effect_size"]


def test_map_flags_fbxo32_provisional_by_measured_reproducibility():
    from keystone.ml.cell_atlas import regulator_map
    pts = {p["gene"]: p for p in regulator_map("tcell")["points"]}
    # FBXO32: low cross-donor r → provisional (the measured reason it is fragile)
    assert pts["FBXO32"]["provisional"] is True
    assert pts["FBXO32"]["crossdonor_r"] < 0.3
    # STAT6 / GATA3 replicate across donors → not provisional
    assert pts["STAT6"]["provisional"] is False
    assert pts["GATA3"]["provisional"] is False
    # RARA has no measured cross-donor r → honestly marked, never faked
    assert pts["RARA"]["reproducibility_missing"] is True
    assert pts["RARA"]["crossdonor_r"] is None


def test_regulator_map_points_link_to_the_real_ranking():
    from keystone.ml.cell_atlas import regulator_map
    from keystone.deterministic.target_ranking import rank_targets
    ranks = {r["gene"]: (r["rank"], r["node_id"]) for r in rank_targets()["ranking"]}
    for p in regulator_map("tcell")["points"]:
        assert (p["rank"], p["node_id"]) == ranks[p["gene"]]


# workflow smoke: the atlas endpoints must not 500
def test_atlas_endpoints_run_without_a_500():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient
    import keystone.ui.server as server
    client = TestClient(server.app, raise_server_exceptions=False)
    for p in ("/api/atlas?domain=tcell", "/api/atlas/select?domain=tcell&arm=GATA3",
              "/api/atlas?domain=gbm", "/api/atlas/select?domain=tcell&arm=NOPE",
              "/api/regulator_map?domain=tcell", "/api/regulator_map?domain=gbm"):
        assert client.get(p).status_code == 200, f"{p} did not return 200"
