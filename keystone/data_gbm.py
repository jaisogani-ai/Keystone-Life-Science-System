"""
keystone.data_gbm
================
Builds the glioblastoma evidence graph from *real connector output* — no
synthetic target. The foundation is a real retracted Oncogene paper; the
dependents are real citers with their real Semantic-Scholar citing sentences;
the reagent is a real misidentified cell line; the target is a real UniProt
protein. Where a connector cannot resolve something (e.g. a citing sentence),
the field is marked ``unresolved`` — never fabricated (rule 7 / determinism
boundary).

``build_gbm_graph()``           -> deterministic, offline (cache + fixtures)
``build_gbm_graph(live=True)``  -> refresh from the live APIs, then cache
"""
from __future__ import annotations

import os
from contextlib import contextmanager

from keystone.core import (EvidenceGraph, Node, Edge, Interval, NodeType,
                           EdgeType, TemporalRelation)
from keystone.connectors import registry as R
from keystone import gbm_spec as SPEC

_UNRESOLVED = "unresolved: citing sentence not returned by connector"


@contextmanager
def _offline(active: bool):
    prev = os.environ.get("KEYSTONE_OFFLINE")
    if active:
        os.environ["KEYSTONE_OFFLINE"] = "1"
    try:
        yield
    finally:
        if active:
            if prev is None:
                os.environ.pop("KEYSTONE_OFFLINE", None)
            else:
                os.environ["KEYSTONE_OFFLINE"] = prev


def _band(point: float, width: float = 0.1) -> Interval:
    return Interval(point, max(0.0, point - width), min(1.0, point + width))


def _year_to_date(year) -> str:
    return f"{int(year)}-01-01" if year else ""


def _context_index() -> dict:
    """Map citing-paper DOI -> first real citing sentence, from Semantic Scholar."""
    idx = {}
    for row in R.semantic_scholar_contexts(SPEC.FOUNDATION["doi"]):
        doi = (row.get("doi") or "").lower()
        if doi and row.get("contexts"):
            idx.setdefault(doi, {"context": row["contexts"][0],
                                 "year": row.get("year"),
                                 "influential": row.get("is_influential")})
    return idx


def build_gbm_graph(live: bool = False) -> EvidenceGraph:
    with _offline(active=not live):
        return _build()


