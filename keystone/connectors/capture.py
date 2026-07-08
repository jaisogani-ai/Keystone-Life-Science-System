"""
keystone.connectors.capture
===========================
Pull the real records behind a demo domain from the live APIs and pin them as
offline fixtures, so the graph builders and tests run offline against *real* data
and reproduce identically.

    KEYSTONE_LIVE=1 python -m keystone.connectors.capture --domain gbm
    KEYSTONE_LIVE=1 python -m keystone.connectors.capture --domain insulin

Re-run only to refresh the pinned real data. Nothing here fabricates: it saves
exactly what the APIs return.
"""
from __future__ import annotations

import argparse
import sys

import requests

from keystone.connectors.http_cache import USER_AGENT, save_fixture
from keystone import gbm_spec, insulin_spec

_SPECS = {"gbm": gbm_spec, "insulin": insulin_spec}

_S = requests.Session()
_S.headers.update({"User-Agent": USER_AGENT})


def _get(url, params=None):
    r = _S.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def capture(spec, s2_limit: int = 120) -> None:
    found_id = spec.FOUNDATION["openalex"]
    found_doi = spec.FOUNDATION["doi"]

    print("  openalex works (foundation + pinned nodes)...")
    for wid in spec.ALL_WORK_IDS:
        save_fixture(f"openalex_{wid}.json", _get(
            f"https://api.openalex.org/works/{wid}",
            {"select": "id,doi,title,publication_year,publication_date,"
                       "cited_by_count,is_retracted"}))

    print("  openalex citers...")
    save_fixture(f"openalex_citers_{found_id}.json", _get(
        "https://api.openalex.org/works",
        {"filter": f"cites:{found_id}", "sort": "cited_by_count:desc",
         "per-page": "25",
         "select": "id,doi,title,publication_year,publication_date,"
                   "cited_by_count,is_retracted"}))

    print("  crossref / retraction watch (foundation + retracted deps)...")
    dois = [found_doi] + [d["doi"] for d in spec.DEPENDENTS
                          if d.get("role") == "retracted" or "openalex" in d]
    for doi in dict.fromkeys(dois):
        slug = doi.replace("/", "_")
        save_fixture(f"crossref_{slug}.json",
                     _get(f"https://api.crossref.org/works/{doi}"))

    print("  cellosaurus...")
    save_fixture(f"cellosaurus_{spec.REAGENT['cellosaurus']}.json", _get(
        f"https://api.cellosaurus.org/cell-line/{spec.REAGENT['cellosaurus']}",
        {"format": "json"}))

    print("  semantic scholar contexts...")
    try:
        slug = found_doi.replace("/", "_")
        save_fixture(f"s2_citations_{slug}.json", _get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{found_doi}/citations",
            {"fields": "contexts,intents,isInfluential,title,year,externalIds",
             "limit": str(s2_limit)}))
    except Exception as e:                      # S2 rate-limits; keep any prior fixture
        print("    s2 skipped:", e)

    print("  uniprot target...")
    save_fixture(f"uniprot_{spec.TARGET['uniprot']}.json",
                 _get(f"https://rest.uniprot.org/uniprotkb/{spec.TARGET['uniprot']}.json"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=["gbm", "insulin", "all"], default="all")
    args = ap.parse_args()
    domains = _SPECS.keys() if args.domain == "all" else [args.domain]
    for name in domains:
        print(f"[{name}]")
        capture(_SPECS[name])
    print("done — fixtures pinned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
