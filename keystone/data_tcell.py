"""
keystone.data_tcell
===================
Builds the CD4+ T-cell / type-2 (Th2) target-prioritization evidence graph from
pinned REAL identifiers (`tcell_spec`). Every ``source`` is a real, resolvable id
(DOI / UniProt / bioRxiv URL); every ``text`` is the real title/role. Nothing is
invented. Offline-safe: the pinned values ARE the real data, so the graph is
identical offline and live (a reviewer can resolve every id themselves).

``build_tcell_graph()`` -> deterministic evidence graph over the Th2 regulator case.
"""
from __future__ import annotations

from keystone.core import (EvidenceGraph, Node, Edge, Interval, NodeType,
                           EdgeType, TemporalRelation)
from keystone import tcell_spec as SPEC


def _band(point: float, width: float = 0.1) -> Interval:
    return Interval(round(point, 4), round(max(0.0, point - width), 4),
                    round(min(1.0, point + width), 4))


def build_tcell_graph(live: bool = False) -> EvidenceGraph:  # noqa: ARG001
    g = EvidenceGraph()

    # --- Grounding perturbation screen (real, peer-reviewed) ---------------
    g.add_node(Node(
        id=SPEC.FOUNDATION["node_id"], node_type=NodeType.DATASET,
        source=SPEC.FOUNDATION["doi"], text=SPEC.FOUNDATION["title"],
        doubt=_band(0.14, 0.08), date="2018-11-01",
        meta={"peer_reviewed": True, "assay": "genome-wide CRISPR (SLICE) in primary human T cells"}))

    # --- Model system (honest: primary cells, not an immortalized line) ----
    g.add_node(Node(
        id=SPEC.REAGENT["node_id"], node_type=NodeType.REAGENT,
        source="UniProt:P01730",   # CD4 — anchors the activated-CD4 model system
        text=SPEC.REAGENT["text"], doubt=_band(SPEC.REAGENT["prior_doubt"], 0.08),
        date="", meta={"model": "primary human CD4+ T cells (activated)"}))

    # --- Lead candidate regulator / target (GATA3) -------------------------
    g.add_node(Node(
        id=SPEC.TARGET["node_id"], node_type=NodeType.TARGET,
        source=f"UniProt:{SPEC.TARGET['uniprot']}",
        text=f"{SPEC.TARGET['gene']} — master Th2 transcription factor",
        doubt=_band(SPEC.TARGET["prior_doubt"], 0.06),
        meta={"gene": SPEC.TARGET["gene"], "pdb": SPEC.TARGET["pdb_preferred"]}))
    g.add_edge(Edge(
        src=SPEC.TARGET["node_id"], dst=SPEC.FOUNDATION["node_id"],
        edge_type=EdgeType.SUPPORTS, load_bearing=_band(0.8),
        context="GATA3 is recovered as a top hit in the CRISPR screen's own Th2 readout."))

    # --- The Th2 transcriptional program (classic grounding) ---------------
    g.add_node(Node(
        id=SPEC.MOLECULAR["node_id"], node_type=NodeType.MOLECULAR_RESULT,
        source=SPEC.MOLECULAR["doi"], text=SPEC.MOLECULAR["title"],
        doubt=_band(SPEC.MOLECULAR["prior_doubt"], 0.06), date="1997-05-01"))
    g.add_edge(Edge(
        src=SPEC.TARGET["node_id"], dst=SPEC.MOLECULAR["node_id"],
        edge_type=EdgeType.TARGETS, load_bearing=_band(0.85),
        context="GATA3 is necessary and sufficient for the IL-4/IL-5/IL-13 type-2 cytokine program."))

    # --- Additional real perturbation-defined regulators (candidate targets) --
    for reg in SPEC.REGULATORS:
        # FBXO32 is only nominated by the not-yet-peer-reviewed preprint → higher doubt.
        doubt = 0.45 if reg["role"] == "novel" else 0.20
        g.add_node(Node(
            id=reg["node_id"], node_type=NodeType.TARGET,
            source=f"UniProt:{reg['uniprot']}", text=reg["title"],
            doubt=_band(doubt, 0.08),
            meta={"gene": reg["gene"], "role": reg["role"]}))
        g.add_edge(Edge(
            src=reg["node_id"], dst=SPEC.MOLECULAR["node_id"],
            edge_type=EdgeType.TARGETS, load_bearing=_band(0.6 if reg["role"] != "novel" else 0.4),
            context=f"{reg['gene']} perturbation shifts the type-2 program in the screen."))

    # --- The 2025 CD4+ Perturb-seq PREPRINT (real integrity liability) ------
    # Not yet peer-reviewed → high inherited doubt; it is the sole support for the
    # novel FBXO32 nomination, so excluding it in the counterfactual weakens FBXO32.
    g.add_node(Node(
        id=SPEC.PREPRINT["node_id"], node_type=NodeType.PAPER,
        source=SPEC.PREPRINT["url"], text=SPEC.PREPRINT["title"],
        doubt=Interval(0.7, 0.6, 0.8), date="2025-12-23",
        meta={"preprint": True, "peer_reviewed": False,
              "integrity_note": "preprint — not peer-reviewed; treat as provisional"}))
    g.add_edge(Edge(
        src="N_dep_C", dst=SPEC.PREPRINT["node_id"], edge_type=EdgeType.DEPENDS_ON,
        load_bearing=_band(0.75),
        context="The novel FBXO32 nomination rests on the not-yet-peer-reviewed Perturb-seq preprint."))

    # --- The complicating / contradicting evidence (real safety tension) ---
    g.add_node(Node(
        id=SPEC.CONTRADICTION["node_id"], node_type=NodeType.MOLECULAR_RESULT,
        source=SPEC.CONTRADICTION["doi"], text=SPEC.CONTRADICTION["title"],
        doubt=_band(SPEC.CONTRADICTION["prior_doubt"], 0.08), date="2019-02-01"))
    g.add_edge(Edge(
        src=SPEC.CONTRADICTION["node_id"], dst=SPEC.TARGET["node_id"],
        edge_type=EdgeType.CONTRADICTS, load_bearing=_band(0.6),
        context="Direct GATA3 loss couples activation and differentiation and impairs "
                "T-cell fitness — a selectivity/safety tension for degrading it."))

    # --- Foundation depends on the model system ---------------------------
    g.add_edge(Edge(
        src=SPEC.FOUNDATION["node_id"], dst=SPEC.REAGENT["node_id"],
        edge_type=EdgeType.DEPENDS_ON, load_bearing=_band(0.5),
        context="Screens performed in activated primary human CD4+ T cells."))
    return g


def tcell_sources() -> list:
    """Provenance list for the Ledger (rule 6) — every id real and resolvable."""
    src = [f"DOI:{SPEC.FOUNDATION['doi']}", f"UniProt:{SPEC.TARGET['uniprot']}",
           f"DOI:{SPEC.MOLECULAR['doi']}", f"DOI:{SPEC.CONTRADICTION['doi']}",
           SPEC.PREPRINT["url"]]
    src += [f"UniProt:{r['uniprot']}" for r in SPEC.REGULATORS]
    return src
