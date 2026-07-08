# Keystone integrations — live Claude, MCP server, Agent SDK

Keystone runs fully offline on pinned real data. These three integrations turn on
the live AI and make Keystone a Claude Science–native capability. Your API key is
set as an environment variable and **never enters the codebase or a chat**.

```bash
pip install -e ".[live,agent,ui]"     # anthropic + mcp + claude-agent-sdk + fastapi
```

## 1. Live Claude reasoner

The five semantic agents (Planner, Literature/Evidence-Quality, Experiment Design,
Reviewer, + the pathway-figure vision agent) run on Claude instead of the offline
heuristic. Statistics stay deterministic — Claude never emits a number (rule 7).

```bash
export ANTHROPIC_API_KEY=sk-...        # your key, in the environment only
KEYSTONE_LIVE=1 python run_workbench.py           # live loop
KEYSTONE_LIVE=1 python calibrate.py --domain gbm  # measure the live moat
KEYSTONE_LIVE=1 python -m keystone.ui.server       # live UI at :8000
```

Model is `claude-sonnet-5` by default; override with `KEYSTONE_MODEL`
(e.g. `claude-haiku-4-5-20251001` for the cheap per-citation moat calls).

## 2. MCP server — expose Keystone to any Claude agent

`keystone/mcp_server.py` exposes 7 tools over MCP: `next_experiment`,
`competing_hypotheses`, `classify_load_bearing` (the moat), `evidence_summary`,
`evidence_graph`, `search_clinical_trials`, `publication_report`. The tools are the
deterministic engine — real data, no budget.

**Claude Code** (this repo): auto-discovered via the committed `.mcp.json`.

**Claude Desktop** — add to its MCP config:

```json
{ "mcpServers": { "keystone": {
    "command": "python3", "args": ["-m", "keystone.mcp_server"],
    "env": { "PYTHONPATH": "/absolute/path/to/keystone_wb" } } } }
```

Then ask Claude: *"Use Keystone to tell me which glioblastoma experiment to run
next and why."* Claude calls the tools and reasons over the structured results.

## 3. Claude Agent SDK demo

`keystone/agent_sdk_demo.py` builds an in-process SDK MCP server of Keystone tools,
hands them to a Claude agent, and asks it to recommend the next experiment. A
$0.50 budget cap bounds cost.

```bash
KEYSTONE_LIVE=1 ANTHROPIC_API_KEY=sk-... python -m keystone.agent_sdk_demo
```

Without a key it prints these instructions and exits — nothing is billed.

---

Everything above degrades safely: no key → the offline heuristic runs and every
tool still returns real, reproducible data. The moat is already a measured number
offline (0.818 on two domains); running the live calibration proves it on Claude.
