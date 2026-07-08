"""
keystone.workspace
=================
The Disease Workspace assembler — the OS surface that unifies every existing
module into one view. It is a deterministic COMPOSITION (no new reasoning, no
LLM): it runs the existing loop, then projects graph + ledger + connectors into
tier-tagged tabs.

Every tab carries its scope tier and an honest status:
  tier 1 + resolved     -> real data from a wired connector or a projection
  tier 1 + zero result  -> resolved:true with an empty list (e.g. undrugged
                           target) — a real finding, never padded
  tier 2 + not_yet_wired-> schema + slot present, explicitly incomplete

A tab never silently empties and never fabricates a value (CONTRIBUTING).
"""
from __future__ import annotations

from keystone.workbench import run
from keystone.agents.reasoner import HeuristicReasoner
from keystone.connectors import registry as R
from keystone.connectors import clinical as C
from keystone.deterministic.contradiction_mining import mine_contradictions
from keystone.deterministic.gap_detection import detect_gaps
from keystone.artifacts.graph_export import graph_to_dict
from keystone.artifacts.render import genome_track_svg
from keystone.replay import record_session
from keystone.reasoning_panel import future_experiments_tree, research_readiness


def _tier1(data, note: str = "") -> dict:
    return {"tier": 1, "status": "resolved", "note": note, "data": data}


def _tier2(note: str) -> dict:
    return {"tier": 2, "status": "not_yet_wired", "note": note, "data": None}


def _spec_and_builder(domain: str):
    if domain == "insulin":
        from keystone import insulin_spec as SPEC
        from keystone.data_insulin import build_insulin_graph as build
        return SPEC, build
    from keystone import gbm_spec as SPEC
    from keystone.data_gbm import build_gbm_graph as build
    return SPEC, build


def build_workspace(domain: str = "gbm", reasoner=None):
    """Assemble the full Disease Workspace. Returns (workspace_dict, graph,
    ledger, hyp, review). Deterministic given fixtures."""
    spec, build = _spec_and_builder(domain)
    reasoner = reasoner or HeuristicReasoner()
    graph = build()
    ledger, hyp, review = run(spec.QUESTION, graph, reasoner)

    target = R.uniprot_protein(spec.TARGET["uniprot"])
    trials = C.clinical_trials(spec.DISEASE)
    drugs = C.chembl_drugs(spec.CHEMBL_QUERY)
    pathways = C.reactome_pathways(spec.TARGET["uniprot"])
    variants = C.clinvar_variants(spec.GENE)
    structure = C.chembl_structure(getattr(spec, "CHEMBL_STRUCTURE", ""))
    session = record_session(spec.QUESTION, graph, ledger, hyp, review)

    retractions = [
        {"node": n.id, "text": n.text, "source": n.source,
         "retraction": R.retraction_status(n.source) if n.source.startswith("10.")
         else {"is_retracted": n.retracted}}
        for n in graph.nodes.values() if n.retracted]

    tabs = {
        "overview": _tier1({
            "disease": spec.DISEASE, "question": spec.QUESTION,
            "nodes": len(graph.nodes), "edges": len(graph.edges),
            "graph_hash": ledger.graph_hash,
            "sources": ledger.sources}, "projection of the EvidenceGraph"),
        "proteins": _tier1(target, "uniprot_protein"),
        "pathways": _tier1(pathways, "Reactome UniProt->pathways (now wired)"),
        "mutations": _tier1(
            {**variants, "genome_track_svg": genome_track_svg(
                variants.get("variants", []), spec.GENE)},
            "ClinVar via NCBI eutils — GRCh38 coordinates on a genome track"),
        "chemistry": _tier1(structure, "ChEMBL 2D structure of the standard-of-care "
                            "small molecule (real SMILES + rendered structure)")
        if structure.get("resolved") else _tier2(
            "no small-molecule structure resolved for this axis"),
        "notebook": _tier1(
            {"steps": [{"index": s.index, "stage": s.stage, "summary": s.summary,
                        "detail": s.detail} for s in session.steps]},
            "session replay (replay.py) — the Ledger's ordered stages ARE the "
            "notebook entries; no free-text tool"),
        "known_drugs": _tier1(drugs, "ChEMBL target->mechanism (now wired); a "
                              "zero result means an undrugged target, not empty"),
        "clinical_trials": _tier1(trials, "ClinicalTrials.gov v2 (now wired)"),
        "retractions": _tier1(retractions, "retraction_status over graph nodes"),
        "contradictions": _tier1(mine_contradictions(graph),
                                 "deterministic pass over EdgeType.CONTRADICTS"),
        "current_hypotheses": _tier1([{
            "statement": hyp.statement,
            "confidence": {"point": hyp.confidence.point,
                           "low": hyp.confidence.low, "high": hyp.confidence.high},
            "reviewer_verdict": review.verdict.value,
            "adjusted_confidence": review.adjusted_confidence.point,
            "grounding": hyp.mechanism_path}], "Hypothesis objects"),
        "future_experiments": _tier1(future_experiments_tree(hyp, graph),
                                     "reasoning_panel.future_experiments_tree"),
        "gaps": _tier1(detect_gaps(hyp, review, graph),
                       "gap-detection stage (readiness missing-evidence + structural)"),
        "readiness": _tier1(research_readiness(hyp, review, graph),
                            "honest readiness — never a fabricated percentage"),
        "knowledge_graph": _tier1(graph_to_dict(graph), "the EvidenceGraph itself"),
        # --- Tier 2: honest scaffolds, no fabricated data ------------------
        "genes": _tier2(f"No dedicated gene expression/variant-burden connector "
                        f"wired. Gene symbol from UniProt: {target.get('gene')}."),
        "datasets": _tier2("GEO / SRA declared in CATALOGUE, not wired — no "
                           "expression-dataset connector this session."),
    }
    return ({"domain": domain, "disease": spec.DISEASE,
             "question": spec.QUESTION, "graph_hash": ledger.graph_hash,
             "tabs": tabs}, graph, ledger, hyp, review)
