"""
Tests for the Field Integrity Report — a computed, auditable integrity index
for a corpus of literature, from real signals. Runs offline on the real GBM
corpus (papers citing the retracted cathepsin B paper).
"""
import os
os.environ["KEYSTONE_OFFLINE"] = "1"

import json  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from keystone.field_integrity import (  # noqa: E402
    field_integrity_report, field_audit_html, reference_set_health, WEIGHTS,
)
from keystone.ingest.references import build_graph_from_dois  # noqa: E402
from keystone.integrity_report import reference_integrity  # noqa: E402

_REAL = json.loads((Path(__file__).resolve().parents[1] / "examples" /
                    "pattern_corpora" / "gbm_cathepsin_real.json").read_text())


def _report():
    return field_integrity_report(_REAL["records"], question=_REAL["question"],
                                  seed_doi=_REAL["seed_doi"])


def test_index_is_computed_from_real_signals():
    r = _report()
    assert r["resolved"] and 0 <= r["score"] <= 100
    assert r["band"] in ("high", "medium", "low")
    # the retraction component is real: the corpus contains real retracted papers
    assert r["components"]["retraction"]["count"] >= 1
    assert r["retracted_papers"] and r["retracted_papers"][0]["doi"]


def test_weights_are_exposed_and_sum_sensibly():
    r = _report()
    assert r["weights"] == WEIGHTS
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9   # auditable composite


def test_score_moves_with_retraction_burden():
    """A corpus with a higher retracted fraction must score no higher than a
    cleaner one — the index is monotonic in the burden, not arbitrary."""
    clean = [{"doi": "10.1/a", "title": "clean paper", "year": 2020,
              "cited_by_count": 10, "is_retracted": False}] * 4
    dirty = [{"doi": "10.1/a", "title": "clean paper", "year": 2020,
              "cited_by_count": 10, "is_retracted": False},
             {"doi": "10.1/b", "title": "retracted paper", "year": 2020,
              "cited_by_count": 5, "is_retracted": True}]
    rc = field_integrity_report(clean, resolve_post_pub=False)
    rd = field_integrity_report(dirty, resolve_post_pub=False)
    assert rc["score"] >= rd["score"]


def test_score_carries_a_sensitivity_analysis():
    """A reviewer will ask 'why those weights?' The report must show the band's
    robustness across alternative priors — the honest ordinal claim."""
    r = _report()
    s = r["sensitivity"]
    assert "band_robust" in s and isinstance(s["band_robust"], bool)
    lo, hi = s["score_range"]
    assert lo <= r["score"] <= hi
    # on the real GBM corpus the band is robust (clean literature, high band)
    assert s["band_robust"] is True and s["bands_seen"] == ["high"]


def test_empty_corpus_is_not_scored():
    r = field_integrity_report([])
    assert r["resolved"] is False and r["n"] == 0


def test_audit_html_is_hash_stamped_and_cites_real_dois():
    r = _report()
    doc = field_audit_html(r)
    assert doc.startswith("<!doctype html>")
    assert "Research Integrity Audit" in doc
    assert "audit:" in doc                       # reproducibility hash
    assert "10.1038/sj.onc.1207616" in doc       # the real retracted seed
    # nothing fabricated: the auditable formula is shown
    assert "100 × (1" in doc or "100 &#215; (1" in doc


def test_no_placeholder_dois_in_the_scored_corpus():
    assert all(not (r.get("doi") or "").startswith("10.9999")
               for r in _REAL["records"])


def test_reference_set_health_runs_on_the_scientists_own_refs():
    """The org-level score must run on a scientist's OWN imported references —
    computed from the triage, with real retracted DOIs, and exportable."""
    graph = build_graph_from_dois("my grant refs", [
        "10.1016/j.cellsig.2012.01.015",   # corrected
        "10.1126/science.1197258",         # retracted
        "10.1038/nrc1949"])                # clean
    triage = reference_integrity(graph)
    triage["question"] = "my grant refs"
    h = reference_set_health(triage)
    assert h["resolved"] and 0 <= h["score"] <= 100
    assert set(h["components"]) == {"retraction", "contamination", "post_pub"}
    assert h["components"]["retraction"]["count"] >= 1
    assert "sensitivity" in h and "band_robust" in h["sensitivity"]
    # the generic audit export renders this shape too, citing a real DOI
    doc = field_audit_html(h)
    assert doc.rstrip().endswith("</html>") and "10.1126/science.1197258" in doc


def test_reference_set_health_empty_is_not_scored():
    assert reference_set_health({"rows": [], "total": 0})["resolved"] is False


if __name__ == "__main__":
    test_index_is_computed_from_real_signals()
    test_weights_are_exposed_and_sum_sensibly()
    test_score_moves_with_retraction_burden()
    test_empty_corpus_is_not_scored()
    test_audit_html_is_hash_stamped_and_cites_real_dois()
    test_no_placeholder_dois_in_the_scored_corpus()
    print("all field-integrity tests passed")
