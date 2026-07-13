"""
Prior-art search — the pasted-identifier path.

Guards the fix for a real red flag: the header bar says "Paste a DOI / PMID",
but a bare DOI was being sent to a *keyword* search (OpenAlex never matches a
raw DOI that way), so real papers returned "no match". A DOI/PMID must resolve
the EXACT record and surface its retraction status. Network-free via monkeypatch.
"""
import keystone.prior_art as PA


def _fake_work(record):
    def _inner(work_id):
        return {**record, "resolved": True, "_work_id": work_id}
    return _inner


def test_doi_resolves_the_exact_record_not_a_keyword_search(monkeypatch):
    seen = {}
    monkeypatch.setattr(PA.R, "openalex_work", _fake_work(
        {"title": "CDK4 is an essential insulin effector in adipocytes",
         "doi": "https://doi.org/10.1172/jci81480", "year": 2015,
         "is_retracted": False, "cited_by_count": 300}))
    def _rs(doi):
        seen["rs"] = doi
        return {"is_retracted": True}
    monkeypatch.setattr(PA.R, "retraction_status", _rs)
    # if this were a keyword search it would be called; assert it is NOT
    monkeypatch.setattr(PA.R, "openalex_search",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("used keyword search for a DOI")))

    out = PA.check_prior_art("10.1172/jci81480")
    assert out["resolved"] is True
    assert len(out["matches"]) == 1
    assert out["matches"][0]["title"].startswith("CDK4")
    # retraction cross-checked via Crossref/RW even though OpenAlex flag was False
    assert out["any_retracted"] is True
    assert "RETRACTED" in out["note"]
    assert seen["rs"] == "10.1172/jci81480"


def test_pmid_resolves_via_direct_lookup(monkeypatch):
    calls = {}
    def _work(work_id):
        calls["id"] = work_id
        return {"resolved": True, "title": "A real paper", "year": 2019,
                "doi": None, "is_retracted": False}
    monkeypatch.setattr(PA.R, "openalex_work", _work)
    out = PA.check_prior_art("30639098")
    assert out["resolved"] is True
    assert calls["id"] == "pmid:30639098"


def test_free_text_still_uses_relevance_search(monkeypatch):
    monkeypatch.setattr(PA.R, "openalex_work",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("free text hit the identifier path")))
    monkeypatch.setattr(PA.R, "openalex_search",
                        lambda q, limit=8: [{"title": "Th2 regulators", "doi": "10.x/y",
                                             "year": 2020, "is_retracted": False}])
    out = PA.check_prior_art("what regulates the type-2 program?")
    assert out["resolved"] is True
    assert out["matches"][0]["title"] == "Th2 regulators"


def test_unresolved_identifier_does_not_fabricate(monkeypatch):
    monkeypatch.setattr(PA.R, "openalex_work", lambda *a, **k: {"resolved": False})
    monkeypatch.setattr(PA.R, "openalex_search", lambda *a, **k: [])
    out = PA.check_prior_art("10.9999/does-not-exist")
    assert out["resolved"] is False
    assert out["matches"] == []
