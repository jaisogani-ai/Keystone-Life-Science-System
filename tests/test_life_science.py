"""
Life-science surfaces: Research Integrity Center, Scientific Notebook, Biology
Chain, Computer Vision Lab (with the CV refusal boundary), Live AI Debate. All
compose existing real modules; nothing fabricated. Offline.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

from keystone.integrity_center import run_integrity_center           # noqa: E402
from keystone.notebook import build_notebook, make_comment           # noqa: E402
from keystone.biology_chain import build_biology_chain               # noqa: E402
from keystone.cv_lab import analyze, modality_catalogue, REFUSED, SUPPORTED  # noqa: E402
from keystone.live_debate import run_debate                          # noqa: E402


def test_integrity_center_composes_real_checks():
    d = run_integrity_center("gbm")
    by = {c["name"]: c for c in d["checks"]}
    # real checks catch the real problems
    assert by["Cell Authentication"]["status"] == "fail"     # U-87MG misidentified
    assert by["Publication Validation"]["status"] == "fail"  # retracted foundation
    assert by["Protocol Validation"]["status"] in ("pass", "warn")
    # tier-2 checks are honest, never silently passed
    assert by["Dataset Validation"]["status"] == "not_wired"
    assert by["Antibody Validation"]["status"] == "not_wired"


def test_notebook_has_all_six_sections_pinned_to_the_run():
    nb = build_notebook("gbm")
    s = nb["sections"]
    assert set(s) == {"protocol", "evidence", "comments", "reviewer",
                      "version_history", "publication"}
    assert s["protocol"]["kill_condition"].strip()
    assert all(e["source"] for e in s["evidence"])
    assert s["publication"]["reproducibility_hash"] == nb["graph_hash"]
    c = make_comment("Dr. X", "check the reagent", nb["graph_hash"])
    assert c["author"] == "Dr. X" and c["pinned_to_hash"] == nb["graph_hash"]


def test_biology_chain_links_real_connectors():
    d = build_biology_chain("gbm")
    layers = [l["layer"] for l in d["chain"]]
    assert layers == ["Cell", "Protein", "Mutation", "Drug", "Pathway",
                      "Disease", "Trial"]
    assert all(l["source"] for l in d["chain"])
    # true spatial-omics is honestly Tier 3, not faked
    assert d["spatial_omics"]["status"] == "not_wired"


def test_cv_lab_refuses_measurement_extraction():
    """The integrity boundary: microscopy/CryoEM/blot measurement is refused."""
    for m in ("microscopy", "cryoem", "western_blot", "histology", "radiology"):
        r = analyze(m)
        assert r["refused"] and "reason" in r      # honest refusal, no detection
    assert set(REFUSED) & {"microscopy", "cryoem", "western_blot"}


def test_cv_lab_supports_pathway_figures_without_fabricating_offline():
    r = analyze("pathway_figure", claim="CTSB is central")
    # supported modality, but offline it refuses to invent an interpretation
    assert r.get("requires_live_vision") is True
    assert "pathway_figure" in SUPPORTED


def test_live_debate_multi_role_consensus_by_evidence_not_voting():
    d = run_debate("gbm")
    roles = [t["role"] for t in d["turns"]]
    assert roles == ["Bioinformatics", "Cancer Biology", "Reviewer", "PI"]
    assert d["consensus"]["method"] == "explicit evidence, not voting"
    assert d["consensus"]["human_gated"] is True


def test_life_science_endpoints():
    from fastapi.testclient import TestClient
    from keystone.ui import server
    c = TestClient(server.app)
    assert c.get("/labs").status_code == 200
    assert c.get("/api/integrity?domain=gbm").json()["checks"]
    assert c.get("/api/notebook?domain=gbm").json()["sections"]
    assert c.get("/api/biology_chain?domain=gbm").json()["chain"]
    assert c.get("/api/cv/catalogue").json()["modalities"]
    assert c.get("/api/debate?domain=gbm").json()["turns"]
    # CV refusal over the endpoint
    assert c.post("/api/cv/analyze", json={"modality": "microscopy"}).json()["refused"]
    # notebook comment write-back
    r = c.post("/api/notebook/comment",
               json={"domain": "gbm", "author": "PI", "text": "verify line",
                     "graph_hash": "h"})
    assert r.status_code == 200 and r.json()["author"] == "PI"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all life-science tests passed")
