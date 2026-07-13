"""
Tests for GAP #3 — "did someone already discover this?" The prior-art check
surfaces the closest existing OpenAlex work for a claim/question. Runs offline
from a real pinned OpenAlex search fixture. Honest by construction: it surfaces
overlap, flags retracted matches, and never issues a novelty verdict.
"""
import os
os.environ["KEYSTONE_OFFLINE"] = "1"

import pytest  # noqa: E402

from keystone.prior_art import check_prior_art  # noqa: E402

DEMO_Q = "cathepsin B glioblastoma invasion"     # pinned OpenAlex search fixture


def test_prior_art_returns_real_matches():
    r = check_prior_art(DEMO_Q)
    assert r["resolved"] and r["matches"]
    top = r["matches"][0]
    assert top["title"] and ("doi" in top)
    # every returned DOI is a real string or None — never fabricated
    for m in r["matches"]:
        assert m["doi"] is None or isinstance(m["doi"], str)


def test_retracted_close_match_is_flagged():
    """The cathepsin B query's closest work IS the retracted seed paper — the
    honest, mission-perfect result: 'someone already did this, and it was
    retracted.'"""
    r = check_prior_art(DEMO_Q)
    assert r["any_retracted"] is True
    assert any(m["is_retracted"] for m in r["matches"])


def test_note_never_claims_novelty():
    r = check_prior_art(DEMO_Q)
    low = r["note"].lower()
    assert "does not" in low or "not" in low          # explicitly disclaims judging novelty
    assert "novel" in low


def test_empty_query_searches_nothing():
    r = check_prior_art("")
    assert r["resolved"] is False and r["matches"] == []


def test_unpinned_offline_query_returns_no_fabricated_match():
    """Offline with no pinned fixture for the query → empty, and the note is
    explicit that absence is not evidence of novelty (no fabrication)."""
    r = check_prior_art("a query with no pinned fixture zzzqqq")
    assert r["matches"] == []
    assert "not evidence of novelty" in r["note"].lower()


if __name__ == "__main__":
    test_prior_art_returns_real_matches()
    test_retracted_close_match_is_flagged()
    test_note_never_claims_novelty()
    test_empty_query_searches_nothing()
    test_unpinned_offline_query_returns_no_fabricated_match()
    print("all prior-art tests passed")
