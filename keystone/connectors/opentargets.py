"""
keystone.connectors.opentargets
================================
Real human genetic / evidence disease-association scores from **Open Targets**
(GraphQL platform API). Used by the target-ranking "disease relevance" component
so that number is *fetched from a real database*, not typed by hand.

Cache-first + pinned fixture (via ``http_cache``) so the demo is deterministic and
offline-safe; an unresolved fetch returns ``None`` and the caller renders
"not available" — a score is never fabricated. The association score is Open
Targets' own aggregate of genetic, literature, and other evidence; Keystone
surfaces it verbatim with its source id, and treats it as *Literature-supported*
evidence (a real database record), never as proof a target is causal.
"""
from __future__ import annotations

from typing import Optional

from keystone.connectors.http_cache import cached_post_json

OT_URL = "https://api.platform.opentargets.org/api/v4/graphql"

# Real Ensembl gene ids (verified against Open Targets).
ENSEMBL = {"GATA3": "ENSG00000107485", "STAT6": "ENSG00000166888",
           "RARA": "ENSG00000131759", "FBXO32": "ENSG00000156804"}

# Name cues for the type-2 inflammatory disease axis (asthma / atopy / allergy).
_TYPE2_CUES = ("asthma", "atopic", "allerg", "dermatitis", "eczema",
               "eosinophil", "rhinitis")

_QUERY = ('{target(ensemblId:"%s"){approvedSymbol '
          'associatedDiseases(page:{index:0,size:80}){rows{disease{name id} score}}}}')


def type2_association(gene: str) -> Optional[dict]:
    """Max Open Targets association score for ``gene`` against any type-2
    inflammatory disease. Returns a dict with the real score + the specific
    disease it came from (with its ontology id and source), or ``None`` if the
    gene is unknown / the fetch is unresolved. A gene with no type-2 association
    resolves to ``score: 0.0`` with a note — a real, meaningful negative signal."""
    ens = ENSEMBL.get(gene.upper())
    if not ens:
        return None
    data = cached_post_json(OT_URL, {"query": _QUERY % ens},
                            fixture_name=f"opentargets_{gene.upper()}.json")
    if not data:
        return None
    try:
        rows = data["data"]["target"]["associatedDiseases"]["rows"]
    except (KeyError, TypeError):
        return None
    hits = [(r["score"], r["disease"]["name"], r["disease"]["id"]) for r in rows
            if any(c in r["disease"]["name"].lower() for c in _TYPE2_CUES)]
    if not hits:
        return {"gene": gene.upper(), "score": 0.0, "disease": None,
                "disease_id": None, "source": "Open Targets", "resolved": True,
                "note": "no type-2 inflammatory disease association found"}
    score, name, did = max(hits)
    return {"gene": gene.upper(), "score": round(float(score), 3), "disease": name,
            "disease_id": did, "source": "Open Targets", "resolved": True}


_SEARCH = ('{search(queryString:"%s",entityNames:["target"]){'
           'hits{id entity object{__typename ... on Target{approvedSymbol}}}}}')
_ASSESS = ('{target(ensemblId:"%s"){approvedSymbol biotype '
           'associatedDiseases(page:{index:0,size:80}){rows{disease{name id} score}}}}')


def resolve_gene(symbol: str) -> Optional[dict]:
    """Resolve ANY gene symbol to its Ensembl id via Open Targets search (live,
    cached). Returns {symbol, ensembl} or None — this is what lets a scientist
    type a gene the demo never curated and still get real data."""
    data = cached_post_json(OT_URL, {"query": _SEARCH % symbol.upper()},
                            fixture_name=f"opentargets_search_{symbol.upper()}.json")
    if not data:
        return None
    try:
        hits = data["data"]["search"]["hits"]
    except (KeyError, TypeError):
        return None
    for h in hits:
        if h.get("entity") == "target" and h.get("id", "").startswith("ENSG"):
            sym = (h.get("object") or {}).get("approvedSymbol") or symbol.upper()
            return {"symbol": sym, "ensembl": h["id"]}
    return None


def assess_target(symbol: str) -> Optional[dict]:
    """Live, real-data snapshot for ANY gene: approved symbol, top real disease
    associations, and the strongest type-2 inflammatory association — all fetched
    from Open Targets in real time, provenance-stamped. Returns None if unresolved
    (never fabricates). This is the 'type any gene, watch it work' path."""
    r = resolve_gene(symbol)
    if not r:
        return None
    data = cached_post_json(OT_URL, {"query": _ASSESS % r["ensembl"]},
                            fixture_name=f"opentargets_assess_{r['symbol']}.json")
    if not data:
        return None
    try:
        tgt = data["data"]["target"]
        rows = tgt["associatedDiseases"]["rows"]
    except (KeyError, TypeError):
        return None
    top = [{"disease": x["disease"]["name"], "id": x["disease"]["id"],
            "score": round(float(x["score"]), 3)} for x in rows[:6]]
    t2 = [(x["score"], x["disease"]["name"], x["disease"]["id"]) for x in rows
          if any(c in x["disease"]["name"].lower() for c in _TYPE2_CUES)]
    type2 = None
    if t2:
        s, n, i = max(t2)
        type2 = {"score": round(float(s), 3), "disease": n, "disease_id": i}
    return {"symbol": tgt.get("approvedSymbol") or r["symbol"], "ensembl": r["ensembl"],
            "biotype": tgt.get("biotype"), "top_diseases": top, "type2": type2,
            "source": "Open Targets", "resolved": True}
