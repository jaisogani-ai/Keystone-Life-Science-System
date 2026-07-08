"""
keystone.biology_chain
=====================
The connected-entity chain a scientist follows from bench to clinic:

  Cell -> Protein -> Mutation -> Drug -> Pathway -> Disease -> Trial

Every link is a REAL wired connector (Cellosaurus, UniProt, ClinVar, ChEMBL,
Reactome, the evidence graph, ClinicalTrials.gov), joined by the shared target
gene. This is the extension of the protein viewer the design asks for.

Honest boundary: this is *entity linkage across real databases*, NOT spatial
transcriptomics. True spatial biology (10x Visium / MERFISH / CELLxGENE) needs a
dataset source that is not wired — it is declared Tier 3 here, not faked.
"""
from __future__ import annotations

from keystone.connectors import registry as R
from keystone.connectors import clinical as C


def _spec_and_builder(domain: str):
    if domain == "insulin":
        from keystone import insulin_spec as SPEC
        from keystone.data_insulin import build_insulin_graph as build
        return SPEC, build
    from keystone import gbm_spec as SPEC
    from keystone.data_gbm import build_gbm_graph as build
    return SPEC, build


def _link(layer, entity, source, count=None) -> dict:
    return {"layer": layer, "tier": 1, "entity": entity, "source": source,
            "count": count}


def build_biology_chain(domain: str = "gbm") -> dict:
    spec, build = _spec_and_builder(domain)
    graph = build()

    reagent = R.cellosaurus_line(spec.REAGENT["cellosaurus"])
    protein = R.uniprot_protein(spec.TARGET["uniprot"])
    variants = C.clinvar_variants(spec.GENE)
    drugs = C.chembl_drugs(spec.CHEMBL_QUERY)
    structure = C.chembl_structure(getattr(spec, "CHEMBL_STRUCTURE", ""))
    pathways = C.reactome_pathways(spec.TARGET["uniprot"])
    trials = C.clinical_trials(spec.DISEASE)

    chain = [
        _link("Cell", reagent.get("name"),
              f"Cellosaurus:{spec.REAGENT['cellosaurus']}"),
        _link("Protein", f"{protein.get('gene')} — {protein.get('name')}",
              f"UniProt:{spec.TARGET['uniprot']}"),
        _link("Mutation", f"{variants.get('total')} ClinVar variants",
              "ClinVar", count=variants.get("total")),
        _link("Drug", (f"{drugs.get('count')} drug(s) on {drugs.get('target_name')}"
                       + (f"; SoC {structure.get('name')}" if structure.get('resolved') else "")),
              "ChEMBL", count=drugs.get("count")),
        _link("Pathway", f"{pathways.get('count')} Reactome pathways",
              "Reactome", count=pathways.get("count")),
        _link("Disease", f"{spec.DISEASE} — {len(graph.nodes)}-node evidence graph",
              "EvidenceGraph"),
        _link("Trial", f"{trials.get('total')} trials", "ClinicalTrials.gov",
              count=trials.get("total")),
    ]
    return {
        "domain": domain, "gene": spec.GENE,
        "chain": chain,
        "protein_pdb": (protein.get("pdb_ids") or [None])[0],
        "structure_svg": structure.get("svg") if structure.get("resolved") else None,
        "genome_coords": [v["coord"] for v in variants.get("variants", []) if v.get("coord")],
        "spatial_omics": {
            "tier": 3, "status": "not_wired",
            "note": "true spatial transcriptomics (10x Visium / MERFISH / "
                    "CELLxGENE census) is not wired — this chain is entity "
                    "linkage across real databases, not spatial-omics data."},
    }
