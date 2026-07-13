"""
Reference-import tests — the entry workflow that makes Keystone usable on a
scientist's OWN references. Offline against pinned Crossref fixtures: a known
retracted DOI must be flagged retracted, a clean DOI must not be, and an
unresolvable DOI must be shown as unresolved (never passed as clean / fabricated).
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

from keystone.ingest.references import parse_dois, build_graph_from_dois  # noqa: E402
from keystone.integrity_report import reference_integrity                 # noqa: E402

# fixtures present in keystone/connectors/fixtures/
_RETRACTED = "10.1038/sj.onc.1207616"     # the real retracted cathepsin B paper
_CLEAN = "10.1038/414799a"                # a real clean paper (insulin signalling)
_MISSING = "10.9999/nonexistent.doi"      # will not resolve — must show unresolved


def test_parse_dois_from_bibtex_and_plain_text():
    bib = """@article{x, title={A}, doi = {10.1038/sj.onc.1207616}, year={2004}}
             See also https://doi.org/10.1038/414799a and 10.1038/414799a (dup)."""
    dois = parse_dois(bib)
    assert _RETRACTED in dois and _CLEAN in dois
    assert len(dois) == 2                              # deduplicated


def test_build_graph_flags_a_real_retraction_offline():
    g = build_graph_from_dois("my refs", [_RETRACTED, _CLEAN])
    assert len(g.nodes) == 2
    retr = [n for n in g.nodes.values() if n.retracted]
    assert len(retr) == 1 and retr[0].source == _RETRACTED
    assert retr[0].doubt.point == 1.0                  # retracted -> fully doubted
    clean = [n for n in g.nodes.values() if not n.retracted]
    assert clean and clean[0].source == _CLEAN


def test_unresolvable_doi_is_shown_not_fabricated():
    g = build_graph_from_dois("q", [_MISSING])
    n = list(g.nodes.values())[0]
    assert n.node_type.value == "unresolved" and n.source == "unresolved"


def test_reference_integrity_triage_counts_and_orders():
    g = build_graph_from_dois("q", [_CLEAN, _RETRACTED, _MISSING])
    tri = reference_integrity(g)
    assert tri["total"] == 3
    assert tri["counts"]["retracted"] == 1
    assert tri["counts"]["unresolved"] == 1
    assert tri["compromised"] >= 1
    assert "compromised" in tri["verdict"]
    assert tri["rows"][0]["status"] == "retracted"     # worst first
    assert tri["rows"][0]["url"].startswith("https://doi.org/")   # verifiable
    assert tri["graph_hash"]                            # reproducible


def test_retrospective_insulin_domain_confirms_disease_agnostic():
    """Second retrospective in an independent domain (insulin CDK4 signalling).
    Offline reproduction: 3 real high-impact citers (Physiological Reviews 2018
    ~2,915 cites, Trends in Cell Biology 2018, Frontiers in Endocrinology 2017)
    cited the 2016 JCI CDK4 paper — retracted in 2023. Same engine, same
    analysis, different disease — that IS disease-agnostic."""
    from pathlib import Path
    bib = Path("examples/retrospective-insulin-cdk4-2016.bib").read_text()
    dois = parse_dois(bib)
    assert len(dois) == 5
    g = build_graph_from_dois("insulin retrospective", dois)
    tri = reference_integrity(g)
    assert tri["counts"]["retracted"] == 1
    assert tri["counts"]["cites_retraction"] == 3
    assert tri["counts"]["clean"] == 1
    contam = [e for e in g.edges if e.edge_type.value == "cites"]
    assert len(contam) == 3
    assert all(e.temporal.value == "pre_retraction" for e in contam)


