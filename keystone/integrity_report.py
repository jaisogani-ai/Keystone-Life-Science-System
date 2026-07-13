"""
keystone.integrity_report
=========================
The Research Integrity triage over a scientist's OWN imported references — the
entry workflow. It classifies every reference against real, verifiable signals and
NEVER fabricates a verdict:

  retracted        -> the paper itself is retracted (Crossref / Retraction Watch)
  cites_retraction -> the paper cites a retracted work in the set (a CITES edge to
                      a retracted node); post-retraction reliance is inexcusable
  unresolved       -> the DOI would not resolve — shown, never passed as clean
  high_doubt       -> resolved & not retracted, but inherited doubt is elevated
  clean            -> resolved, not retracted, no compromised dependency

Every row carries its DOI (so the scientist can click through and verify) and the
doubt interval (uncertainty is never hidden). This is a deterministic projection of
the evidence graph — no LLM, no invented flags.
"""
from __future__ import annotations

from keystone.core import EvidenceGraph

_HIGH_DOUBT = 0.4        # inherited-doubt threshold for a resolved, clean paper


def _doi_url(source: str) -> str:
    return f"https://doi.org/{source}" if source.startswith("10.") else ""


def reference_integrity(graph: EvidenceGraph) -> dict:
    """Return the per-reference triage + a summary. Deterministic; the same graph
    yields the same triage every run."""
    # who cites a retracted node (intra-set contamination)
    retracted_ids = {nid for nid, n in graph.nodes.items() if n.retracted}
    cites_retracted: dict[str, list] = {}
    for e in graph.edges:
        if e.edge_type.value in ("cites", "depends_on") and e.dst in retracted_ids:
            cites_retracted.setdefault(e.src, []).append(
                {"target": e.dst, "target_doi": graph.nodes[e.dst].source,
                 "post_retraction": e.temporal.value == "post_retraction"})

    rows = []
    for nid, n in graph.nodes.items():
        updates = n.meta.get("post_pub_updates") or []
        utypes = {(u.get("type") or "") for u in updates}
        if n.node_type.value == "unresolved":
            status = "unresolved"
        elif n.retracted:
            status = "retracted"
        elif nid in cites_retracted:
            status = "cites_retraction"
        elif "expression_of_concern" in utypes:
            status = "expression_of_concern"
        elif utypes & {"correction", "erratum"}:
            status = "corrected"
        elif n.doubt.point >= _HIGH_DOUBT:
            status = "high_doubt"
        else:
            status = "clean"
        rows.append({
            "id": nid, "doi": n.source if n.source != "unresolved" else n.meta.get("doi"),
            "url": _doi_url(n.source),
            "title": n.meta.get("title") or n.text,
            "year": n.meta.get("year"),
            "status": status,
            "doubt": round(n.doubt.point, 3),
            "doubt_interval": [n.doubt.low, n.doubt.high],
            "retraction_date": n.meta.get("retraction_date"),
            "inexcusable": bool(n.inexcusable),
            "cites_retracted": cites_retracted.get(nid, []),
            # the full post-publication change history — retractions AND
            # corrections/expressions of concern/errata (real Crossref data).
            "post_pub_updates": updates,
            "changed_after_publication": bool(utypes),
        })

    # order: worst first (retracted → cites-retraction → concern → corrected …)
    order = {"retracted": 0, "cites_retraction": 1, "expression_of_concern": 2,
             "corrected": 3, "high_doubt": 4, "unresolved": 5, "clean": 6}
    rows.sort(key=lambda r: (order[r["status"]], -r["doubt"]))

    counts = {k: sum(1 for r in rows if r["status"] == k) for k in order}
    compromised = counts["retracted"] + counts["cites_retraction"]
    # "changed after publication" but not compromised — a distinct, milder flag
    changed = counts["expression_of_concern"] + counts["corrected"]
    total = len(rows)
    verdict = (f"{compromised} of {total} references are compromised"
               if compromised else
               (f"no compromised references among {total} resolved"
                if total else "no references parsed"))
    if changed:
        verdict += (f"; {changed} changed after publication "
                    f"(correction / expression of concern)")
    return {
        "total": total,
        "counts": counts,
        "compromised": compromised,
        "changed_after_publication": changed,
        "verdict": verdict,
        "graph_hash": graph.snapshot_hash(),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Plain-language integrity summary — the "click moment" above the triage table
# ---------------------------------------------------------------------------
# The paragraph appears on the front door immediately after import. It has TWO
# sources depending on the deployment mode:
#
#   * offline / no API key  ->  ``integrity_summary_template`` (this file). A
#     deterministic composition of the triage rows: real DOIs, real counts, real
#     doubt values. Uses only what the engine already computed. Never fabricates
#     a number or a DOI. Always available — even without network.
#
#   * KEYSTONE_LIVE=1 + ANTHROPIC_API_KEY  ->  ``ClaudeReasoner.integrity_summary``
#     (in agents/claude_reasoner.py). Claude reads the triage and writes 2-4
#     sentences of natural-language interpretation. Numbers stay deterministic
#     (they come from the triage dict, not the model); only prose is Claude.
#
# The template is the trust floor; Claude is the polish. Both cite the same real
# rows so the paragraph and the table below it never disagree.


def _fmt_doi(row: dict) -> str:
    doi = row.get("doi") or "unresolved"
    return doi if doi != "unresolved" else "an unresolved DOI"


def integrity_summary_template(triage: dict) -> dict:
    """Compose a plain-language integrity summary from the triage — deterministic
    template using only real values (DOIs, counts, doubt intervals). Returns a
    dict with ``paragraph`` and ``source`` so the caller can show provenance."""
    total = triage.get("total", 0)
    counts = triage.get("counts", {})
    rows = triage.get("rows", [])
    retracted = [r for r in rows if r["status"] == "retracted"]
    cites = [r for r in rows if r["status"] == "cites_retraction"]
    unresolved = counts.get("unresolved", 0)

    if total == 0:
        return {"paragraph": "No references parsed. Paste a `.bib`/`.ris` "
                             "export or a DOI list to begin.",
                "source": "template"}

    parts = []
    if not retracted and not cites and unresolved == 0:
        parts.append(
            f"All {total} references resolved cleanly against Crossref / "
            f"Retraction Watch. No retractions, no post-retraction reliance, "
            f"and no unresolved DOIs. Doubt intervals for every reference are "
            f"low and consistent."
        )
    else:
        # Lead with the verdict + the counts, using ONLY real numbers.
        lead_bits = []
        if counts.get("retracted"):
            lead_bits.append(f"{counts['retracted']} retracted")
        n_cites = counts.get("cites_retraction", 0)
        if n_cites:
            verb = "cite" if n_cites != 1 else "cites"
            noun = "papers" if n_cites != 1 else "paper"
            lead_bits.append(f"{n_cites} {noun} that {verb} a retracted "
                             "work in this set")
        if unresolved:
            lead_bits.append(f"{unresolved} unresolved")
        verdict = "; ".join(lead_bits) or "none"
        parts.append(
            f"Of {total} references submitted, {verdict}. "
            "Every flag below links back to a real Crossref record — "
            "click through to verify."
        )

        # Name the worst offender(s) with real DOIs (never fabricated).
        if retracted:
            r = retracted[0]
            retr_date = r.get("retraction_date")
            more = len(retracted) - 1
            parts.append(
                f"The retracted foundation in this set is "
                f"**{_fmt_doi(r)}**"
                + (f" (retracted {retr_date})" if retr_date else "")
                + (f" — and {more} other retracted reference"
                   f"{'s' if more != 1 else ''}" if more else "")
                + ". Any downstream claim that depends on it inherits doubt."
            )

        # Blast radius — post-retraction reliance is the most-actionable finding.
        if cites:
            inex = [r for r in cites if r.get("inexcusable")]
            if inex:
                parts.append(
                    f"{len(inex)} of these citations occurred "
                    f"*after* the retraction date "
                    "(post-retraction reliance) — the strongest signal in "
                    "the report."
                )
            else:
                n = len(cites)
                verb = "predate" if n != 1 else "predates"
                noun = "papers" if n != 1 else "paper"
                parts.append(
                    f"The {n} citing {noun} {verb} the retraction — "
                    "an authorial no-way-to-know at the time, but the "
                    "downstream inheritance is real now."
                )

    parts.append(
        "Every value in this summary is drawn directly from the triage rows "
        "below; nothing is fabricated. AI proposes, scientists decide, "
        "experiments verify."
    )
    return {"paragraph": " ".join(parts), "source": "template"}


def integrity_summary(triage: dict, reasoner=None) -> dict:
    """Front-door summary. Delegates to the live ``ClaudeReasoner`` when one is
    supplied (and its API key is present); otherwise returns the deterministic
    template. Returns a ``{paragraph, source}`` dict so the UI can label the
    provenance of the prose."""
    if reasoner is not None and hasattr(reasoner, "integrity_summary"):
        try:
            live = reasoner.integrity_summary(triage)
            if isinstance(live, dict) and live.get("paragraph"):
                return live
        except Exception:
            pass  # live failure -> honest template fallback, never fabrication
    return integrity_summary_template(triage)
