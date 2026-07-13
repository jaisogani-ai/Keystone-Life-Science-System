"""
Tests for the Laboratory Agent's bench-data Reviewer — six cases spanning
the three verdicts, the refusal boundary, aggregation, and the "no
fabrication" guarantee. Runs offline (KEYSTONE_OFFLINE=1 at import) so the
deterministic path is exercised.
"""
import os
os.environ["KEYSTONE_OFFLINE"] = "1"

from pathlib import Path

import pytest  # noqa: E402

from keystone.agents.bench_reviewer import (  # noqa: E402
    review_plate, review_batch, format_catalogue,
)

_EX = Path(__file__).resolve().parents[1] / "examples" / "bench_data"


def _load(name):
    return (_EX / name).read_text()


def test_clean_plate_is_supported_no_breaches():
    r = review_plate(_load("clean_plate.csv"), label="clean")
    assert r.verdict == "supported"
    assert r.adjusted_confidence["point"] == r.base_confidence
    assert all(not m["breached"] for m in r.qc_metrics)
    assert r.suggestions == []


def test_borderline_plate_downgrades_confidence():
    """A noisy standard curve (single breach) downgrades 0.55 -> 0.35 — the
    same visible self-challenge the literature Reviewer applies."""
    r = review_plate(_load("borderline_plate.csv"), label="borderline")
    assert r.verdict == "downgraded"
    assert r.adjusted_confidence["point"] == 0.35
    breached = [m for m in r.qc_metrics if m["breached"]]
    assert len(breached) == 1 and breached[0]["name"] == "standard_curve_r2"
    assert len(r.suggestions) == 1


def test_bad_plate_is_rejected_with_multiple_objections():
    r = review_plate(_load("bad_plate.csv"), label="bad")
    assert r.verdict == "rejected"
    assert r.adjusted_confidence["point"] < r.base_confidence
    assert len(r.objections) >= 3
    assert len(r.suggestions) >= 3           # a workflow fix per failed check
    # every QC metric carries a real methodology citation — never fabricated
    assert all(m["citation"] for m in r.qc_metrics)


def test_unsupported_format_is_refused_with_structured_reason():
    """Western-blot densitometry is refused by policy — the caller gets a
    structured explanation, never a fabricated measurement."""
    r = review_plate("irrelevant", label="blot", fmt="western_blot")
    assert r.refused is True and r.verdict == "refused"
    assert "densitometry" in r.reason.lower() or "refused" in r.reason.lower()
    assert r.qc_metrics == []


def test_unknown_format_refuses_without_fabrication():
    r = review_plate("x", label="mystery", fmt="totally_made_up")
    assert r.refused is True
    assert "unknown format" in r.reason.lower()


def test_batch_aggregates_into_one_operational_report():
    files = [
        {"name": "plate-A", "csv_text": _load("clean_plate.csv")},
        {"name": "plate-B", "csv_text": _load("borderline_plate.csv")},
        {"name": "plate-C", "csv_text": _load("bad_plate.csv")},
        {"name": "blot-1", "csv_text": "n/a", "format": "western_blot"},
    ]
    rep = review_batch(files)
    assert rep["n_plates"] == 4
    assert rep["counts"]["supported"] == 1
    assert rep["counts"]["downgraded"] == 1
    assert rep["counts"]["rejected"] == 1
    assert rep["counts"]["refused"] == 1
    # worst verdict across the batch is the operational headline signal
    assert rep["worst_verdict"] == "refused"
    assert "reviewed" in rep["operational_headline"]


def test_format_catalogue_lists_supported_and_refused():
    cat = format_catalogue()
    statuses = {c["status"] for c in cat}
    assert "supported" in statuses and "refused" in statuses
    supported = [c["format"] for c in cat if c["status"] == "supported"]
    assert "plate_reader_csv" in supported


if __name__ == "__main__":
    test_clean_plate_is_supported_no_breaches()
    test_borderline_plate_downgrades_confidence()
    test_bad_plate_is_rejected_with_multiple_objections()
    test_unsupported_format_is_refused_with_structured_reason()
    test_unknown_format_refuses_without_fabrication()
    test_batch_aggregates_into_one_operational_report()
    test_format_catalogue_lists_supported_and_refused()
    print("all bench-reviewer tests passed")
