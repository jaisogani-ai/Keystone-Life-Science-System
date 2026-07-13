"""
keystone.ich_spec
================
Third domain — intracerebral / brain hemorrhage ("NeuroHem"), same pattern as
``gbm_spec.py`` and ``insulin_spec.py``: pinned REAL identifiers, every one
resolvable through the existing connectors (OpenAlex / Crossref-RetractionWatch /
Cellosaurus / UniProt / Semantic Scholar / ChEMBL / ClinVar / ClinicalTrials.gov)
and captured as an offline fixture. No identifier or citing sentence is invented.

The story (all true): a 2009 paper claiming matrix metalloproteinase-9 (MMP-9)
potentiates early brain injury after intracerebral hemorrhage was **RETRACTED**
(``retraction_status`` confirms it via Crossref). It still has 59 citers — real
papers that build on the MMP-9 mechanism. MMP-9 (UniProt P14780) is a genuine,
druggable secondary-injury target in hemorrhage (blood-brain-barrier breakdown,
perihematomal edema), yet no MMP-9 inhibitor is approved for hemorrhage — so the
decision engine's "what experiment settles it?" question is real.

Same topology as GBM (retracted foundation → real citers inherit doubt), with a
real dual-role CONTRADICTION: Zhao et al. Nature Medicine 2006 showed MMP-9 also
drives *beneficial* delayed neurovascular remodeling — so "MMP-9 is purely
harmful" is genuinely contested, not fabricated.

This domain is presented in the UI as "NeuroHem", a themed view of Keystone —
NOT a separate product. Hemorrhage detection on a CT, patient brain-waves/vitals,
and treatment recommendations remain REFUSED by the Scientific Safety Boundary.
"""
from __future__ import annotations

# Disease-workspace anchors for the Tier-1 clinical connectors.
DISEASE = "intracerebral hemorrhage"          # -> ClinicalTrials.gov
GENE = "MMP9"                                 # -> ClinVar (GRCh38 -> genome track)
CHEMBL_QUERY = "matrix metalloproteinase 9"  # -> ChEMBL (MMP-9 inhibitors exist; none approved for ICH)
CHEMBL_STRUCTURE = "minocycline"             # -> ChEMBL 2D structure (MMP-inhibiting neuroprotectant, studied in stroke)

# The retracted foundation — MMP-9 potentiates early brain injury after hemorrhage.
FOUNDATION = {
    "node_id": "N_foundation",
    "openalex": "W1973210660",
    "doi": "10.1179/016164109x12478302362491",
    "retracted": True,          # verified via retraction_status — real retraction
}

# A standard neuroinflammation model line. BV-2 microglia has no Cellosaurus
# problematic flag (honestly clean), so this domain has no reagent-integrity beat
# — that is fine, we do not invent one (same honesty as insulin's 3T3-L1).
REAGENT = {
    "node_id": "N_reagent",
    "cellosaurus": "CVCL_0182",   # BV-2 microglia (neuroinflammation model)
    "prior_doubt": 0.25,
}

# The target: matrix metalloproteinase-9 — central to BBB breakdown and edema.
TARGET = {
    "node_id": "N_target",
    "uniprot": "P14780",          # MMP9
    "pdb_preferred": "1L6J",
    "prior_doubt": 0.10,
}

# Real downstream citers of the retracted foundation, resolved by DOI against the
# Semantic Scholar citing-context fixture. Each carries a REAL citing sentence.
#   dep_A – load_bearing: deploys the MMP-9 secondary-injury mechanism as support
#   dep_B – incidental:   cites as general background on cerebral hemorrhage
DEPENDENTS = [
    {"node_id": "N_dep_A", "doi": "10.1007/s13311-011-0038-0", "role": "load_bearing",
     "title": "Role of Matrix Metalloproteinases and Therapeutic Benefits of Their Inhibition in Brain Injury"},
    {"node_id": "N_dep_B", "doi": "10.1177/0271678x18774666", "role": "incidental",
     "title": "Brain endothelial cell junctions after cerebral hemorrhage (background)"},
]

# Real molecular grounding (MMP-9 → BBB breakdown / edema) and the real dual-role
# contradiction (MMP-9 also drives beneficial delayed remodeling — Zhao 2006).
MOLECULAR = {"node_id": "N_molecular", "doi": "10.3390/ijms21249739",
             "title": "Matrix metalloproteinases and their inhibitors in brain injury and hemorrhage",
             "prior_doubt": 0.15}
CONTRADICTION = {"node_id": "N_contra", "doi": "10.1038/nm1387",
                 "title": "Role of matrix metalloproteinases in delayed cortical responses after stroke (MMP-9 is also beneficial)",
                 "prior_doubt": 0.20}

# OpenAlex works pinned individually (the retracted foundation).
ALL_WORK_IDS = [FOUNDATION["openalex"]]

QUESTION = (
    "In intracerebral (brain) hemorrhage, is matrix metalloproteinase-9 (MMP-9) "
    "a safe therapeutic target for reducing secondary brain injury — given that "
    "the foundational paper establishing its role has been retracted and MMP-9 "
    "also drives beneficial recovery — and what experiment would settle it?"
)
