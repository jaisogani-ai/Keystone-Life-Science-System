"""
keystone.insulin_spec
====================
Second domain, same pattern as ``gbm_spec.py``: pinned REAL identifiers for
insulin signalling / insulin resistance, every one resolvable through the
existing connectors (OpenAlex / Crossref-RetractionWatch / Cellosaurus / UniProt
/ Semantic Scholar) and captured as an offline fixture. No identifier or citing
sentence is invented.

The point of this file is the *second calibration number*: the load-bearing
classifier, unchanged, is measured on this domain's real citing sentences
(``keystone/calibration/insulin_citing_sentences.jsonl``). If it lands near the
GBM number, "domain-agnostic" stops being a claim.

An honest asymmetry vs. GBM: the **foundation here is NOT retracted** — Saltiel &
Kahn (2001) is a landmark review, and ``retraction_status`` on it returns clean.
We do NOT fabricate a retraction for parity. Instead the graph carries a REAL
retracted *dependent* (Torres-Leal et al., "CDK4 is an essential insulin
effector", retracted per Retraction Watch), so the doubt machinery is still
exercised — just with a clean foundation and a compromised citer.
"""
from __future__ import annotations

# Disease-workspace anchors for the Tier-1 clinical connectors.
DISEASE = "insulin resistance"       # -> ClinicalTrials.gov
GENE = "IRS1"                        # -> ClinVar
CHEMBL_QUERY = "insulin receptor"   # -> ChEMBL (the druggable receptor of the axis)

# Foundational insulin-signalling paper — Saltiel & Kahn, Nature 2001. NOT retracted.
FOUNDATION = {
    "node_id": "N_foundation",
    "openalex": "W2014887370",
    "doi": "10.1038/414799a",
    "retracted": False,          # verified via retraction_status — real, clean
}

# A standard insulin-signalling model line. 3T3-L1 has no Cellosaurus problematic
# flag (honestly clean), so this domain has no reagent-integrity beat — that is
# fine, we do not invent one.
REAGENT = {
    "node_id": "N_reagent",
    "cellosaurus": "CVCL_0123",   # 3T3-L1 (adipocyte model)
    "prior_doubt": 0.25,
}

# The target: insulin receptor substrate 1 — central to insulin resistance.
TARGET = {
    "node_id": "N_target",
    "uniprot": "P35568",          # IRS1
    "pdb_preferred": "1IRS",
    "prior_doubt": 0.10,
}

# Real downstream citers, resolved by DOI against the S2 citing-context fixture.
#   dep_A – load_bearing: deploys the IRS-1/PI3K/Akt/GLUT4 mechanism as support
#   dep_B – incidental:   cites the review as generic background
#   dep_C – retracted:    a real RETRACTED citer (Retraction Watch confirmed)
DEPENDENTS = [
    {"node_id": "N_dep_A", "doi": "10.3389/fendo.2026.1799702", "role": "load_bearing",
     "title": "Reduced IRS-1 phosphorylation and PI3K/AKT signalling in insulin resistance"},
    {"node_id": "N_dep_B", "doi": "10.3389/fnagi.2026.1710075", "role": "incidental",
     "title": "Insulin as a key regulator of whole-body glucose homeostasis (background)"},
    {"node_id": "N_dep_C", "openalex": "W2212034801", "doi": "10.1172/jci81480",
     "role": "retracted",
     "title": "CDK4 is an essential insulin effector in adipocytes (RETRACTED)"},
]

# Real molecular grounding and a real metabolic-vs-mitogenic complication.
MOLECULAR = {"node_id": "N_molecular", "doi": "10.25258/ijddt.16.26s.102",
             "title": "IRS-1/PI3K/Akt/GLUT4 signalling is impaired in type 2 diabetes",
             "prior_doubt": 0.15}
CONTRADICTION = {"node_id": "N_contra", "doi": "10.1111/jcmm.71183",
                 "title": "Insulin signalling also exerts strong mitogenic (non-metabolic) effects",
                 "prior_doubt": 0.20}

# OpenAlex works pinned individually (foundation + the retracted citer).
ALL_WORK_IDS = [FOUNDATION["openalex"], "W2212034801"]

QUESTION = (
    "In insulin resistance / type 2 diabetes, is the IRS-1 / PI3K / Akt axis a "
    "safe therapeutic target for restoring insulin sensitivity — and which "
    "downstream evidence is trustworthy given a retracted effector paper in the "
    "citation graph?"
)
