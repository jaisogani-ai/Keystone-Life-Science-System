"""
MCP server + Agent SDK integration tests. The tools must register and return real
engine data offline (no budget). The live ClaudeReasoner must wire correctly with
anthropic installed but refuse cleanly without a key.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

import asyncio  # noqa: E402

from keystone import mcp_server as M                              # noqa: E402

_EXPECTED = {"next_experiment", "competing_hypotheses", "classify_load_bearing",
             "evidence_summary", "search_clinical_trials", "evidence_graph",
             "publication_report", "check_reference_integrity",
             "validation_metrics"}


def test_mcp_server_registers_tools():
    tools = asyncio.new_event_loop().run_until_complete(M.mcp.list_tools())
    names = {t.name for t in tools}
    assert _EXPECTED <= names


def test_next_experiment_tool_returns_real_recommendation():
    rec = M.next_experiment("gbm")
    assert rec["hypothesis_id"] and rec["how_to_falsify"].strip()
    assert rec["over_alternatives"]


def test_competing_hypotheses_tool_is_ranked():
    hy = M.competing_hypotheses("gbm")
    assert len(hy) >= 5 and hy[0]["rank"] == 1
    assert hy[0]["priority"] >= hy[-1]["priority"]


def test_classify_load_bearing_tool_discriminates():
    lb = M.classify_load_bearing(
        "Inhibition of Cts B in glioblastoma cells attenuated their invasion.")
    inc = M.classify_load_bearing(
        "Moreover, MMPs are associated with cancer generally [4, 7, 12].")
    assert lb["load_bearing"] > inc["load_bearing"]
    assert lb["verdict"] == "load-bearing"


def test_evidence_summary_tool_carries_hash_and_sources():
    ev = M.evidence_summary("gbm")
    assert ev["graph_hash"] and ev["nodes"] >= 1 and ev["sources"]


def test_search_trials_tool_is_real():
    t = M.search_clinical_trials("glioblastoma", limit=3)
    assert t["resolved"] and int(t["total"]) > 100


def test_check_reference_integrity_tool_runs_on_a_scientists_own_dois():
    """The 'usable without you in the room' tool — a scientist calls this from
    Claude Desktop with their own DOIs and gets a real, verifiable triage."""
    tri = M.check_reference_integrity(
        ["10.1038/sj.onc.1207616", "10.1038/414799a", "10.9999/no.such.doi"])
    assert tri["total"] == 3
    assert tri["counts"]["retracted"] >= 1        # the real retraction
    assert tri["counts"]["unresolved"] >= 1       # the honest miss
    assert tri["rows"][0]["status"] == "retracted"


def test_validation_metrics_tool_reports_a_verifiable_number():
    v = M.validation_metrics("gbm")
    assert v["caught"] + v["missed"] == v["n_planted"]
    assert 0.0 <= v["accuracy"] <= 1.0
    assert v["load_bearing_agreement"] == 0.818


def test_agent_sdk_tools_build():
    from keystone.agent_sdk_demo import _build_tools, _SDK
    assert _SDK, "claude-agent-sdk should be installed"
    tools = _build_tools()
    assert len(tools) == 3


def test_claude_reasoner_wires_and_refuses_without_key():
    from keystone.agents.claude_reasoner import ClaudeReasoner
    r = ClaudeReasoner()
    assert r.version == "claude-1.0" and r.model
    os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        _ = r.client
        raised = False
    except RuntimeError:
        raised = True
    assert raised, "must refuse (not fabricate) without an API key"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all mcp tests passed")
