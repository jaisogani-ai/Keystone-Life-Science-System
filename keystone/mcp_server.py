"""
keystone.mcp_server
==================
Keystone as an MCP server — the integration that makes it a Claude Science-native
capability. Claude Code, Claude Desktop, or a Claude Agent SDK client connects to
this server and calls Keystone's scientific tools: rank competing hypotheses,
classify a citing sentence's load-bearing weight (the moat), summarize the
evidence, search real clinical trials, check scientific memory, and emit a
publication report.

The tools are the DETERMINISTIC engine (real data, no fabrication); the moat
classifier can run live on Claude when KEYSTONE_LIVE=1 + ANTHROPIC_API_KEY is set,
otherwise the transparent heuristic. Run it:

    python -m keystone.mcp_server            # stdio transport for an MCP client

Register in an MCP client (e.g. Claude Desktop / Claude Code) config:
    {"mcpServers": {"keystone": {"command": "python", "args": ["-m", "keystone.mcp_server"]}}}
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from keystone.decision_engine import decide
from keystone.connectors import clinical as C
from keystone.artifacts.report import research_report_html
from keystone.artifacts.graph_export import graph_to_dict

mcp = FastMCP("keystone")


def _reasoner():
    # Claude runs iff a key is present and not forced offline. Setting
    # ANTHROPIC_API_KEY is enough (KEYSTONE_LIVE=1 still accepted for compat).
    live = os.environ.get("KEYSTONE_OFFLINE") != "1" and (
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("KEYSTONE_LIVE") == "1")
    if live:
        try:
            from keystone.agents.claude_reasoner import ClaudeReasoner
            return ClaudeReasoner()
        except Exception:
            pass
    from keystone.agents.reasoner import HeuristicReasoner
    return HeuristicReasoner()


@mcp.tool()
def next_experiment(domain: str = "gbm") -> dict:
    """Recommend the single next experiment to run for a disease domain
    ('gbm' or 'insulin'): what to run, why, cost/duration/risk, how to falsify
    it, and why it beats the alternatives. The core Keystone decision."""
    d, *_ = decide(domain)
    return d["recommendation"]


@mcp.tool()
def competing_hypotheses(domain: str = "gbm") -> list:
    """Return the ranked competing hypotheses with their decision-board scores
    (priority, expected information gain, cost, risk, kind). A scientist chooses
    among these; every score is computed/estimate/qualitative, never fabricated."""
    d, *_ = decide(domain)
    return [{"rank": s["rank"], "id": s["id"], "kind": s["kind"],
             "statement": s["statement"],
             "priority": s["priority_score"]["value"],
             "information_gain": s["information_gain"]["value"],
             "cost_usd": s["cost_usd"]["value"], "risk": s["risk"]["value"],
             "why": s.get("why", [])} for s in d["competing_hypotheses"]]


@mcp.tool()
def classify_load_bearing(citing_sentence: str) -> dict:
    """Classify how LOAD-BEARING a citing sentence is (does the citing work rely
    on the cited paper's specific result?) vs. incidental. Calibrated at 0.818
    agreement with a hand-labelled reference set (single-annotator baseline, not
    an inter-annotator ceiling; reproduce with calibrate.py). Uses Claude live
    when KEYSTONE_LIVE=1, else the transparent heuristic."""
    iv = _reasoner().classify_load_bearing(citing_sentence)
    return {"load_bearing": iv.point, "interval": [iv.low, iv.high],
            "verdict": "load-bearing" if iv.point >= 0.5 else "incidental"}


@mcp.tool()
def evidence_summary(domain: str = "gbm") -> dict:
    """Summarize the evidence graph for a domain: node/edge counts, contradictions,
    knowledge gaps, cited sources, and the reproducibility hash."""
    d, graph, *_ = decide(domain)
    return {"domain": domain, "question": d["question"],
            "graph_hash": d["graph_hash"],
            "contradictions": len(d["contradictions"]),
            "knowledge_gaps": d["knowledge_gaps"]["count"],
            "gap_types": [g["type"] for g in d["knowledge_gaps"]["gaps"]],
            "nodes": len(graph.nodes), "edges": len(graph.edges),
            "sources": sorted({n.source for n in graph.nodes.values()
                               if n.source and n.source != "unresolved"})}


@mcp.tool()
def search_clinical_trials(condition: str, limit: int = 8) -> dict:
    """Search real ClinicalTrials.gov (v2 API) for trials on a condition; returns
    NCT id, status, phase, and eligibility. Real data or 'unresolved' — never
    fabricated."""
    return C.clinical_trials(condition, limit=limit)


@mcp.tool()
def evidence_graph(domain: str = "gbm") -> dict:
    """Return the full evidence graph (nodes with NodeType + doubt intervals,
    edges with load-bearing weight + temporal relation) as JSON."""
    _, graph, *_ = decide(domain)
    return graph_to_dict(graph)


@mcp.tool()
def check_reference_integrity(dois: list[str], question: str = "") -> dict:
    """Triage a scientist's OWN reference list (a list of DOIs from Zotero/Mendeley
    /EndNote) for research-integrity concerns: which papers are retracted, which
    cite a retracted work in the set (the blast radius), which won't resolve, and
    which inherit elevated doubt. Every flag links back to a real source; nothing
    is fabricated. Returns the per-reference triage + summary counts + the
    reproducibility hash. This is the tool a scientist calls from Claude Desktop
    to make Keystone useful without opening the app."""
    from keystone.ingest.references import build_graph_from_dois
    from keystone.integrity_report import reference_integrity
    graph = build_graph_from_dois(question or "reference integrity check", dois)
    return reference_integrity(graph)


@mcp.tool()
def validation_metrics(domain: str = "gbm") -> dict:
    """Report Keystone's measured accuracy: run the flaw-catch evaluation (planted
    known flaws + benign controls) and return caught / missed / false-alarm counts
    with precision/recall/F1. The proof-of-trust number a scientist can verify."""
    from keystone.agents.flaw_catch_eval import evaluate
    from keystone.agents.reasoner import HeuristicReasoner
    from keystone.decision_engine import _spec_and_builder
    _, build = _spec_and_builder(domain)
    r = evaluate(HeuristicReasoner(), build)
    return {"domain": domain,
            "caught": r["tp"], "missed": r["fn"], "false_alarms": r["fp"],
            "n_planted": r["tp"] + r["fn"], "n_benign": r["tn"] + r["fp"],
            "accuracy": round(r["accuracy"], 3),
            "precision": round(r["precision"], 3),
            "recall": round(r["recall"], 3), "f1": round(r["f1"], 3),
            "load_bearing_agreement": 0.818}


@mcp.tool()
def publication_report(domain: str = "gbm") -> str:
    """Generate a publication-ready research report (HTML) citing real DOIs, with
    the independent reviewer critique, figures, provenance appendix, and
    reproducibility hash."""
    d, graph, ledger, hyp, review = decide(domain)
    return research_report_html(d["question"], graph, ledger, hyp, review)


@mcp.tool()
def mine_literature_patterns(records: list, question: str = "",
                              seed_doi: str = "",
                              scan_type: str = "all") -> dict:
    """Scan a corpus of OpenAlex-shaped paper records and return four kinds of
    literature pattern manual reading misses: contradiction clusters, assay
    method drift over time, flagged reagent contamination trends, and
    consensus-vs-outlier claim clusters. Each hit cites REAL DOIs from the
    input corpus — nothing is fabricated. Out-of-scope scans (causal
    inference, patient outcome, drug efficacy, clinical decision support)
    return a structured refusal with the reason."""
    from keystone.agents.pattern_miner import mine_patterns
    result = mine_patterns(records or [], question=question,
                            seed_doi=seed_doi, scan_type=scan_type)
    return result.to_dict()


@mcp.tool()
def review_bench_data(csv_text: str, label: str = "plate",
                       fmt: str = "plate_reader_csv") -> dict:
    """The Laboratory Agent's review: run deterministic QC on a 96-well
    plate-reader CSV (standard-curve R², replicate CV, edge effect, missing
    wells), then return a Reviewer verdict (supported / downgraded / rejected)
    that downgrades confidence when the data fails QC, with grounded workflow
    fixes. Every threshold is cite-able (FDA Bioanalytical 2018; Ekins & Chu
    1988). Instrument formats without a validated interpretation model
    (western blot, microscopy, CryoEM, FCS, FASTQ) are refused with a
    structured explanation — never a fabricated reading."""
    from keystone.agents.bench_reviewer import review_plate
    return review_plate(csv_text or "", label=label, fmt=fmt).to_dict()


@mcp.tool()
def discovery_run(records: list, domain: str = "gbm", question: str = "",
                   seed_doi: str = "", bench_csv: str = "") -> dict:
    """Run Keystone's self-correcting loop end to end: mine literature
    contradictions from a paper corpus, turn each into a rankable competing
    hypothesis, rank it on the SAME auditable decision board as the graph-
    derived hypotheses, and — if a validation plate CSV is supplied — downgrade
    the recommendation's confidence when the plate fails QC. Every number is
    deterministic; a literature-only hypothesis carries honest default
    uncertainty (never an inflated graph score); a failing plate downgrades the
    hypothesis it was meant to test."""
    from keystone.discovery_run import run_discovery
    return run_discovery(records or [], domain=domain, question=question,
                         seed_doi=seed_doi,
                         bench_csv=(bench_csv or None))


@mcp.tool()
def assess_frontier(frontier: str, genes: list | None = None,
                     study: dict | None = None, records: list | None = None,
                     question: str = "") -> dict:
    """Frontier Guard — Keystone's responsible-AI layer for three frontier
    claims. frontier='phage_design' vets a phage-genome candidate for biosafety
    (toxin / lysogeny / AMR screen + host-range) → go/caution/no-go, and refuses
    to prescribe a phage. frontier='organoid_response' scores an organoid study
    for reproducibility risk (low/medium/high). frontier='aging_clock' scores a
    biological-age-acceleration study's rigor and benchmarks a claimed result
    against published clocks (Horvath / PhenoAge / GrimAge). Each adds a
    literature evidence scan (when records are supplied) and a rigor checklist.
    Keystone NEVER generates a sequence, prescribes a phage, predicts a
    patient's treatment response, computes a patient's biological age, reads
    patient images, or ingests PHI — unknown frontiers are refused."""
    from keystone.frontier_guard import assess_frontier as _assess
    return _assess(frontier, genes=genes, study=study,
                   records=records, question=question)


@mcp.tool()
def field_integrity(records: list, question: str = "",
                    seed_doi: str = "") -> dict:
    """Compute a Field Integrity Report — a transparent, auditable integrity
    index (0-100) for a corpus of literature, from real signals: retraction
    burden, post-publication-change burden, and integrity-pattern load
    (contradiction / method-drift / reagent-trend). Answers "how contaminated
    is the literature I'm building on?" Every weight is exposed; nothing is
    fabricated. Pairs with the printable Research Integrity Audit."""
    from keystone.field_integrity import field_integrity_report
    return field_integrity_report(records or [], question=question,
                                  seed_doi=seed_doi)


@mcp.tool()
def check_prior_art(query: str) -> dict:
    """"Did someone already discover this?" — search OpenAlex for the closest
    existing work to a hypothesis or research question, so a scientist does not
    re-run a published experiment. Returns REAL records (or none); flags any
    retracted match; NEVER issues a novelty verdict — surfacing overlap is the
    tool's job, judging novelty is the scientist's."""
    from keystone.prior_art import check_prior_art as _cpa
    return _cpa(query or "")


@mcp.tool()
def post_publication_changes(doi: str) -> dict:
    """"Which papers changed after publication?" — every Crossref post-
    publication change for a DOI: retractions, corrections, errata, and
    expressions of concern (not just retractions). Real data or an explicit
    unresolved marker; never fabricated."""
    from keystone.connectors.registry import post_publication_updates
    return post_publication_updates(doi or "")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
