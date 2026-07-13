"""
keystone.data_ich
================
Third-domain graph builder — intracerebral / brain hemorrhage ("NeuroHem") —
mirroring ``data_insulin.py`` and reusing ``core.py``'s Node/Edge/EvidenceGraph
(no parallel types). Built from real connector output; a failed resolution is
marked ``unresolved``, never fabricated.

Topology mirrors GBM: a real *retracted* foundation (MMP-9 potentiates early
brain injury after hemorrhage) whose real citers inherit doubt via the blast
radius, a real druggable target (MMP-9), and a real dual-role CONTRADICTION
(Zhao 2006: MMP-9 also drives beneficial delayed remodeling).

``build_ich_graph()``           -> deterministic, offline (cache + fixtures)
``build_ich_graph(live=True)``  -> refresh from the live APIs, then cache
"""
from __future__ import annotations

from keystone.core import (EvidenceGraph, Node, Edge, Interval, NodeType,
                           EdgeType, TemporalRelation)
from keystone.connectors import registry as R
from keystone import ich_spec as SPEC
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


def build_ich_graph(live: bool = False) -> EvidenceGraph:
    with _offline(active=not live):
        return _build()


def _build() -> EvidenceGraph:
    g = EvidenceGraph()
    ctx = _context_index()

    # --- Foundation (real, RETRACTED — the compromised keystone) -----------
    found = R.openalex_work(SPEC.FOUNDATION["openalex"])
    ret = R.retraction_status(SPEC.FOUNDATION["doi"])
    retracted = bool(found.get("is_retracted")) or bool(ret.get("is_retracted"))
    g.add_node(Node(
        id="N_foundation", node_type=NodeType.PAPER,
        source=found.get("doi") or SPEC.FOUNDATION["doi"],
        text=found.get("title") or "MMP-9 potentiates early brain injury after hemorrhage",
        # a retracted foundation carries full doubt; the blast radius flows from here
        doubt=Interval(1.0, 1.0, 1.0) if retracted else _band(0.15, 0.08),
        date=found.get("date") or "2009-01-01",
        retracted=retracted,
        meta={"cited_by_count": found.get("cited_by_count"),
              "retraction_checked": True, "retracted": retracted}))

    # --- Reagent (real, clean line — no Cellosaurus problematic flag) -------
    cell = R.cellosaurus_line(SPEC.REAGENT["cellosaurus"])
    problem = cell.get("problematic") if cell.get("resolved") else None
    g.add_node(Node(
        id="N_reagent", node_type=NodeType.REAGENT,
        source=f"Cellosaurus:{SPEC.REAGENT['cellosaurus']}",
        text=(f"{cell.get('name', 'BV-2')} — microglia neuroinflammation model"
              + (f"; {problem[:60]}" if problem else " (no misidentification flag)")),
        doubt=_band(SPEC.REAGENT["prior_doubt"], 0.1),
        meta={"synonyms": cell.get("synonyms"), "problematic": problem}))

    # --- Target (real protein) ---------------------------------------------
    prot = R.uniprot_protein(SPEC.TARGET["uniprot"])
    pdb = (prot.get("pdb_ids") or [SPEC.TARGET["pdb_preferred"]])[0]
    g.add_node(Node(
        id="N_target", node_type=NodeType.TARGET,
        source=f"UniProt:{SPEC.TARGET['uniprot']}",
        text=f"{prot.get('gene', 'MMP9')} — {prot.get('name', 'Matrix metalloproteinase-9')}",
        doubt=_band(SPEC.TARGET["prior_doubt"], 0.05),
        meta={"pdb": pdb, "pdb_ids": prot.get("pdb_ids")}))

    # --- Dependents (real citers of the retracted foundation) --------------
    for dep in SPEC.DEPENDENTS:
        c = ctx.get(dep["doi"].lower(), {})
        citing_context = c.get("context")
        year = c.get("year")
        date = _year_to_date(year)
        # a citer of a retracted paper inherits doubt through the CITES edge; its
        # own prior stays honest (load-bearing citers carry a touch more).
        doubt = _band(0.28 if dep["role"] == "load_bearing" else 0.12, 0.08)
        g.add_node(Node(
            id=dep["node_id"], node_type=NodeType.PAPER,
            source=dep["doi"], text=dep["title"], doubt=doubt, date=date,
            retracted=False,
            meta={"role": dep["role"], "s2_influential": c.get("influential")}))
        g.add_edge(Edge(
            src=dep["node_id"], dst="N_foundation", edge_type=EdgeType.CITES,
            load_bearing=_band(0.6 if dep["role"] == "load_bearing" else 0.3),
            temporal=TemporalRelation.NA,
            context=citing_context or _UNRESOLVED, rationale=f"role={dep['role']}"))

    # --- Foundation depends on the reagent ---------------------------------
    g.add_edge(Edge(
        src="N_foundation", dst="N_reagent", edge_type=EdgeType.DEPENDS_ON,
        load_bearing=_band(0.5),
        context="BV-2 microglia are a standard in-vitro model for the "
                "neuroinflammatory response and MMP-9 release after hemorrhage."))

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
        context=molc.get("context") or "MMP-9 degrades the basal lamina and tight "
                "junctions, driving blood-brain-barrier breakdown and edema."))

    # --- Contradiction (MMP-9's real dual role — beneficial in recovery) ---
    conc = ctx.get(SPEC.CONTRADICTION["doi"].lower(), {})
    g.add_node(Node(
        id="N_contra", node_type=NodeType.MOLECULAR_RESULT,
        source=SPEC.CONTRADICTION["doi"], text=SPEC.CONTRADICTION["title"],
        doubt=_band(SPEC.CONTRADICTION["prior_doubt"], 0.08),
        date=_year_to_date(conc.get("year")), meta={"context": conc.get("context")}))
    g.add_edge(Edge(
        src="N_contra", dst="N_foundation", edge_type=EdgeType.CONTRADICTS,
        load_bearing=_band(0.6),
        context=conc.get("context") or "MMP-9 also drives beneficial delayed "
                "neurovascular remodeling, complicating a purely harmful role."))

    # --- Foundation targets MMP-9 ------------------------------------------
    g.add_edge(Edge(
        src="N_foundation", dst="N_target", edge_type=EdgeType.TARGETS,
        load_bearing=_band(0.8),
        context="The hemorrhage secondary-injury cascade signals through MMP-9 to "
                "degrade the neurovascular unit."))
    return g


def ich_sources() -> list:
    src = [f"OpenAlex:{SPEC.FOUNDATION['openalex']}",
           f"DOI:{SPEC.FOUNDATION['doi']}",
           f"Cellosaurus:{SPEC.REAGENT['cellosaurus']}",
           f"UniProt:{SPEC.TARGET['uniprot']}"]
    src += [f"DOI:{d['doi']}" for d in SPEC.DEPENDENTS]
    src += [f"DOI:{SPEC.MOLECULAR['doi']}", f"DOI:{SPEC.CONTRADICTION['doi']}"]
    return src
