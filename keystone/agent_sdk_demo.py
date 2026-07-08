"""
keystone.agent_sdk_demo
=====================
Keystone driven by the Claude Agent SDK. A Claude agent is given Keystone's
scientific tools (in-process SDK MCP server) and asked what experiment to run
next — it CALLS the tools, then reasons over the structured results. This is the
"agents exchange structured artifacts, not chat" pattern: Keystone's deterministic
engine produces the evidence and the numbers; the Agent SDK coordinates.

    KEYSTONE_LIVE=1 ANTHROPIC_API_KEY=... python -m keystone.agent_sdk_demo

Without a key it prints activation instructions and exits (no budget spent). A
$0.50 budget cap bounds cost. The tools themselves are free/deterministic.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

from keystone.decision_engine import decide
from keystone.connectors import clinical as C

try:
    from claude_agent_sdk import (query, tool, create_sdk_mcp_server,
                                  ClaudeAgentOptions, AssistantMessage,
                                  TextBlock, ToolUseBlock)
    _SDK = True
except ImportError:
    _SDK = False

_MODEL = os.environ.get("KEYSTONE_MODEL", "claude-sonnet-5")


def _text(obj) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(obj, default=str)}]}


def _build_tools():
    @tool("next_experiment", "Recommend the single next experiment for a disease "
          "domain (gbm|insulin): what to run, why, cost/risk, how to falsify it.",
          {"domain": str})
    async def next_experiment(args):
        d, *_ = decide(args.get("domain", "gbm"))
        return _text(d["recommendation"])

    @tool("competing_hypotheses", "List the ranked competing hypotheses with "
          "decision scores (priority, expected info gain, cost, risk).",
          {"domain": str})
    async def competing_hypotheses(args):
        d, *_ = decide(args.get("domain", "gbm"))
        return _text([{"rank": s["rank"], "id": s["id"], "kind": s["kind"],
                       "priority": s["priority_score"]["value"],
                       "eig": s["information_gain"]["value"],
                       "cost_usd": s["cost_usd"]["value"], "risk": s["risk"]["value"],
                       "statement": s["statement"]} for s in d["competing_hypotheses"]])

    @tool("search_clinical_trials", "Search real ClinicalTrials.gov for a condition.",
          {"condition": str})
    async def search_clinical_trials(args):
        return _text(C.clinical_trials(args.get("condition", ""), limit=5))

    return [next_experiment, competing_hypotheses, search_clinical_trials]


_PROMPT = (
    "You are a research advisor. Using ONLY the Keystone tools, determine the "
    "single most important experiment to run next for glioblastoma and justify "
    "it over the alternatives. Call next_experiment and competing_hypotheses, "
    "then give a 4-sentence recommendation a PI could act on. Do not invent "
    "numbers — cite the tool outputs.")


async def run_live() -> int:
    server = create_sdk_mcp_server("keystone", tools=_build_tools())
    options = ClaudeAgentOptions(
        model=_MODEL,
        mcp_servers={"keystone": server},
        allowed_tools=["mcp__keystone__next_experiment",
                       "mcp__keystone__competing_hypotheses",
                       "mcp__keystone__search_clinical_trials"],
        max_budget_usd=0.50,
        system_prompt="Coordinate Keystone's tools; never fabricate a value.")
    print("=== Keystone x Claude Agent SDK — live ===\n")
    async for msg in query(prompt=_PROMPT, options=options):
        if isinstance(msg, AssistantMessage):
            for b in msg.content:
                if isinstance(b, ToolUseBlock):
                    print(f"[agent calls tool] {b.name}({json.dumps(b.input)})")
                elif isinstance(b, TextBlock):
                    print(b.text)
    return 0


def main() -> int:
    if not _SDK:
        print("Install the SDK:  pip install claude-agent-sdk")
        return 1
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(__doc__)
        print("\nSet ANTHROPIC_API_KEY (and KEYSTONE_LIVE=1) to run the live "
              "agent. Nothing was billed.")
        return 0
    return asyncio.run(run_live())


if __name__ == "__main__":
    sys.exit(main())