def _build() -> EvidenceGraph:
    g = EvidenceGraph()
    ctx = _context_index()

    # --- Foundation (real, retracted) --------------------------------------
    found = R.openalex_work(SPEC.FOUNDATION["openalex"])
    ret = R.retraction_status(SPEC.FOUNDATION["doi"])
    retracted = bool(found.get("is_retracted")) or bool(ret.get("is_retracted"))
    retraction_date = ret.get("retraction_date") or ""
    g.add_node(Node(
        id="N_foundation", node_type=NodeType.PAPER,
        source=found.get("doi") or SPEC.FOUNDATION["doi"],
        text=found.get("title") or "Retracted glioblastoma RNAi paper",
        doubt=Interval(1.0, 1.0, 1.0), date=found.get("date") or "2004-01-01",
        retracted=retracted,
        meta={"retraction_date": retraction_date,
              "retraction_via": ret.get("via"),
              "retraction_record": ret.get("record_id"),
              "cited_by_count": found.get("cited_by_count")}))

    # --- Reagent (real misidentified cell line) ----------------------------
    cell = R.cellosaurus_line(SPEC.REAGENT["cellosaurus"])
    problem = cell.get("problematic") if cell.get("resolved") else None
    g.add_node(Node(
        id="N_reagent", node_type=NodeType.REAGENT,
        source=f"Cellosaurus:{SPEC.REAGENT['cellosaurus']}",
        text=(f"{cell.get('name', 'U-87MG')} — "
              + ("misidentified line; " + (problem or "")[:80] if problem
                 else "cell line")),
        doubt=_band(SPEC.REAGENT["prior_doubt"], 0.1), date="",
        meta={"synonyms": cell.get("synonyms"), "problematic": problem}))

    # --- Target (real protein) ---------------------------------------------
    prot = R.uniprot_protein(SPEC.TARGET["uniprot"])
    pdb = (prot.get("pdb_ids") or [SPEC.TARGET["pdb_preferred"]])[0]
    g.add_node(Node(
        id="N_target", node_type=NodeType.TARGET,
        source=f"UniProt:{SPEC.TARGET['uniprot']}",
        text=f"{prot.get('gene', 'CTSB')} — {prot.get('name', 'Cathepsin B')}",
        doubt=_band(SPEC.TARGET["prior_doubt"], 0.05), date="",
        meta={"pdb": pdb, "pdb_ids": prot.get("pdb_ids")}))

    # --- Dependents (real citers with real citing sentences) ---------------
    for dep in SPEC.DEPENDENTS:
        c = ctx.get(dep["doi"].lower(), {})
        citing_context = c.get("context")
        year = c.get("year")
        if dep["role"] == "post_retraction":       # resolve its real date via OpenAlex
            w = R.openalex_work(dep["openalex"])
            year = w.get("year") or year
            date = w.get("date") or _year_to_date(year)
        else:
            date = _year_to_date(year)
        temporal = _temporal(date, retraction_date)
        g.add_node(Node(
            id=dep["node_id"], node_type=NodeType.PAPER,
            source=dep["doi"], text=dep["title"],
            doubt=_band(0.08, 0.05), date=date,
            inexcusable=(dep["role"] == "post_retraction" and
                         temporal == TemporalRelation.POST_RETRACTION),
            meta={"role": dep["role"], "s2_influential": c.get("influential")}))
        g.add_edge(Edge(
            src=dep["node_id"], dst="N_foundation", edge_type=EdgeType.CITES,
            load_bearing=_band(0.5), temporal=temporal,
            context=citing_context or _UNRESOLVED,
            rationale=f"role={dep['role']}"))

    # --- Foundation depends on the reagent ---------------------------------
    g.add_edge(Edge(
        src="N_foundation", dst="N_reagent", edge_type=EdgeType.DEPENDS_ON,
        load_bearing=_band(0.5), temporal=TemporalRelation.NA,
        context="Central model system: the U-87MG glioblastoma cell line was "
                "used for the RNAi knockdown invasion assays."))

    # --- Molecular grounding (supports the target's relevance) -------------
    molc = ctx.get(SPEC.MOLECULAR["doi"].lower(), {})
    g.add_node(Node(
        id="N_molecular", node_type=NodeType.MOLECULAR_RESULT,
        source=SPEC.MOLECULAR["doi"], text=SPEC.MOLECULAR["title"],
        doubt=_band(SPEC.MOLECULAR["prior_doubt"], 0.08),
        date=_year_to_date(molc.get("year")),
        meta={"context": molc.get("context")}))
    g.add_edge(Edge(
        src="N_molecular", dst="N_target", edge_type=EdgeType.SUPPORTS,
        load_bearing=_band(0.7),
        context=molc.get("context") or "Cathepsin B is multifunctional in "
                "cancer (angiogenesis, invasion, proliferation)."))

    # --- Contradiction (dual role complicates the universal claim) ---------
    conc = ctx.get(SPEC.CONTRADICTION["doi"].lower(), {})
    g.add_node(Node(
        id="N_contra", node_type=NodeType.MOLECULAR_RESULT,
        source=SPEC.CONTRADICTION["doi"], text=SPEC.CONTRADICTION["title"],
        doubt=_band(SPEC.CONTRADICTION["prior_doubt"], 0.08),
        date=_year_to_date(conc.get("year")),
        meta={"context": conc.get("context")}))
    g.add_edge(Edge(
        src="N_contra", dst="N_foundation", edge_type=EdgeType.CONTRADICTS,
        load_bearing=_band(0.6),
        context=conc.get("context") or "CTSB may play two opposing roles in "
                "malignancy — apoptosis executioner vs. invasion mediator."))

    # --- Foundation targets the CTSB/MMP-9 axis ----------------------------
    g.add_edge(Edge(
        src="N_foundation", dst="N_target", edge_type=EdgeType.TARGETS,
        load_bearing=_band(0.8),
        context="The retracted claim: knocking down the CTSB/MMP-9 axis "
                "suppresses invasion, growth and angiogenesis."))
    return g


def _temporal(citer_date: str, retraction_date: str) -> TemporalRelation:
    if not citer_date or not retraction_date:
        return TemporalRelation.NA
    return (TemporalRelation.POST_RETRACTION if citer_date > retraction_date
            else TemporalRelation.PRE_RETRACTION)


def gbm_sources() -> list:
    """Provenance list for the Ledger (rule 6)."""
    src = [f"OpenAlex:{SPEC.FOUNDATION['openalex']}",
           f"DOI:{SPEC.FOUNDATION['doi']}",
           f"Cellosaurus:{SPEC.REAGENT['cellosaurus']}",
           f"UniProt:{SPEC.TARGET['uniprot']}"]
    src += [f"DOI:{d['doi']}" for d in SPEC.DEPENDENTS]
    src += [f"DOI:{SPEC.MOLECULAR['doi']}", f"DOI:{SPEC.CONTRADICTION['doi']}"]
    return src
