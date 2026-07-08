"""
keystone.gbm_spec
================
The pinned, verified real identifiers behind the glioblastoma demo. Every id
here resolves against a live public API (OpenAlex / Crossref-RetractionWatch /
Cellosaurus / UniProt / Semantic Scholar) and is captured as an offline fixture.
This is the single source of truth shared by the capture tool and the graph
builder — no identifier or citing sentence is invented anywhere else.

The story (all true): a 2004 Oncogene paper claiming that RNAi knockdown of
cathepsin B (CTSB) and MMP-9 suppresses glioblastoma invasion, growth and
angiogenesis was **retracted on 2025-04-29** (Retraction Watch record 64194).
293 papers cite it. The dependents below are real citers whose *actual* citing
sentences (from Semantic Scholar) place them as load-bearing, incidental, or —
for one cited 8 months after the retraction — inexcusable.
"""
from __future__ import annotations

# Disease-workspace anchors for the Tier-1 clinical connectors.
DISEASE = "glioblastoma"          # -> ClinicalTrials.gov
GENE = "CTSB"                     # -> ClinVar (returns GRCh38 coords -> genome track)
CHEMBL_QUERY = "cathepsin B"     # -> ChEMBL (honestly returns 0 drugs: undrugged)
CHEMBL_STRUCTURE = "temozolomide"  # -> ChEMBL 2D structure (GBM standard of care)

# The retracted foundation.
FOUNDATION = {
    "node_id": "N_foundation",
    "openalex": "W2016394200",
    "doi": "10.1038/sj.onc.1207616",
}

# The reagent whose identity is itself in doubt (famous real misidentification).
REAGENT = {
    "node_id": "N_reagent",
    "cellosaurus": "CVCL_0022",   # U-87MG (ATCC) — not the original 1968 line
    "prior_doubt": 0.40,
}

# The molecular target (drives the 3D structure artifact).
TARGET = {
    "node_id": "N_target",
    "uniprot": "P07858",          # Cathepsin B (CTSB)
    "pdb_preferred": "1HUC",
    "prior_doubt": 0.10,
}

# Real downstream citers of the retracted foundation, resolved by DOI against the
# Semantic Scholar citing-context fixture. Each carries a REAL citing sentence.
#   dep_A – load_bearing: restates the retracted knockdown finding as fact
#   dep_B – incidental:   off-domain, general bundled mention
#   dep_C – post_retraction: cited the paper after it was retracted (inexcusable)
DEPENDENTS = [
    {"node_id": "N_dep_A", "doi": "10.3390/ijms20143602", "role": "load_bearing",
     "title": "The Role of Cysteine Cathepsins in Cancer Progression and Drug Resistance"},
    {"node_id": "N_dep_B", "doi": "10.1101/520346", "role": "incidental",
     "title": "Wingless promotes JNK/MMPs-positive feedback loop mediated tumour metastasis"},
    {"node_id": "N_dep_C", "openalex": "W7118444080",
     "doi": "10.3389/fonc.2025.1577492", "role": "post_retraction",
     "title": "High intra-tumoral and serum MMP-9 levels in glioma"},
]

# Real molecular grounding (multifunctionality) and the real "dual role"
# contradiction — both resolved by DOI against the same S2 context fixture.
MOLECULAR = {"node_id": "N_molecular", "doi": "10.1016/j.canlet.2019.02.035",
             "title": "Cathepsin B: a sellsword of cancer progression",
             "prior_doubt": 0.15}
CONTRADICTION = {"node_id": "N_contra", "doi": "10.1111/jcmm.14077",
                 "title": "Targeting the lysosome by aminomethylated Riccardin D",
                 "prior_doubt": 0.20}

# OpenAlex works pinned individually (foundation + the post-retraction citer,
# which is not in the top-cited citer page).
ALL_WORK_IDS = [FOUNDATION["openalex"], "W7118444080"]

QUESTION = (
    "In glioblastoma, is the cathepsin B / MMP-9 proteolytic axis a safe "
    "therapeutic target for suppressing tumor invasion — given that the "
    "foundational RNAi paper establishing it has been retracted — and what "
    "experiment would settle it?"
)
