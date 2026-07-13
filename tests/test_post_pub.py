"""
Tests for GAP #5 — "which papers changed after publication?" Keystone now
detects ALL Crossref post-publication changes (retractions + corrections +
errata + expressions of concern), not just retractions. Runs offline from
real pinned fixtures.
"""
import os
os.environ["KEYSTONE_OFFLINE"] = "1"

import pytest  # noqa: E402

from keystone.connectors.registry import post_publication_updates  # noqa: E402
from keystone.ingest.references import build_graph_from_dois  # noqa: E402
from keystone.integrity_report import reference_integrity  # noqa: E402

# Real DOIs pinned as fixtures (verified against Crossref at capture time):
CORRECTION = "10.1016/j.cellsig.2012.01.015"        # correction + erratum, not retracted
CONCERN = "10.1016/j.chemosphere.2022.133829"       # expression of concern, not retracted
RETRACTED = "10.1126/science.1197258"               # arsenic-life: EoC (2011) → retraction (2012)
CLEAN = "10.1038/nrc1949"                           # real, no post-pub change


def test_correction_is_detected_not_just_retraction():
    u = post_publication_updates(CORRECTION)
    assert u["resolved"] and u["has_correction"] and not u["has_retraction"]
    labels = {x["label"] for x in u["updates"]}
    assert any("correct" in l for l in labels)


def test_expression_of_concern_is_detected():
    u = post_publication_updates(CONCERN)
    assert u["resolved"] and u["has_concern"] and not u["has_retraction"]


def test_retraction_still_detected_with_full_history():
    """A retracted paper still flags retracted — AND surfaces its earlier
    expression of concern, so the scientist sees the full timeline."""
    u = post_publication_updates(RETRACTED)
    assert u["has_retraction"] and u["has_concern"]


def test_clean_paper_has_no_post_pub_changes():
    u = post_publication_updates(CLEAN)
    assert u["resolved"] and not (u["has_retraction"] or u["has_correction"]
                                  or u["has_concern"])


def test_triage_surfaces_the_new_statuses():
    graph = build_graph_from_dois("post-pub", [CORRECTION, CONCERN, RETRACTED, CLEAN])
    t = reference_integrity(graph)
    statuses = {r["doi"]: r["status"] for r in t["rows"]}
    assert statuses[CORRECTION] == "corrected"
    assert statuses[CONCERN] == "expression_of_concern"
    assert statuses[RETRACTED] == "retracted"
    assert t["changed_after_publication"] == 2          # correction + concern
    # the retracted row still carries its full change history for the timeline
    retr_row = next(r for r in t["rows"] if r["doi"] == RETRACTED)
    assert any(u["type"] == "expression_of_concern" for u in retr_row["post_pub_updates"])


def test_unresolved_doi_is_not_fabricated():
    u = post_publication_updates("10.9999/does-not-exist-xyz")
    assert u["resolved"] is False and u["updates"] == []


if __name__ == "__main__":
    test_correction_is_detected_not_just_retraction()
    test_expression_of_concern_is_detected()
    test_retraction_still_detected_with_full_history()
    test_clean_paper_has_no_post_pub_changes()
    test_triage_surfaces_the_new_statuses()
    test_unresolved_doi_is_not_fabricated()
    print("all post-publication tests passed")
