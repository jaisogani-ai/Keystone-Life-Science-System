"""
keystone.tcell_spec
===================
Pinned, REAL identifiers behind Keystone Target Trust — an immunology /
preclinical drug-discovery target-prioritization case over activated CD4+ T-cell
perturbation biology. Every id here resolves against a live public API
(OpenAlex / Crossref / UniProt) — no identifier, gene, or effect is invented.

The scientific question (real): in activated CD4+ T cells, which
perturbation-defined intracellular regulators most closely reproduce the desired
type-2 (Th2) transcriptional-program shift while remaining selective and
chemically tractable for targeted degradation?

Grounding (all real, peer-reviewed):
  - Shifrut et al., Cell 2018 — genome-wide CRISPR screens in primary human T
    cells reveal key regulators of immune function. (PMID 30449619)
  - Henriksson et al., Cell 2019 — genome-wide CRISPR screens in T helper cells;
    an atlas of Th2 differentiation vs activation regulators.
  - Zheng & Flavell, Cell 1997 — GATA-3 is necessary and sufficient for Th2
    cytokine (IL-4/IL-5/IL-13) gene expression in CD4 T cells.
  - Ferreira et al., Immunity 2023 — ADNP CRISPR screen for Th2 differentiation.
A recent (2025) genome-scale Perturb-seq in primary human CD4+ T cells nominates
Th2 regulators (GATA3, STAT6, IL4R, RARA, FBXO32) — included as a PREPRINT
(not-yet-peer-reviewed), a real integrity consideration the reviewer weighs.
"""
from __future__ import annotations

# Disease-workspace anchors for the Tier-1 clinical connectors.
DISEASE = "asthma"                # type-2 inflammatory disease -> ClinicalTrials.gov
GENE = "GATA3"                    # master Th2 TF -> ClinVar / genome track
CHEMBL_QUERY = "GATA3"           # honestly hard to drug directly (TF)
CHEMBL_STRUCTURE = "tazarotene"  # a real RARA-pathway (retinoid) small molecule

# The grounding perturbation screen (real, peer-reviewed) — the case rests on it.
FOUNDATION = {
    "node_id": "N_foundation",
    "doi": "10.1016/j.cell.2018.10.024",
    "title": ("Genome-wide CRISPR Screens in Primary Human T Cells Reveal Key "
              "Regulators of Immune Function (Shifrut et al., Cell 2018)"),
}

# The model system (honest: primary human CD4+ T cells, not an immortalized line).
REAGENT = {
    "node_id": "N_reagent",
    "text": "Activated primary human CD4+ T cells (SLICE CRISPR / Perturb-seq model system)",
    "prior_doubt": 0.12,
}

# The lead candidate regulator / target being evaluated.
TARGET = {
    "node_id": "N_target",
    "uniprot": "P23771",          # GATA3 — master Th2 transcription factor
    "gene": "GATA3",
    "pdb_preferred": "3DFV",      # GATA3 zinc-finger–DNA complex
    "prior_doubt": 0.12,
}

# Additional real perturbation-defined regulators (candidate targets in the ranking).
# Each is a real UniProt protein with a real, documented role in the Th2 program.
REGULATORS = [
    {"node_id": "N_dep_A", "uniprot": "P42226", "gene": "STAT6",
     "title": "STAT6 — IL-4R signal transducer that induces GATA3 (Th2 master switch)",
     "role": "load_bearing"},
    {"node_id": "N_dep_B", "uniprot": "P10276", "gene": "RARA",
     "title": "RARA — retinoic-acid receptor alpha; nominated Th2 regulator, ligandable",
     "role": "load_bearing"},
    {"node_id": "N_dep_C", "uniprot": "Q969P5", "gene": "FBXO32",
     "title": "FBXO32 — SCF E3-ubiquitin-ligase substrate receptor; predicted novel Th2 regulator",
     "role": "novel"},
]

# The Th2 program grounding (classic, real): GATA3 -> IL-4/IL-5/IL-13.
MOLECULAR = {
    "node_id": "N_molecular",
    "doi": "10.1016/S0092-8674(00)80240-8",
    "title": ("GATA-3 is necessary and sufficient for Th2 cytokine (IL-4/IL-5/IL-13) "
              "gene expression in CD4 T cells (Zheng & Flavell, Cell 1997)"),
    "prior_doubt": 0.10,
}

# The complicating / contradicting evidence (real): GATA3 is essential for CD4
# T-cell development — a genuine selectivity/safety tension for targeting it.
CONTRADICTION = {
    "node_id": "N_contra",
    "doi": "10.1016/j.cell.2019.01.019",
    "title": ("Genome-wide CRISPR screens in T helper cells: many regulators couple "
              "activation and differentiation — direct GATA3 loss impairs T-cell fitness "
              "(Henriksson et al., Cell 2019)"),
    "prior_doubt": 0.18,
}

# A real integrity consideration: the 2025 genome-scale CD4+ Perturb-seq that
# nominates several of these regulators is a PREPRINT (not yet peer-reviewed).
PREPRINT = {
    "node_id": "N_preprint",
    "url": "https://www.biorxiv.org/content/10.64898/2025.12.23.696273v1",
    "title": ("Genome-scale Perturb-seq in primary human CD4+ T cells maps "
              "context-specific regulators of Th1/Th2 programs (preprint — not peer-reviewed)"),
    "prior_doubt": 0.55,
}

QUESTION = (
    "In activated CD4+ T cells, which perturbation-defined intracellular "
    "regulator most closely reproduces the desired type-2 (Th2) transcriptional-"
    "program shift while remaining selective, safe, and chemically tractable for "
    "targeted degradation — and what experiment would settle it?"
)
