"""
keystone.ingest.references
==========================
Turn a scientist's OWN reference list into a real Keystone evidence graph — the
change that makes Keystone a tool they run without the builder in the room. A
pasted ``.bib`` / ``.ris`` / free-text list of DOIs becomes ``PAPER`` nodes whose
retraction status is resolved against Crossref/Retraction Watch, wired with the
intra-set contamination edges that make doubt propagate.

Determinism boundary is preserved (rule 7): every node ties to a real DOI or is
marked ``unresolved`` — a DOI that will not resolve is NEVER given a fabricated
title or a clean bill of health. Retraction status is read from a connector, not
guessed. Offline (``KEYSTONE_OFFLINE=1``) the pinned Crossref fixtures resolve; the
OpenAlex contamination-edge enrichment is best-effort and skipped on a miss.
"""
from __future__ import annotations

import re

from keystone.core import (EvidenceGraph, Node, Edge, Interval, NodeType,
                           EdgeType, TemporalRelation)
from keystone.connectors import registry as R
from keystone.deterministic.propagation import propagate_doubt

# A DOI: the 10.<registrant>/<suffix> form. Suffix runs to the first whitespace or
# a common trailing delimiter; we trim trailing punctuation afterwards.
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>&]+", re.IGNORECASE)
_TRAILING = ".,;)>]}\"'"
_MAX_REFS = 60          # be polite to shared public APIs; honest cap, shown to user
_CLEAN_PRIOR = 0.08     # small residual prior for a resolved, non-retracted paper


def parse_dois(text: str) -> list[str]:
    """Extract DOIs from pasted text — works for a raw list, a BibTeX ``.bib``, or
    an EndNote/Zotero ``.ris`` export (all embed the DOI literally). Deduplicated,
    order-preserving, case-normalized. Never invents a DOI."""
    seen, out = set(), []
    for m in _DOI_RE.findall(text or ""):
        doi = m.strip().rstrip(_TRAILING).lower()
        # BibTeX often wraps the DOI in {...}; strip a dangling brace pair.
        doi = doi.rstrip("}").rstrip(_TRAILING)
        if doi and doi not in seen:
            seen.add(doi)
            out.append(doi)
    return out


def _band(point: float, width: float = 0.05) -> Interval:
    return Interval(round(point, 4), round(max(0.0, point - width), 4),
                    round(min(1.0, point + width), 4)).clamp()


def _paper_node(node_id: str, doi: str, meta: dict) -> Node:
    """A resolved reference: retracted -> fully doubted; else a small prior. The
    doubt is a floor propagation can only raise (a paper that cites a retraction
    inherits doubt on top of this)."""
    retracted = bool(meta.get("is_retracted"))
    doubt = Interval(1.0, 1.0, 1.0) if retracted else _band(_CLEAN_PRIOR)
    title = meta.get("title") or doi
    return Node(
        id=node_id, node_type=NodeType.PAPER, source=doi, text=title,
        doubt=doubt, date=(f"{meta['year']}-01-01" if meta.get("year") else ""),
        retracted=retracted,
        meta={"title": title, "year": meta.get("year"),
              "container": meta.get("container"),
              "retraction_date": meta.get("retraction_date"),
              "retraction_via": meta.get("retraction_via"),
              "retraction_record": meta.get("retraction_record"),
              # every post-publication change (corrections, expressions of
              # concern, errata, …), not just the retraction — answers
              # "which papers changed after publication?"
              "post_pub_updates": meta.get("updates") or [],
              "resolved": True})


def _unresolved_node(node_id: str, doi: str) -> Node:
    """A DOI that would not resolve — shown honestly, never silently dropped or
    passed as clean. Doubt is a wide 'cannot judge' band."""
    return Node(id=node_id, node_type=NodeType.UNRESOLVED, source="unresolved",
                text=f"{doi} — could not resolve against Crossref",
                doubt=Interval(0.5, 0.3, 0.7),
                meta={"doi": doi, "resolved": False})


def _add_contamination_edges(graph: EvidenceGraph) -> None:
    """Best-effort (live-only): wire a CITES edge from every imported paper that
    *references* a retracted paper in the set, so doubt propagates and the blast
    radius is visible. Reads each paper's real OpenAlex reference list and links it
    to the retracted nodes' OpenAlex ids — never fabricates a citation; on any miss
    (offline / unresolved) the edge is simply not drawn."""
    # Fast path: with no retracted node in the set, no contamination edge is
    # possible — skip the per-node OpenAlex reference-list lookups entirely
    # (N network round-trips saved on a clean reference set). Behaviour is
    # identical: an all-clean set would draw no edges either way.
    if not any(n.retracted for n in graph.nodes.values()):
        return
    # resolve each resolved node's OpenAlex id + reference list
    oa: dict[str, dict] = {}
    for nid, node in graph.nodes.items():
        if node.source == "unresolved":
            continue
        try:
            rec = R.openalex_references(f"https://doi.org/{node.source}")
            if rec.get("resolved"):
                oa[nid] = rec
        except Exception:
            continue
    retracted_oa = {oa[nid]["id"]: nid for nid, n in graph.nodes.items()
                    if n.retracted and nid in oa}
    if not retracted_oa:
        return
    for nid, node in graph.nodes.items():
        if node.retracted or nid not in oa:
            continue
        for ref_id in oa[nid]["referenced_works"]:
            tgt = retracted_oa.get(ref_id)
            if not tgt:
                continue
            rdate = graph.nodes[tgt].meta.get("retraction_date") or ""
            temporal = TemporalRelation.NA
            if node.date and rdate:
                temporal = (TemporalRelation.POST_RETRACTION if node.date > rdate
                            else TemporalRelation.PRE_RETRACTION)
            graph.add_edge(Edge(
                src=nid, dst=tgt, edge_type=EdgeType.CITES,
                load_bearing=_band(0.6, 0.1), temporal=temporal,
                context=f"{nid} references the retracted work {graph.nodes[tgt].source}",
                rationale="intra-set contamination (OpenAlex reference list)"))


def build_graph_from_dois(question: str, dois: list[str],
                          limit: int = _MAX_REFS) -> EvidenceGraph:
    """Build a real evidence graph from a scientist's reference DOIs. Resolves
    retraction status per DOI (Crossref/RW), wires intra-set contamination edges
    (live best-effort), then propagates doubt. Returns an ``EvidenceGraph`` — the
    same type the whole engine consumes, so every downstream surface works."""
    graph = EvidenceGraph()
    for i, doi in enumerate(dois[:limit]):
        node_id = f"N_ref_{i}"
        rec = R.crossref_work(doi)
        node = _paper_node(node_id, doi, rec) if rec.get("resolved") \
            else _unresolved_node(node_id, doi)
        graph.add_node(node)
    _add_contamination_edges(graph)
    propagate_doubt(graph)
    return graph
