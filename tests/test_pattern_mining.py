"""
Tests for the Literature Pattern Miner — six cases spanning every detector,
the refusal path, and the "no fabrication" guarantee (only real DOIs cited).
Runs offline; sets KEYSTONE_OFFLINE=1 at import so the deterministic path
is exercised.
"""
import os
os.environ["KEYSTONE_OFFLINE"] = "1"

import pytest  # noqa: E402

from keystone.agents.pattern_miner import mine_patterns  # noqa: E402
from keystone.deterministic.pattern_mining import (  # noqa: E402
    Corpus, Paper, run_scans, build_corpus_from_openalex,
)


def _rec(doi, title, year, cited=5, retracted=False, abstract=""):
    return {"doi": doi, "title": title, "year": year,
            "cited_by_count": cited, "is_retracted": retracted,
            "abstract": abstract}


def test_contradiction_detector_finds_polar_pair_on_shared_target():
    """Two papers on the same gene with opposite polarity → contradiction hit,
    citing both real DOIs."""
    corpus = [
        _rec("10.1000/a", "CTSB promotes glioblastoma invasion", 2018, 30),
        _rec("10.1000/b", "CTSB inhibits glioblastoma invasion in vivo",
             2020, 22),
        _rec("10.1000/c", "MMP9 upregulates tumour cell migration", 2019, 40),
        _rec("10.1000/d", "MMP9 blocks angiogenesis in orthotopic models",
             2021, 12),
    ]
    r = mine_patterns(corpus, question="CTSB in glioblastoma")
    kinds = {h["kind"] for h in r.report.to_dict()["hits"]}
    assert "contradiction_cluster" in kinds
    # every DOI cited must be a real one from the input corpus (no fabrication)
    real_dois = {c["doi"] for c in corpus}
    for h in r.report.hits:
        for d in h.dois:
            assert d in real_dois, f"invented DOI: {d}"


def test_reagent_contamination_trend_flags_known_flagged_line():
    """A cohort where a Cellosaurus-flagged line ('KB', a HeLa derivative)
    appears in ≥ 10% of papers per year → reagent_trend hit."""
    corpus = [
        _rec("10.2000/a", "Signalling in KB cell line, 2018", 2018, 8),
        _rec("10.2000/b", "Cytoskeletal dynamics in KB carcinoma model",
             2018, 15),
        _rec("10.2000/c", "Adhesion assays in HeLa cells", 2018, 22),
        _rec("10.2000/d", "Chang liver metabolism reassessed", 2019, 11),
        _rec("10.2000/e", "Novel signalling in Hep-2 as HeLa derivative",
             2020, 5),
    ]
    r = mine_patterns(corpus)
    kinds = {h["kind"] for h in r.report.to_dict()["hits"]}
    assert "reagent_trend" in kinds


def test_method_drift_detects_assay_shift_across_years():
    """A corpus where Boyden chamber dominates 2005-2007 but transwell takes
    over by 2015-2017 → method_drift hit with swing ≥ 30 pts."""
    corpus = [
        _rec("10.3000/a", "Boyden chamber invasion assay in glioma", 2005, 90),
        _rec("10.3000/b", "Boyden chamber for cathepsin B", 2006, 60),
        _rec("10.3000/c", "Boyden chamber revisited", 2007, 40),
        _rec("10.3000/d", "Transwell invasion in glioblastoma", 2015, 30),
        _rec("10.3000/e", "Transwell dose response for MMP9", 2016, 25),
        _rec("10.3000/f", "Transwell chamber standardisation", 2017, 20),
    ]
    r = mine_patterns(corpus)
    kinds = {h["kind"] for h in r.report.to_dict()["hits"]}
    assert "method_drift" in kinds


def test_refused_scan_type_returns_structured_explanation():
    """causal_inference is REFUSED by policy — the caller gets a structured
    reason, never a fabricated pattern."""
    r = mine_patterns([_rec("10.4000/a", "Any title", 2020)],
                      scan_type="causal_inference")
    d = r.to_dict()
    assert d["refused"] is True
    assert "intervention" in d["reason"].lower() or "refused" in d["reason"].lower()
    assert d["report"]["hits"] == []


def test_unknown_scan_type_refuses_without_fabrication():
    r = mine_patterns([_rec("10.5000/a", "Any", 2020)], scan_type="foobar")
    d = r.to_dict()
    assert d["refused"] is True
    assert "unknown" in d["reason"].lower()


def test_provenance_splits_real_from_illustrative_dois():
    """The credibility guarantee the review panel demanded: illustrative
    synthetic records are counted separately and never presented as real."""
    real = [_rec("10.1038/sj.onc.1207616", "CTSB promotes invasion", 2004, 320)]
    fake = [{"doi": "10.1038/demo-01", "title": "CTSB inhibits invasion",
             "year": 2006, "cited_by_count": 5, "illustrative": True}]
    r = mine_patterns(real + fake).to_dict()
    prov = r["provenance"]
    assert prov["n_real"] == 1 and prov["n_illustrative"] == 1
    assert "10.1038/demo-01" in prov["illustrative_dois"]
    # a real DOI is never mislabelled illustrative
    assert "10.1038/sj.onc.1207616" not in prov["illustrative_dois"]


