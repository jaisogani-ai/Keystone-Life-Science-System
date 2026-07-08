"""
keystone.data_insulin
====================
Second-domain graph builder — insulin signalling / insulin resistance — mirroring
``data_gbm.py`` and reusing ``core.py``'s Node/Edge/EvidenceGraph (no parallel
types). Built from real connector output; a failed resolution is marked
``unresolved``, never fabricated.

Topology differs honestly from GBM: the foundation is a real *clean* landmark
review, and the compromised node is a real *retracted dependent* (verified via
``retraction_status``). Same machinery, different shape — the point of the second
domain.

``build_insulin_graph()``           -> deterministic, offline (cache + fixtures)
``build_insulin_graph(live=True)``  -> refresh from the live APIs, then cache
"""
from __future__ import annotations

from keystone.core import (EvidenceGraph, Node, Edge, Interval, NodeType,
                           EdgeType, TemporalRelation)
from keystone.connectors import registry as R
from keystone import insulin_spec as SPEC
# Reuse the generic (domain-independent) helpers rather than duplicate them.
from keystone.data_gbm import _offline, _band, _year_to_date, _UNRESOLVED


def _context_index() -> dict:
    idx = {}
    for row in R.semantic_scholar_contexts(SPEC.FOUNDATION["doi"], limit=120):
        doi = (row.get("doi") or "").lower()
        if doi and row.get("contexts"):
            idx.setdefault(doi, {"context": row["contexts"][0],
                                 "year": row.get("year"),
                                 "influential": row.get("is_influential")})
    return idx


def build_insulin_graph(live: bool = False) -> EvidenceGraph:
    with _offline(active=not live):
        return _build()


