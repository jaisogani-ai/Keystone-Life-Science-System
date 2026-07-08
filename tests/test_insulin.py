"""
Second-domain (insulin) tests — proves the pipeline is domain-agnostic on REAL
data with a second calibration number, and that the honest asymmetry holds (clean
foundation, real retracted dependent). Offline against pinned real fixtures.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

from keystone.connectors import registry as R           # noqa: E402
from keystone.data_insulin import build_insulin_graph    # noqa: E402
from keystone import insulin_spec as SPEC                 # noqa: E402


def test_foundation_is_real_and_honestly_not_retracted():
    w = R.openalex_work(SPEC.FOUNDATION["openalex"])
    ret = R.retraction_status(SPEC.FOUNDATION["doi"])
    assert w["resolved"] and w["doi"].endswith("414799a")
    assert w["is_retracted"] is False and ret["is_retracted"] is False


def test_retracted_dependent_is_real():
    """The compromised node is a real RETRACTED citer, not a fabricated one."""
    ret = R.retraction_status("10.1172/jci81480")
    assert ret["is_retracted"] and ret["via"] == "retraction-watch"


def test_target_is_irs1():
    up = R.uniprot_protein(SPEC.TARGET["uniprot"])
    assert up["resolved"] and up["gene"] == "IRS1" and up["pdb_ids"]


def test_graph_real_dois_reproducible_no_fabrication():
    g1 = build_insulin_graph()
    g2 = build_insulin_graph()
    assert g1.snapshot_hash() == g2.snapshot_hash()
    assert g1.nodes["N_foundation"].retracted is False
    assert g1.nodes["N_dep_C"].retracted is True          # real retracted citer
    assert g1.nodes["N_dep_C"].doubt.point == 1.0
    for n in g1.nodes.values():
        assert n.source and n.source != "unresolved"


def test_real_citing_sentences_attached():
    g = build_insulin_graph()
    resolved = [e for e in g.edges if e.edge_type.value == "cites"
                and not e.context.startswith("unresolved")]
    assert resolved, "expected real citing sentences on cites edges"


def test_domain_agnostic_second_calibration_number():
    """The SAME classifier, measured on the second domain, must clear the bar —
    this is the two-data-point proof of 'domain-agnostic'."""
    import calibrate
    from keystone.agents.reasoner import HeuristicReasoner
    rows = calibrate.load_labeled("insulin")
    assert len(rows) >= 30
    res = calibrate.evaluate(HeuristicReasoner(), rows)
    assert res["accuracy"] > 0.5


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all insulin tests passed")
