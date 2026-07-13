"""
Claim-integrity model tests — the distinction the whole product rests on:
"verified" (the source record resolves) must NEVER mean "scientifically true"
or even "supports this claim." Evidence status is conclusion-specific; retracted
sources are excluded from positive support; a real DOI without an exact link is
not evidence.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

from keystone.core import Node, NodeType, Interval                       # noqa: E402
from keystone.data_gbm import build_gbm_graph                            # noqa: E402
from keystone.decision_engine import decide                             # noqa: E402
from keystone.deterministic.claim_status import (                        # noqa: E402
    source_record_verified, classify_claim_type, node_claim, assess_claim)


def _gbm():
    return build_gbm_graph(live=False)


def test_retracted_source_resolves_but_is_excluded():
    """A retracted paper's DOI can RESOLVE (source_record_verified=True) yet it
    stays integrity_state=retracted and evidence_status=excluded for EVERY
    conclusion — a resolvable record never means the claim is true/supportive."""
    n = _gbm().nodes["N_foundation"]
    c = node_claim(n)
    assert c["source_record_verified"] is True          # the DOI resolves
    assert c["integrity_state"] == "retracted"
    for conclusion in (
            {"id": "A", "supporting_evidence": ["N_foundation"], "contradicting_evidence": []},
            {"id": "B", "supporting_evidence": [], "contradicting_evidence": []}):
        assert assess_claim("N_foundation", n, conclusion)["evidence_status"] == "excluded"


def test_retracted_never_positive_support_in_any_hypothesis():
    """Retraction rule: a retracted node is never counted as positive (supporting)
    evidence for any ranked hypothesis."""
    g = _gbm()
    retracted = {nid for nid, n in g.nodes.items() if n.retracted}
    for h in decide("gbm")[0].get("competing_hypotheses", []):
        assert not (retracted & set(h.get("supporting_evidence", []))), \
            f"retracted node used as support in {h.get('id')}"


def test_evidence_status_is_conclusion_specific():
    """The same claim can SUPPORT one conclusion and CONTRADICT another —
    evidence status is a relation, never a single global field on the claim."""
    n = _gbm().nodes["N_target"]
    a = assess_claim("N_target", n, {"id": "A", "supporting_evidence": ["N_target"],
                                     "contradicting_evidence": []})
    b = assess_claim("N_target", n, {"id": "B", "supporting_evidence": [],
                                     "contradicting_evidence": ["N_target"]})
    assert a["evidence_status"] == "supported"
    assert b["evidence_status"] == "contradicted"
    assert a["evidence_status"] != b["evidence_status"]


def test_real_doi_without_exact_link_is_not_evidence():
    """A real DOI attached to an unrelated sentence (no quote/locator) must NOT
    count as evidence — it is `missing` until an exact link is provided."""
    assert classify_claim_type("paper", "10.1038/nature12345", None, None) == "missing"
    assert classify_claim_type("paper", "10.1038/nature12345", "the assay measured X", None) == "evidence"
    assert classify_claim_type("paper", "10.1038/nature12345", None, "Fig 3B") == "evidence"


def test_unresolved_is_missing_and_never_supported():
    """An unresolved source is claim_type=missing; listed under a conclusion it
    reads `unresolved`, never `supported`."""
    assert source_record_verified("unresolved") is False
    assert classify_claim_type("unresolved", "unresolved", None, None) == "missing"
    ghost = Node(id="N_x", node_type=NodeType.UNRESOLVED, source="unresolved",
                 text="", doubt=Interval(0.5, 0.3, 0.7))
    assert node_claim(ghost)["claim_type"] == "missing"
    a = assess_claim("N_x", ghost, {"id": "C", "supporting_evidence": ["N_x"],
                                    "contradicting_evidence": []})
    assert a["evidence_status"] == "unresolved"
