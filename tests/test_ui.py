"""
UI server tests — the UI is pure projection of the engine, so we assert the
bundle it serves has every panel's data and that human approval writes back to
the Ledger. Skipped cleanly if FastAPI is not installed.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

import pytest  # noqa: E402

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from keystone.ui import server  # noqa: E402
from keystone.data_gbm import build_gbm_graph  # noqa: E402
from keystone.workbench import run  # noqa: E402
from keystone.replay import record_session  # noqa: E402
from keystone.agents.reasoner import HeuristicReasoner  # noqa: E402

client = TestClient(server.app)


def _make_bundle():
    graph = build_gbm_graph()
    ledger, hyp, review = run("Q", graph, HeuristicReasoner())
    session = record_session("Q", graph, ledger, hyp, review)
    return server._bundle("sid", "Q", graph, ledger, hyp, review, session)


def test_index_and_default_question():
    assert client.get("/").status_code == 200
    q = client.get("/api/default-question").json()["question"]
    assert "glioblastoma" in q.lower()


def test_bundle_has_every_panel():
    b = _make_bundle()
    for key in ("hypothesis", "review", "why_panel", "future_tree", "readiness",
                "timeline", "nodes", "evidence_graph_svg", "timeline_svg",
                "protein_html", "session", "ledger"):
        assert key in b, f"bundle missing {key}"
    assert b["evidence_graph_svg"].startswith("<svg")
    assert "data-node" in b["evidence_graph_svg"]            # clickable
    assert b["review"]["verdict"] == "downgraded"            # self-challenge
    assert "%" not in str(b["readiness"]["novelty"]["estimate"])  # honest


def test_approval_writes_back_to_ledger_with_attribution():
    sid = "test-sid-1"
    graph = build_gbm_graph()
    ledger, hyp, review = run("Q", graph, HeuristicReasoner())
    server._SESSIONS[sid] = {"graph": graph, "ledger": ledger, "hyp": hyp,
                             "review": review, "question": "Q"}
    r = client.post("/api/approve", json={"session_id": sid,
                                          "decision": "override", "who": "Dr. X",
                                          "note": "needs replication"})
    assert r.status_code == 200
    body = r.json()
    assert body["human_decision"] == "override" and "Dr. X" in body["human_signoff"]
    assert ledger.human_decision == "override"   # written back to the object


def test_approval_unknown_session_404():
    r = client.post("/api/approve", json={"session_id": "nope",
                                          "decision": "approved"})
    assert r.status_code == 404


if __name__ == "__main__":
    test_index_and_default_question()
    test_bundle_has_every_panel()
    test_approval_writes_back_to_ledger_with_attribution()
    test_approval_unknown_session_404()
    print("all ui tests passed")
