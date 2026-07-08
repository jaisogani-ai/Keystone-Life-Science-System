"""
keystone.connectors.registry
============================
Real connectors to public research databases, each behind the cache-first HTTP
layer. Every function returns a *normalized, provenance-tagged* record or a
``resolved: False`` marker — the determinism boundary (rule 7 / rule 6): a
connector never invents a DOI, accession, or citing context. A failed lookup is
reported as ``unresolved``, not filled in.

Wired live here (with fixture fallback): OpenAlex, Crossref/Retraction-Watch,
Cellosaurus, Semantic Scholar (citing contexts + isInfluential), UniProt.
The remaining catalogue databases are declared for provenance completeness.
"""
from __future__ import annotations

from typing import Optional

from keystone.connectors.http_cache import cached_get_json

CATALOGUE = [
    "openalex", "retraction_watch", "cellosaurus", "semantic_scholar",
    "uniprot", "pdb", "pubmed", "geo", "sra", "clinvar", "chembl",
    "reactome", "clinicaltrials",
]

# Tier-1 wired (real API, cache->live->fixture, keyless public endpoints):
#   openalex, retraction_watch (crossref), cellosaurus, semantic_scholar,
#   uniprot, clinicaltrials, chembl, reactome, clinvar  (see connectors/clinical.py)
# Still declared-only (Tier 2, honest _unresolved): pdb-structure-search, pubmed,
#   geo, sra.
WIRED = ["openalex", "retraction_watch", "cellosaurus", "semantic_scholar",
         "uniprot", "clinicaltrials", "chembl", "reactome", "clinvar"]


def _unresolved(kind: str, query: str) -> dict:
    return {"resolved": False, "kind": kind, "query": query,
            "source": "unresolved", "note": "lookup failed; not fabricated"}


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------
def openalex_work(work_id: str) -> dict:
    data = cached_get_json(
        f"https://api.openalex.org/works/{work_id}",
        params={"select": "id,doi,title,publication_year,publication_date,"
                          "cited_by_count,is_retracted"},
        fixture_name=f"openalex_{work_id}.json")
    if not data or "id" not in data:
        return _unresolved("work", work_id)
    return {
        "resolved": True, "source": "openalex",
        "id": data["id"].split("/")[-1], "doi": data.get("doi"),
        "title": data.get("title"), "year": data.get("publication_year"),
        "date": data.get("publication_date"),
        "cited_by_count": data.get("cited_by_count"),
        "is_retracted": data.get("is_retracted", False),
    }


def openalex_citers(work_id: str, limit: int = 25) -> list[dict]:
    data = cached_get_json(
        "https://api.openalex.org/works",
        params={"filter": f"cites:{work_id}", "sort": "cited_by_count:desc",
                "per-page": str(limit),
                "select": "id,doi,title,publication_year,publication_date,"
                          "cited_by_count,is_retracted"},
        fixture_name=f"openalex_citers_{work_id}.json")
    if not data or "results" not in data:
        return []
    out = []
    for c in data["results"]:
        out.append({
            "resolved": True, "source": "openalex",
            "id": c["id"].split("/")[-1], "doi": c.get("doi"),
            "title": c.get("title"), "year": c.get("publication_year"),
            "date": c.get("publication_date"),
            "cited_by_count": c.get("cited_by_count"),
            "is_retracted": c.get("is_retracted", False),
        })
    return out


# ---------------------------------------------------------------------------
# Retraction Watch (via Crossref, which now carries the RW dataset)
# ---------------------------------------------------------------------------
def retraction_status(doi: str) -> dict:
    clean = doi.replace("https://doi.org/", "")
    data = cached_get_json(f"https://api.crossref.org/works/{clean}",
                           fixture_name=f"crossref_{clean.replace('/', '_')}.json")
    if not data or "message" not in data:
        return _unresolved("retraction", doi)
    msg = data["message"]
    for upd in msg.get("updated-by", []) or []:
        if upd.get("type") == "retraction":
            parts = upd.get("updated", {}).get("date-parts", [[None]])[0]
            date = "-".join(f"{p:02d}" for p in parts if p is not None)
            return {"resolved": True, "source": "retraction_watch",
                    "is_retracted": True, "retraction_date": date,
                    "retraction_doi": upd.get("DOI"),
                    "record_id": upd.get("record-id"),
                    "via": upd.get("source")}
    return {"resolved": True, "source": "retraction_watch",
            "is_retracted": False, "retraction_date": None}


# ---------------------------------------------------------------------------
# Cellosaurus — cell-line identity / problematic-line flags
# ---------------------------------------------------------------------------
def cellosaurus_line(accession: str) -> dict:
    data = cached_get_json(
        f"https://api.cellosaurus.org/cell-line/{accession}",
        params={"format": "json"},
        fixture_name=f"cellosaurus_{accession}.json")
    try:
        cl = data["Cellosaurus"]["cell-line-list"][0]
    except (TypeError, KeyError, IndexError):
        return _unresolved("cell_line", accession)
    names = [n["value"] for n in cl.get("name-list", [])]
    problematic = None
    for c in cl.get("comment-list", []):
        if c.get("category") == "Problematic cell line":
            problematic = c.get("value") or ""
    return {"resolved": True, "source": "cellosaurus",
            "accession": accession, "name": names[0] if names else accession,
            "synonyms": names[:4], "problematic": problematic}


# ---------------------------------------------------------------------------
# Semantic Scholar — real citing contexts + the isInfluential load-bearing hint
# ---------------------------------------------------------------------------
def semantic_scholar_contexts(doi: str, limit: int = 40) -> list[dict]:
    clean = doi.replace("https://doi.org/", "")
    data = cached_get_json(
        f"https://api.semanticscholar.org/graph/v1/paper/DOI:{clean}/citations",
        params={"fields": "contexts,intents,isInfluential,title,year,externalIds",
                "limit": str(limit)},
        fixture_name=f"s2_citations_{clean.replace('/', '_')}.json")
    if not data or "data" not in data:
        return []
    out = []
    for row in data["data"]:
        paper = row.get("citingPaper", {}) or {}
        out.append({
            "resolved": True, "source": "semantic_scholar",
            "title": paper.get("title"), "year": paper.get("year"),
            "doi": (paper.get("externalIds") or {}).get("DOI"),
            "is_influential": bool(row.get("isInfluential")),
            "intents": row.get("intents") or [],
            "contexts": row.get("contexts") or [],
        })
    return out


# ---------------------------------------------------------------------------
# UniProt — target protein + a PDB structure for the 3D artifact
# ---------------------------------------------------------------------------
def uniprot_protein(accession: str) -> dict:
    data = cached_get_json(
        f"https://rest.uniprot.org/uniprotkb/{accession}.json",
        fixture_name=f"uniprot_{accession}.json")
    if not data or "proteinDescription" not in data:
        return _unresolved("protein", accession)
    name = (data["proteinDescription"].get("recommendedName", {})
            .get("fullName", {}).get("value"))
    gene = None
    genes = data.get("genes") or []
    if genes:
        gene = genes[0].get("geneName", {}).get("value")
    pdbs = [x["id"] for x in data.get("uniProtKBCrossReferences", [])
            if x.get("database") == "PDB"]
    return {"resolved": True, "source": "uniprot", "accession": accession,
            "name": name, "gene": gene, "pdb_ids": pdbs[:6]}