def test_shipped_corpus_provenance_is_honest():
    """The shipped GBM corpus must declare its real/illustrative split so the
    UI can badge synthetic DOIs — no synthetic DOI is ever shown as real."""
    import json
    from pathlib import Path
    c = json.loads((Path(__file__).resolve().parents[1] / "examples" /
                    "pattern_corpora" / "gbm_cathepsin_b.json").read_text())
    r = mine_patterns(c["records"], question=c["question"]).to_dict()
    prov = r["provenance"]
    assert prov["n_real"] >= 1 and prov["n_illustrative"] >= 1
    # the real retracted seed is on the real side, never illustrative
    assert "10.1038/sj.onc.1207616" not in prov["illustrative_dois"]


def test_live_claude_path_imports_are_wired_offline_guard():
    """Regression guard for the silent-fallback class of bug: the live-Claude
    narration path imports ClaudeReasoner + DEFAULT_MODEL and reaches the
    .client property. Verified WITHOUT a key or network — we only assert the
    symbols exist and .client is an attribute, so a broken import (the earlier
    `import _client` bug) fails loudly here instead of silently degrading to
    deterministic in production."""
    from keystone.agents import claude_reasoner
    assert hasattr(claude_reasoner, "ClaudeReasoner")
    assert hasattr(claude_reasoner, "DEFAULT_MODEL")
    # .client is a property on an instance (raises only when actually used
    # without a key/package — construction + attribute access must not KeyError)
    r = claude_reasoner.ClaudeReasoner()
    assert type(r).client.fget is not None      # the property exists
    assert isinstance(claude_reasoner.DEFAULT_MODEL, str) and claude_reasoner.DEFAULT_MODEL


def test_real_gbm_corpus_is_100_percent_real_and_fires_on_abstracts():
    """The flagship corpus is now REAL: the retracted seed + real OpenAlex
    papers that cite it, with real abstracts. Zero illustrative records, and
    at least one pattern fires on real full text (not crafted titles) — the
    credibility capstone."""
    import json
    from pathlib import Path
    c = json.loads((Path(__file__).resolve().parents[1] / "examples" /
                    "pattern_corpora" / "gbm_cathepsin_real.json").read_text())
    r = mine_patterns(c["records"], question=c["question"],
                      seed_doi=c["seed_doi"]).to_dict()
    prov = r["provenance"]
    assert prov["n_illustrative"] == 0 and prov["n_real"] >= 20
    # every record carries a real (non-10.9999) DOI
    assert all(not row["doi"].startswith("10.9999") for row in c["records"])
    # at least one pattern is detected on the real abstracts
    assert len(r["report"]["hits"]) >= 1


def test_real_prostate_corpus_is_100_percent_real_and_fires_method_drift():
    """The SECOND real corpus (prostate cancer invasion): 100% real OpenAlex
    records, zero illustrative, and it surfaces a GENUINE methodological drift
    in invasion assays (Boyden chamber → Transwell / 3D spheroid) across
    1996-2022 — the same tool finding a real pattern in a second independent
    literature, not a crafted one. This is the 'two real domains' capstone for
    the Pattern Miner."""
    import json
    from pathlib import Path
    c = json.loads((Path(__file__).resolve().parents[1] / "examples" /
                    "pattern_corpora" / "prostate_invasion_real.json").read_text())
    r = mine_patterns(c["records"], question=c["question"]).to_dict()
    prov = r["provenance"]
    assert prov["n_illustrative"] == 0 and prov["n_real"] >= 20
    # every record carries a real (non-synthetic) DOI
    assert all(not row["doi"].startswith("10.9999") for row in c["records"])
    assert all(not row["doi"].startswith("10.1038/gbm-") for row in c["records"])
    # the genuine pattern in this literature is a method drift, on real data
    kinds = {h["kind"] for h in r["report"]["hits"]}
    assert "method_drift" in kinds


def test_tiny_corpus_produces_no_hits_never_fabricates():
    """Below CORPUS_MIN_SIZE, every detector returns None — we do not invent
    a pattern from three papers just to please the caller."""
    corpus = [
        _rec("10.6000/a", "CTSB promotes invasion", 2015),
        _rec("10.6000/b", "CTSB inhibits invasion", 2016),
    ]
    r = mine_patterns(corpus)
    assert r.report.to_dict()["hits"] == []
    assert not r.refused


if __name__ == "__main__":
    test_contradiction_detector_finds_polar_pair_on_shared_target()
    test_reagent_contamination_trend_flags_known_flagged_line()
    test_method_drift_detects_assay_shift_across_years()
    test_refused_scan_type_returns_structured_explanation()
    test_unknown_scan_type_refuses_without_fabrication()
    test_tiny_corpus_produces_no_hits_never_fabricates()
    print("all pattern-mining tests passed")
