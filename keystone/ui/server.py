"""
keystone.ui.server
=================
Local web workbench (FastAPI). The UI holds NO scientific logic — every endpoint
is a projection of the existing engine: it calls ``build_gbm_graph`` / ``run`` /
the reasoning panels / the renderers and serializes the result. Human approval is
written back into the Ledger with attribution (rule 1).

    python -m keystone.ui.server        # then open http://127.0.0.1:8000
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import (FileResponse, StreamingResponse, JSONResponse,
                               HTMLResponse)

from keystone.data_gbm import build_gbm_graph
from keystone.gbm_spec import QUESTION
from keystone.workbench import run
from keystone.reasoning_panel import (why_panel, future_experiments_tree,
                                      research_readiness)
from keystone.replay import record_session
from keystone.artifacts.render import (evidence_graph_svg, timeline_svg,
                                       protein_viewer_html)
from keystone.workspace import build_workspace
from keystone.deterministic.ledger_index import LedgerIndex

app = FastAPI(title="Keystone Discovery OS")
_STATIC = Path(__file__).parent / "static"
_SESSIONS: dict = {}   # in-memory: session_id -> {graph, ledger, hyp, review}
_MEMORY = LedgerIndex()   # scientific memory across workspace runs this session


def _reasoner():
    if os.environ.get("KEYSTONE_LIVE") == "1":
        from keystone.agents.claude_reasoner import ClaudeReasoner
        return ClaudeReasoner()
    from keystone.agents.reasoner import HeuristicReasoner
    return HeuristicReasoner()


def _node_details(graph) -> dict:
    return {nid: {"id": nid, "type": n.node_type.value, "source": n.source,
                  "text": n.text, "doubt": round(n.doubt.point, 3),
                  "doubt_interval": [n.doubt.low, n.doubt.high],
                  "retracted": n.retracted, "inexcusable": n.inexcusable,
                  "date": n.date}
            for nid, n in graph.nodes.items()}


def _bundle(sid, question, graph, ledger, hyp, review, session) -> dict:
    return {
        "session_id": sid,
        "question": question,
        "ledger": json.loads(ledger.to_json()),
        "hypothesis": {
            "statement": hyp.statement,
            "confidence": {"point": hyp.confidence.point,
                           "low": hyp.confidence.low, "high": hyp.confidence.high},
            "supporting_evidence": hyp.supporting_evidence,
            "contradicting_evidence": hyp.contradicting_evidence,
            "failure_modes": hyp.failure_modes,
            "expected_outcome": hyp.expected_outcome,
            "experiment": asdict(hyp.validation_experiment)},
        "review": {"verdict": review.verdict.value, "weakness": review.weakness,
                   "adjusted_confidence": review.adjusted_confidence.point,
                   "objections": review.objections},
        "why_panel": why_panel(hyp, review, graph),
        "future_tree": future_experiments_tree(hyp, graph),
        "readiness": research_readiness(hyp, review, graph),
        "timeline": ledger.timeline,
        "nodes": _node_details(graph),
        "evidence_graph_svg": evidence_graph_svg(graph),
        "timeline_svg": timeline_svg(ledger.timeline),
        "protein_html": protein_viewer_html(
            graph.nodes["N_target"].meta.get("pdb", "1HUC"),
            graph.nodes["N_target"].text),
        "session": [asdict(s) for s in session.steps],
    }


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.get("/")
def index():
    return FileResponse(_STATIC / "decision.html")


@app.get("/workspace")
def workspace_page():
    return FileResponse(_STATIC / "os.html")


@app.get("/workbench")
def workbench_page():
    return FileResponse(_STATIC / "index.html")


@app.get("/api/decision")
def decision_api(domain: str = "gbm"):
    """The Scientific Decision Engine: competing hypotheses, ranked, with the
    next-experiment recommendation. Deterministic; enriched with why-panel +
    graph for drill-down."""
    from keystone.decision_engine import decide
    d, graph, ledger, hyp, review = decide(domain)
    d["why_panel"] = why_panel(hyp, review, graph)
    d["evidence_graph_svg"] = evidence_graph_svg(graph)
    return d


@app.get("/api/workspace")
def workspace(domain: str = "gbm"):
    """The Disease Workspace: real connectors + reasoning + scientific memory.
    Deterministic; enriched with the existing artifacts."""
    ws, graph, ledger, hyp, review = build_workspace(domain)
    # scientific memory: check BEFORE recording this run, then remember it
    prior = _MEMORY.find_prior_work(ledger.sources, ledger.hypothesis_grounding,
                                    ledger.graph_hash)
    _MEMORY.add_ledger_dict(json.loads(ledger.to_json()), path=f"{domain}-run")
    ws["scientific_memory"] = prior
    ws["why_panel"] = why_panel(hyp, review, graph)
    ws["evidence_graph_svg"] = evidence_graph_svg(graph)
    ws["timeline_svg"] = timeline_svg(ledger.timeline)
    tgt = graph.nodes["N_target"]
    ws["protein_html"] = protein_viewer_html(tgt.meta.get("pdb", "1HUC"), tgt.text)
    ws["reasoning_loop"] = ["Planner", "Evidence Collection", "Quality Validation",
                            "Knowledge Graph", "Contradiction Mining",
                            "Gap Detection", "Hypothesis", "Reviewer",
                            "Experiment Design", "Protocol + Statistics",
                            "Evidence Ledger", "Human Scientist"]
    return ws


@app.get("/api/default-question")
def default_question():
    return {"question": QUESTION}


@app.get("/api/stream")
def stream(question: str = ""):
    question = question.strip() or QUESTION

    def gen():
        yield _sse({"type": "stage", "stage": "PLAN", "summary": "decomposing question"})
        graph = build_gbm_graph()
        reasoner = _reasoner()
        yield _sse({"type": "stage", "stage": "COLLECT",
                    "summary": f"{len(graph.nodes)} nodes from real connectors"})
        time.sleep(0.2)
        ledger, hyp, review = run(question, graph, reasoner)
        session = record_session(question, graph, ledger, hyp, review)
        # stream the recorded stages for live progress (ordered projection)
        for step in session.steps:
            yield _sse({"type": "stage", "stage": step.stage,
                        "summary": step.summary})
            time.sleep(0.3)
        sid = uuid.uuid4().hex[:12]
        _SESSIONS[sid] = {"graph": graph, "ledger": ledger, "hyp": hyp,
                          "review": review, "question": question}
        yield _sse({"type": "done",
                    "data": _bundle(sid, question, graph, ledger, hyp, review,
                                    session)})

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/approve")
async def approve(request: Request):
    body = await request.json()
    sid = body.get("session_id")
    sess = _SESSIONS.get(sid)
    if not sess:
        return JSONResponse({"error": "unknown or expired session"},
                            status_code=404)
    decision = body.get("decision", "approved")
    who = (body.get("who") or "anonymous").strip()
    note = (body.get("note") or "").strip()
    ledger = sess["ledger"]
    ledger.human_decision = decision
    ledger.human_signoff = (f"{who} @ {time.strftime('%Y-%m-%d %H:%M:%S')}"
                            + (f" — {note}" if note else ""))
    return {"human_decision": ledger.human_decision,
            "human_signoff": ledger.human_signoff,
            "graph_hash": ledger.graph_hash}


def main() -> int:
    import uvicorn
    port = int(os.environ.get("KEYSTONE_PORT", "8000"))
    print(f"Keystone workbench UI -> http://127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