def test_retrospective_real_world_positive_control():
    """Offline reproduction of the 'if only they'd known' story: 3 real
    high-impact papers (Nature Reviews Cancer 2006, Cancer Cell 2008, Eur Respir
    J 2010; combined ~3,100 citations) that cited the 2004 cathepsin B paper —
    which was retracted in 2025. This is Keystone's built-in retrospective
    positive control (analogous to Sayane's STAT6 rediscovery)."""
    from pathlib import Path
    bib = Path("examples/retrospective-nature-reviews-2006.bib").read_text()
    dois = parse_dois(bib)
    assert len(dois) == 5
    g = build_graph_from_dois("retrospective", dois)
    tri = reference_integrity(g)
    assert tri["counts"]["retracted"] == 1
    assert tri["counts"]["cites_retraction"] == 3         # 3 real citers
    assert tri["counts"]["clean"] == 1
    # every contamination edge marks the pre-retraction temporal (the papers
    # were published BEFORE 2025 — the story of "no way to know at the time")
    contam = [e for e in g.edges if e.edge_type.value == "cites"]
    assert len(contam) == 3
    assert all(e.temporal.value == "pre_retraction" for e in contam)


def test_blast_radius_contamination_edge_offline():
    """A paper that cites a retracted work inherits doubt — the blast radius.
    Offline via pinned OpenAlex reference-list fixtures: the recent paper
    references the retracted cathepsin B paper, so it is flagged and its doubt is
    raised by propagation (never fabricated)."""
    citer = "10.3389/fonc.2025.1577492"          # references the retracted paper
    g = build_graph_from_dois("q", [_RETRACTED, _CLEAN, citer])
    # an edge from the citer to the retracted node exists
    contaminated = [e for e in g.edges
                    if g.nodes[e.dst].retracted and e.edge_type.value == "cites"]
    assert contaminated, "expected a contamination edge to the retracted paper"
    tri = reference_integrity(g)
    assert tri["counts"]["cites_retraction"] >= 1
    citer_row = next(r for r in tri["rows"] if r["doi"] == citer)
    assert citer_row["status"] == "cites_retraction"
    assert citer_row["doubt"] > 0.5               # inherited doubt, propagated


def test_integrity_summary_template_uses_real_dois_and_counts():
    """The deterministic summary paragraph must cite real numbers + a real DOI
    from the input, and it must NOT hallucinate a percentage or invented DOI."""
    from keystone.integrity_report import (integrity_summary_template,
                                           integrity_summary)
    g = build_graph_from_dois("q", [_RETRACTED, _CLEAN, _MISSING])
    tri = reference_integrity(g)
    s = integrity_summary_template(tri)
    assert s["source"] == "template"
    p = s["paragraph"]
    assert _RETRACTED in p                            # cites the real DOI
    assert "3 references" in p                        # real total
    assert "1 retracted" in p                         # real count
    assert "AI proposes, scientists decide" in p       # discipline reminder
    # never invent a percentage in the template
    assert "%" not in p
    # integrity_summary() with no reasoner is the template
    assert integrity_summary(tri)["source"] == "template"


def test_integrity_summary_honest_when_all_clean():
    """No compromised references -> honest 'clean' paragraph, not a fabricated
    concern to make the paragraph feel useful."""
    from keystone.integrity_report import integrity_summary_template
    g = build_graph_from_dois("q", [_CLEAN])
    tri = reference_integrity(g)
    p = integrity_summary_template(tri)["paragraph"]
    assert "cleanly" in p or "clean" in p.lower()
    assert "retracted" not in p.lower() or "no retract" in p.lower() or \
           "0 retracted" in p or "no retractions" in p.lower()


def test_integrity_summary_falls_back_when_reasoner_raises():
    """A live-Claude failure must never fabricate — it falls back to the
    honest deterministic template."""
    from keystone.integrity_report import integrity_summary
    class _Broken:
        def integrity_summary(self, triage): raise RuntimeError("no api key")
    g = build_graph_from_dois("q", [_RETRACTED, _CLEAN])
    tri = reference_integrity(g)
    out = integrity_summary(tri, reasoner=_Broken())
    assert out["source"] == "template"                # never claude on failure
    assert out["paragraph"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all ingest tests passed")
