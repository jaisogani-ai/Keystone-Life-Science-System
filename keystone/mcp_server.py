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
    if os.environ.get("KEYSTONE_LIVE") == "1":
        from keystone.agents.claude_reasoner import ClaudeReasoner
        return ClaudeReasoner()
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
    on the cited paper's specific result?) vs. incidental. This is Keystone's
    calibrated moat (0.818 agreement on real labeled sentences). Uses Claude live
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
def publication_report(domain: str = "gbm") -> str:
    """Generate a publication-ready research report (HTML) citing real DOIs, with
    the independent reviewer critique, figures, provenance appendix, and
    reproducibility hash."""
    d, graph, ledger, hyp, review = decide(domain)
    return research_report_html(d["question"], graph, ledger, hyp, review)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