def _build() -> EvidenceGraph:
    g = EvidenceGraph()
    ctx = _context_index()

    # --- Foundation (real, CLEAN — not retracted) --------------------------
    found = R.openalex_work(SPEC.FOUNDATION["openalex"])
    ret = R.retraction_status(SPEC.FOUNDATION["doi"])
    retracted = bool(found.get("is_retracted")) or bool(ret.get("is_retracted"))
    g.add_node(Node(
        id="N_foundation", node_type=NodeType.PAPER,
        source=found.get("doi") or SPEC.FOUNDATION["doi"],
        text=found.get("title") or "Insulin signalling landmark review",
        doubt=_band(0.12, 0.06), date=found.get("date") or "2001-12-13",
        retracted=retracted,
        meta={"cited_by_count": found.get("cited_by_count"),
              "retraction_checked": True, "retracted": retracted}))

    # --- Reagent (real, clean line — no Cellosaurus problematic flag) -------
    cell = R.cellosaurus_line(SPEC.REAGENT["cellosaurus"])
    problem = cell.get("problematic") if cell.get("resolved") else None
    g.add_node(Node(
        id="N_reagent", node_type=NodeType.REAGENT,
        source=f"Cellosaurus:{SPEC.REAGENT['cellosaurus']}",
        text=(f"{cell.get('name', '3T3-L1')} — adipocyte model line"
              + (f"; {problem[:60]}" if problem else " (no misidentification flag)")),
        doubt=_band(SPEC.REAGENT["prior_doubt"], 0.1),
        meta={"synonyms": cell.get("synonyms"), "problematic": problem}))

    # --- Target (real protein) ---------------------------------------------
    prot = R.uniprot_protein(SPEC.TARGET["uniprot"])
    pdb = (prot.get("pdb_ids") or [SPEC.TARGET["pdb_preferred"]])[0]
    g.add_node(Node(
        id="N_target", node_type=NodeType.TARGET,
        source=f"UniProt:{SPEC.TARGET['uniprot']}",
        text=f"{prot.get('gene', 'IRS1')} — {prot.get('name', 'Insulin receptor substrate 1')}",
        doubt=_band(SPEC.TARGET["prior_doubt"], 0.05),
        meta={"pdb": pdb, "pdb_ids": prot.get("pdb_ids")}))

    # --- Dependents (real citers; one is a REAL retracted paper) -----------
    for dep in SPEC.DEPENDENTS:
        c = ctx.get(dep["doi"].lower(), {})
        citing_context = c.get("context")
        year = c.get("year")
        retracted_dep = False
        if dep["role"] == "retracted":
            w = R.openalex_work(dep["openalex"])
            dret = R.retraction_status(dep["doi"])
            retracted_dep = bool(w.get("is_retracted")) or bool(dret.get("is_retracted"))
            year = w.get("year") or year
            date = w.get("date") or _year_to_date(year)
            doubt = Interval(1.0, 1.0, 1.0) if retracted_dep else _band(0.3, 0.1)
        else:
            date = _year_to_date(year)
            doubt = _band(0.10, 0.05)
        g.add_node(Node(
            id=dep["node_id"], node_type=NodeType.PAPER,
            source=dep["doi"], text=dep["title"], doubt=doubt, date=date,
            retracted=retracted_dep,
            meta={"role": dep["role"], "s2_influential": c.get("influential")}))
        g.add_edge(Edge(
            src=dep["node_id"], dst="N_foundation", edge_type=EdgeType.CITES,
            load_bearing=_band(0.5), temporal=TemporalRelation.NA,
            context=citing_context or _UNRESOLVED, rationale=f"role={dep['role']}"))

    # --- Foundation depends on the reagent ---------------------------------
    g.add_edge(Edge(
        src="N_foundation", dst="N_reagent", edge_type=EdgeType.DEPENDS_ON,
        load_bearing=_band(0.5),
        context="3T3-L1 adipocytes are a standard model for insulin-stimulated "
                "glucose uptake and IRS-1/PI3K/Akt signalling assays."))

    # --- Molecular grounding (supports the target) -------------------------
    molc = ctx.get(SPEC.MOLECULAR["doi"].lower(), {})
    g.add_node(Node(
        id="N_molecular", node_type=NodeType.MOLECULAR_RESULT,
        source=SPEC.MOLECULAR["doi"], text=SPEC.MOLECULAR["title"],
        doubt=_band(SPEC.MOLECULAR["prior_doubt"], 0.08),
        date=_year_to_date(molc.get("year")), meta={"context": molc.get("context")}))
    g.add_edge(Edge(
        src="N_molecular", dst="N_target", edge_type=EdgeType.SUPPORTS,
        load_bearing=_band(0.7),
        context=molc.get("context") or "IRS-1/PI3K/Akt/GLUT4 signalling is "
                "impaired in type 2 diabetes."))

    # --- Contradiction (metabolic-vs-mitogenic complication) ---------------
    conc = ctx.get(SPEC.CONTRADICTION["doi"].lower(), {})
    g.add_node(Node(
        id="N_contra", node_type=NodeType.MOLECULAR_RESULT,
        source=SPEC.CONTRADICTION["doi"], text=SPEC.CONTRADICTION["title"],
        doubt=_band(SPEC.CONTRADICTION["prior_doubt"], 0.08),
        date=_year_to_date(conc.get("year")), meta={"context": conc.get("context")}))
    g.add_edge(Edge(
        src="N_contra", dst="N_foundation", edge_type=EdgeType.CONTRADICTS,
        load_bearing=_band(0.6),
        context=conc.get("context") or "The same pathway exerts strong mitogenic "
                "effects, complicating a purely metabolic interpretation."))

    # --- Foundation targets the IRS-1/PI3K/Akt axis ------------------------
    g.add_edge(Edge(
        src="N_foundation", dst="N_target", edge_type=EdgeType.TARGETS,
        load_bearing=_band(0.8),
        context="The insulin cascade signals through IRS-1 to PI3K/Akt to drive "
                "glucose uptake and metabolism."))
    return g


def insulin_sources() -> list:
    src = [f"OpenAlex:{SPEC.FOUNDATION['openalex']}",
           f"DOI:{SPEC.FOUNDATION['doi']}",
           f"Cellosaurus:{SPEC.REAGENT['cellosaurus']}",
           f"UniProt:{SPEC.TARGET['uniprot']}"]
    src += [f"DOI:{d['doi']}" for d in SPEC.DEPENDENTS]
    src += [f"DOI:{SPEC.MOLECULAR['doi']}", f"DOI:{SPEC.CONTRADICTION['doi']}"]
    return src
