"""
keystone.prior_art
=================
"Did someone already discover this?" — the prior-art check.

Given a hypothesis statement or research question, surface the CLOSEST existing
work from OpenAlex so a scientist does not re-run an experiment that is already
published. Honest by construction:

  * it returns REAL OpenAlex records (or an empty list) — never a fabricated
    paper;
  * it SURFACES overlap; it never issues a novelty verdict — "is this novel?"
    is the scientist's judgment, not the tool's;
  * it ties into the post-publication layer: if the closest prior work is
    retracted, it says so (so you don't build on a retracted result).
"""
from __future__ import annotations

import re

from keystone.connectors import registry as R

_MAX = 8
# a pasted identifier resolves the EXACT record (not a keyword search)
_DOI_RE = re.compile(r"(10\.\d{4,}/[^\s\"'<>]+)", re.I)
_PMID_RE = re.compile(r"^\s*(?:pmid:?\s*)?(\d{5,9})\s*$", re.I)


def _resolve_identifier(q: str) -> dict | None:
    """If ``q`` is a DOI or PMID, resolve the EXACT OpenAlex record directly
    (``works/doi:…`` / ``works/pmid:…``) instead of a free-text search — a bare
    DOI never matches a keyword query. Cross-checks retraction via Crossref/
    Retraction Watch (OpenAlex's flag can lag). Returns ``None`` if ``q`` is not an
    identifier, or if the record does not resolve (never fabricates a match)."""
    doi_m = _DOI_RE.search(q)
    pmid_m = _PMID_RE.match(q)
    if doi_m:
        ident = doi_m.group(1).rstrip(").,;")
        work = R.openalex_work("doi:" + ident)
    elif pmid_m:
        ident = "PMID:" + pmid_m.group(1)
        work = R.openalex_work("pmid:" + pmid_m.group(1))
    else:
        return None
    if not work or not work.get("resolved"):
        return None
    is_retracted = bool(work.get("is_retracted"))
    if doi_m:
        try:
            is_retracted = is_retracted or bool(R.retraction_status(ident).get("is_retracted"))
        except Exception:
            pass
    return {
        "identifier": ident,
        "match": {
            "title": work.get("title"),
            "doi": (work.get("doi") or "").replace("https://doi.org/", "") or (ident if doi_m else None),
            "url": (f"https://doi.org/{ident}" if doi_m else None),
            "year": work.get("year"),
            "cited_by_count": work.get("cited_by_count"),
            "is_retracted": is_retracted,
        },
    }


def check_prior_art(query: str, limit: int = _MAX) -> dict:
    """Return the closest existing work for a claim/question. A pasted DOI/PMID
    resolves the EXACT record; free text runs a real OpenAlex relevance search.
    Deterministic; no novelty judgment, no fabricated paper."""
    q = (query or "").strip()
    if not q:
        return {"query": "", "resolved": False, "matches": [],
                "any_retracted": False,
                "note": "no query supplied — nothing searched."}

    ident = _resolve_identifier(q)
    if ident is not None:
        m = ident["match"]
        note = (f"Resolved the exact record for {ident['identifier']}. A resolvable "
                "identifier proves the source EXISTS — never that its claim is true.")
        if m["is_retracted"]:
            note += " ⚠ This record is RETRACTED — do not build on it."
        return {"query": q, "resolved": True, "matches": [m],
                "any_retracted": bool(m["is_retracted"]), "note": note}

    hits = R.openalex_search(q, limit=limit)
    matches = [{
        "title": h.get("title"),
        "doi": h.get("doi"),
        "url": (f"https://doi.org/{h['doi']}" if h.get("doi") else None),
        "year": h.get("year"),
        "cited_by_count": h.get("cited_by_count"),
        "is_retracted": bool(h.get("is_retracted")),
    } for h in hits if h.get("title")]

    any_retracted = any(m["is_retracted"] for m in matches)
    if matches:
        note = ("Closest existing work by relevance. Keystone surfaces overlap "
                "so you don't re-run a published experiment — it does NOT judge "
                "novelty; that is your call.")
        if any_retracted:
            note += (" ⚠ At least one close match is RETRACTED — do not build "
                     "on it without checking the retraction.")
    else:
        note = ("No matching work resolved against OpenAlex (or the search is "
                "offline without a pinned result). Absence of a match is not "
                "evidence of novelty.")

    return {
        "query": q,
        "resolved": bool(matches),
        "matches": matches,
        "any_retracted": any_retracted,
        "note": note,
    }
