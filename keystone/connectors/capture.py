"""
keystone.connectors.capture
===========================
One-shot tool that pulls the real records behind the glioblastoma demo from the
live APIs and pins them as offline fixtures, so ``build_gbm_graph()`` and the
tests run offline against *real* data and reproduce identically.

    KEYSTONE_LIVE=1 python -m keystone.connectors.capture

Re-run only to refresh the pinned real data. Nothing here fabricates: it saves
exactly what the APIs return.
"""
from __future__ import annotations

import json
import sys

import requests

from keystone.connectors.http_cache import USER_AGENT, save_fixture
from keystone.gbm_spec import (ALL_WORK_IDS, FOUNDATION, REAGENT, TARGET)

# The real demo entities (all verified against the live APIs).
FOUNDATION_ID = FOUNDATION["openalex"]
FOUNDATION_DOI = FOUNDATION["doi"]
CELL_LINE = REAGENT["cellosaurus"]   # U-87MG (misidentified line)
TARGET_UNIPROT = TARGET["uniprot"]   # Cathepsin B

_S = requests.Session()
_S.headers.update({"User-Agent": USER_AGENT})


def _get(url, params=None):
    r = _S.get(url, params=params, timeout=40)
    r.raise_for_status()
    return r.json()


def main() -> int:
    doi_slug = FOUNDATION_DOI.replace("/", "_")

    print("openalex works (foundation + every pinned node)...")
    for wid in ALL_WORK_IDS:
        save_fixture(f"openalex_{wid}.json", _get(
            f"https://api.openalex.org/works/{wid}",
            {"select": "id,doi,title,publication_year,publication_date,"
                       "cited_by_count,is_retracted"}))

    print("openalex citers...")
    save_fixture(f"openalex_citers_{FOUNDATION_ID}.json", _get(
        "https://api.openalex.org/works",
        {"filter": f"cites:{FOUNDATION_ID}", "sort": "cited_by_count:desc",
         "per-page": "25",
         "select": "id,doi,title,publication_year,publication_date,"
                   "cited_by_count,is_retracted"}))

    print("crossref / retraction watch...")
    save_fixture(f"crossref_{doi_slug}.json",
                 _get(f"https://api.crossref.org/works/{FOUNDATION_DOI}"))

    print("cellosaurus...")
    save_fixture(f"cellosaurus_{CELL_LINE}.json", _get(
        f"https://api.cellosaurus.org/cell-line/{CELL_LINE}", {"format": "json"}))

    print("semantic scholar contexts...")
    try:
        save_fixture(f"s2_citations_{doi_slug}.json", _get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{FOUNDATION_DOI}/citations",
            {"fields": "contexts,intents,isInfluential,title,year,externalIds",
             "limit": "40"}))
    except Exception as e:  # S2 rate-limits aggressively; keep any prior fixture
        print("  s2 skipped:", e)

    print("uniprot target...")
    save_fixture(f"uniprot_{TARGET_UNIPROT}.json",
                 _get(f"https://rest.uniprot.org/uniprotkb/{TARGET_UNIPROT}.json"))

    print("done — fixtures pinned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
