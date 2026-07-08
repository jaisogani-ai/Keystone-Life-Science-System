"""
Connector + real-data-graph + calibration tests. All offline against pinned real
fixtures (KEYSTONE_OFFLINE=1), so they are deterministic and need no network.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"   # force cache/fixtures, never the network

from keystone.connectors import registry as R          # noqa: E402
from keystone.data_gbm import build_gbm_graph           # noqa: E402
from keystone import gbm_spec as SPEC                    # noqa: E402


def test_foundation_is_a_real_retracted_paper():
    w = R.openalex_work(SPEC.FOUNDATION["openalex"])
    assert w["resolved"] and w["is_retracted"] is True
    assert w["doi"].endswith("sj.onc.1207616")


def test_retraction_watch_provenance_is_real():
    ret = R.retraction_status(SPEC.FOUNDATION["doi"])
    assert ret["is_retracted"] and ret["retraction_date"] == "2025-04-29"
    assert ret["via"] == "retraction-watch" and str(ret["record_id"]) == "64194"


def test_cellosaurus_flags_the_misidentified_line():
    cl = R.cellosaurus_line(SPEC.REAGENT["cellosaurus"])
    assert cl["resolved"] and "U-87MG" in cl["name"]
    assert cl["problematic"] and "isidentified" in cl["problematic"]


def test_uniprot_target_resolves_with_structure():
    up = R.uniprot_protein(SPEC.TARGET["uniprot"])
    assert up["resolved"] and up["gene"] == "CTSB"
    assert up["pdb_ids"]


def test_connector_never_fabricates_on_miss():
    """Determinism boundary: an unknown id is 'unresolved', not invented."""
    miss = R.openalex_work("W0000000000")
    assert miss["resolved"] is False and miss["source"] == "unresolved"


def test_graph_built_from_real_dois_and_is_reproducible():
    g1 = build_gbm_graph()
    g2 = build_gbm_graph()
    assert g1.snapshot_hash() == g2.snapshot_hash()
    # foundation node carries a real DOI and is retracted with full doubt
    f = g1.nodes["N_foundation"]
    assert "10.1038/sj.onc.1207616" in f.source and f.retracted
    assert f.doubt.point == 1.0
    # every resolved node's provenance is a real identifier, never fabricated
    for n in g1.nodes.values():
        assert n.source and n.source != "unresolved"


def test_real_citing_sentences_are_attached():
    g = build_gbm_graph()
    cites = [e for e in g.edges if e.edge_type.value == "cites"]
    resolved = [e for e in cites if not e.context.startswith("unresolved")]
    assert resolved, "expected at least one real citing sentence on a cites edge"


def test_post_retraction_citer_is_flagged_inexcusable():
    g = build_gbm_graph()
    dep_c = g.nodes["N_dep_C"]
    assert dep_c.date > "2025-04-29"          # cited after retraction
    # after a run the inexcusable flag drives its doubt toward saturation
    from keystone.workbench import run
    from keystone.agents.reasoner import HeuristicReasoner
    run("Q", g, HeuristicReasoner())
    assert g.nodes["N_dep_C"].inexcusable and g.nodes["N_dep_C"].doubt.point >= 0.9


def test_calibration_beats_a_coin_flip():
    import calibrate
    from keystone.agents.reasoner import HeuristicReasoner
    rows = calibrate.load_labeled()
    assert len(rows) >= 30, "calibration set should have >=30 real sentences"
    res = calibrate.evaluate(HeuristicReasoner(), rows)
    assert res["accuracy"] > 0.5, "the moat must beat a coin flip"


def test_renderers_emit_svg():
    from keystone.artifacts.render import evidence_graph_svg, timeline_svg
    from keystone.workbench import run
    from keystone.agents.reasoner import HeuristicReasoner
    g = build_gbm_graph()
    ledger, _, _ = run("Q", g, HeuristicReasoner())
    assert evidence_graph_svg(g).startswith("<svg")
    assert timeline_svg(ledger.timeline).startswith("<svg")


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all connector tests passed")
