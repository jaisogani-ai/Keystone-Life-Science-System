"""
Discovery OS tests — the new Tier-1 surfaces. All offline against pinned real
fixtures. Verifies: real clinical connectors resolve (and honestly return zero,
never fabricate), contradiction mining + gap detection are deterministic passes,
scientific memory answers "tried before", and the workspace is tier-honest.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

import json  # noqa: E402

from keystone.connectors import clinical as C                 # noqa: E402
from keystone.workspace import build_workspace                 # noqa: E402
from keystone.deterministic.contradiction_mining import mine_contradictions  # noqa: E402
from keystone.deterministic.gap_detection import detect_gaps   # noqa: E402
from keystone.deterministic.ledger_index import LedgerIndex    # noqa: E402
from keystone.data_gbm import build_gbm_graph                  # noqa: E402
from keystone.workbench import run                             # noqa: E402
from keystone.agents.reasoner import HeuristicReasoner         # noqa: E402


# --- Tier-1 real connectors -------------------------------------------------
def test_clinical_trials_are_real():
    t = C.clinical_trials("glioblastoma")
    assert t["resolved"] and t["total"] and int(t["total"]) > 100
    assert t["trials"][0]["nct_id"].startswith("NCT")


def test_chembl_returns_honest_zero_not_a_fabrication():
    """Cathepsin B has no approved drug — resolved:true, empty list, count 0."""
    d = C.chembl_drugs("cathepsin B")
    assert d["resolved"] and d["target_name"] == "Cathepsin B"
    assert d["count"] == 0 and d["drugs"] == []
    # ...while a druggable target really returns drugs
    ins = C.chembl_drugs("insulin receptor")
    assert ins["resolved"] and ins["count"] > 0 and ins["drugs"]


def test_reactome_and_clinvar_resolve():
    p = C.reactome_pathways("P07858")
    assert p["resolved"] and p["count"] >= 1 and p["pathways"][0]["st_id"].startswith("R-")
    v = C.clinvar_variants("CTSB")
    assert v["resolved"] and int(v["total"]) > 10 and v["variants"]


def test_connectors_never_fabricate_on_miss():
    miss = C.clinvar_variants("NOTAREALGENE123")
    assert miss["resolved"] is False and miss["source"] == "unresolved"


# --- Named deterministic loop stages ---------------------------------------
def test_contradiction_mining_surfaces_the_contradiction():
    g = build_gbm_graph()
    run("Q", g, HeuristicReasoner())
    cons = mine_contradictions(g)
    assert cons and cons[0]["against"] == "N_foundation"
    assert cons[0]["opportunity"] is True         # contradicts a retracted node


def test_gap_detection_counts_real_absences():
    g = build_gbm_graph()
    _, hyp, review = run("Q", g, HeuristicReasoner())
    gaps = detect_gaps(hyp, review, g)
    assert gaps["stage"] == "gap_detection" and isinstance(gaps["gaps"], list)


# --- Scientific memory (ledger index) --------------------------------------
def test_ledger_index_finds_prior_work(tmp_path):
    g = build_gbm_graph()
    ledger, hyp, review = run("Q", g, HeuristicReasoner())
    (tmp_path / "run1.json").write_text(ledger.to_json())

    idx = LedgerIndex().load_dir(tmp_path)
    assert len(idx) == 1
    res = idx.find_prior_work(sources=ledger.sources,
                              grounding=ledger.hypothesis_grounding,
                              graph_hash=ledger.graph_hash)
    assert res["tried_before"] and res["matches"][0]["exact_reproduction"]

    # a disjoint evidence base is NOT reported as prior work
    novel = idx.find_prior_work(sources=["DOI:10.9999/nonexistent"], grounding=[])
    assert novel["tried_before"] is False


# --- Workspace is tier-honest ----------------------------------------------
def test_workspace_is_tier_tagged_and_never_fabricates(tmp_path):
    ws, g, ledger, hyp, review = build_workspace("gbm")
    tabs = ws["tabs"]
    # every tab declares a tier
    assert all("tier" in t for t in tabs.values())
    # Tier-2 tabs are explicitly incomplete, never silently empty
    for name in ("genes", "datasets"):
        assert tabs[name]["tier"] == 2 and tabs[name]["status"] == "not_yet_wired"
    # Tier-1 clinical tabs carry real data
    assert tabs["clinical_trials"]["data"]["total"]
    # honest zero: undrugged target is resolved with an empty list, not faked
    kd = tabs["known_drugs"]["data"]
    assert kd["resolved"] and kd["count"] == 0
    # workspace is reproducible
    ws2, *_ = build_workspace("gbm")
    assert ws2["graph_hash"] == ws["graph_hash"]
    json.dumps(ws)          # fully JSON-serializable for the UI


if __name__ == "__main__":
    import tempfile, pathlib
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except TypeError:
                fn(pathlib.Path(tempfile.mkdtemp()))
            print(f"  ok  {name}")
    print("all discovery-os tests passed")
