"""
keystone.connectors.clinical
===========================
Additive Tier-1 connectors for the Disease Workspace. Each wraps a REAL, keyless
public API through the same cache->live->fixture layer as ``registry.py`` and
honours the determinism boundary: a miss returns ``_unresolved(...)``; a genuine
zero result (e.g. no approved drug targets cathepsin B) returns ``resolved: True``
with an empty list — never a fabricated value.

Exact endpoints (nameable, per the Tier-1 rule):
  clinical_trials  -> https://clinicaltrials.gov/api/v2/studies
  chembl_drugs     -> https://www.ebi.ac.uk/chembl/api/data/{target,mechanism,molecule}
  reactome_pathways-> https://reactome.org/ContentService/data/mapping/UniProt/{acc}/pathways
  clinvar_variants -> https://eutils.ncbi.nlm.nih.gov/entrez/eutils/{esearch,esummary}.fcgi
"""
from __future__ import annotations

from keystone.connectors.http_cache import cached_get_json
from keystone.connectors.registry import _unresolved

_CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"
_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.lower())[:40]


# ---------------------------------------------------------------------------
# ClinicalTrials.gov v2
# ---------------------------------------------------------------------------
def clinical_trials(condition: str, limit: int = 8) -> dict:
    data = cached_get_json(
        "https://clinicaltrials.gov/api/v2/studies",
        params={"query.cond": condition, "pageSize": str(limit),
                "countTotal": "true", "format": "json"},
        fixture_name=f"trials_{_slug(condition)}.json")
    if not data or "studies" not in data:
        return _unresolved("clinical_trials", condition)
    trials = []
    for s in data["studies"]:
        p = s.get("protocolSection", {})
        idm = p.get("identificationModule", {})
        st = p.get("statusModule", {})
        des = p.get("designModule", {})
        elig = (p.get("eligibilityModule", {}).get("eligibilityCriteria") or "")
        trials.append({
            "nct_id": idm.get("nctId"), "title": idm.get("briefTitle"),
            "status": st.get("overallStatus"),
            "phase": ", ".join(des.get("phases", []) or []) or "N/A",
            "eligibility": " ".join(elig.split())[:240],
            "url": f"https://clinicaltrials.gov/study/{idm.get('nctId')}"})
    return {"resolved": True, "source": "clinicaltrials.gov",
            "condition": condition, "total": data.get("totalCount"),
            "trials": trials}


# ---------------------------------------------------------------------------
# ChEMBL — approved/known drugs whose mechanism targets the protein
# ---------------------------------------------------------------------------
def chembl_drugs(target_query: str, limit: int = 8) -> dict:
    ts = cached_get_json(f"{_CHEMBL}/target/search",
                         params={"q": target_query, "format": "json"},
                         fixture_name=f"chembl_target_{_slug(target_query)}.json")
    targets = [t for t in (ts or {}).get("targets", [])
               if t.get("organism") == "Homo sapiens"] if ts else []
    if not targets:
        return _unresolved("chembl_target", target_query)
    tid = targets[0].get("target_chembl_id")
    mech = cached_get_json(f"{_CHEMBL}/mechanism",
                           params={"target_chembl_id": tid, "format": "json"},
                           fixture_name=f"chembl_mechanism_{tid}.json") or {}
    rows = mech.get("mechanisms", []) or []
    mol_ids = list(dict.fromkeys(m.get("molecule_chembl_id") for m in rows
                                 if m.get("molecule_chembl_id")))[:limit]
    names = {}
    if mol_ids:
        mols = cached_get_json(
            f"{_CHEMBL}/molecule",
            params={"molecule_chembl_id__in": ",".join(mol_ids), "format": "json"},
            fixture_name=f"chembl_molecule_{tid}.json") or {}
        names = {m.get("molecule_chembl_id"): m.get("pref_name")
                 for m in mols.get("molecules", [])}
    drugs = [{"chembl_id": m.get("molecule_chembl_id"),
              "name": names.get(m.get("molecule_chembl_id")) or m.get("molecule_chembl_id"),
              "action": m.get("action_type"),
              "moa": (m.get("mechanism_of_action") or "")[:80]}
             for m in rows[:limit]]
    return {"resolved": True, "source": "chembl", "target_chembl_id": tid,
            "target_name": targets[0].get("pref_name"),
            "count": len(rows), "drugs": drugs}


# ---------------------------------------------------------------------------
# Reactome — pathways containing the protein (by UniProt accession)
# ---------------------------------------------------------------------------
def reactome_pathways(uniprot: str, limit: int = 10) -> dict:
    data = cached_get_json(
        f"https://reactome.org/ContentService/data/mapping/UniProt/{uniprot}/pathways",
        params={"species": "9606"},
        fixture_name=f"reactome_{uniprot}.json")
    if not isinstance(data, list):
        return _unresolved("reactome_pathways", uniprot)
    paths = [{"st_id": p.get("stId"), "name": p.get("displayName"),
              "url": f"https://reactome.org/PathwayBrowser/#/{p.get('stId')}"}
             for p in data[:limit]]
    return {"resolved": True, "source": "reactome", "uniprot": uniprot,
            "count": len(data), "pathways": paths}


# ---------------------------------------------------------------------------
# ClinVar (NCBI eutils) — clinically-annotated variants for a gene
# ---------------------------------------------------------------------------
def clinvar_variants(gene: str, limit: int = 6) -> dict:
    es = cached_get_json(f"{_EUTILS}/esearch.fcgi",
                         params={"db": "clinvar", "term": f"{gene}[gene]",
                                 "retmode": "json", "retmax": str(limit)},
                         fixture_name=f"clinvar_esearch_{_slug(gene)}.json")
    ids = ((es or {}).get("esearchresult", {}) or {}).get("idlist", [])
    if not es or not ids:
        return _unresolved("clinvar", gene)
    total = es["esearchresult"].get("count")
    su = cached_get_json(f"{_EUTILS}/esummary.fcgi",
                         params={"db": "clinvar", "id": ",".join(ids),
                                 "retmode": "json"},
                         fixture_name=f"clinvar_esummary_{_slug(gene)}.json") or {}
    res = su.get("result", {})
    variants = []
    for vid in ids:
        v = res.get(vid, {})
        if not v:
            continue
        sig = (v.get("germline_classification", {}) or {}).get("description")
        variants.append({"id": vid, "title": (v.get("title") or "")[:90],
                         "significance": sig or "not provided"})
    return {"resolved": True, "source": "clinvar", "gene": gene,
            "total": total, "variants": variants}
