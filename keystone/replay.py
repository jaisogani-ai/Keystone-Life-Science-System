"""
keystone.replay
===============
Session Replay (#4). Records every workbench stage as an ordered, timestamped
step list and replays it deterministically. Aligned with the reproducibility /
full-audit-history direction: a scientist (or a reviewer, or an integrity
office) can step through exactly how a conclusion was reached.

This is not a new engine — it is an ordered projection of what the workbench
already did. No LLM.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field


@dataclass
class ReplayStep:
    index: int
    stage: str
    summary: str
    detail: dict = field(default_factory=dict)


@dataclass
class Session:
    question: str
    graph_hash: str
    reasoner_version: str
    steps: list = field(default_factory=list)

    def record(self, stage: str, summary: str, detail: dict | None = None) -> None:
        self.steps.append(ReplayStep(len(self.steps), stage, summary,
                                     detail or {}))

    def to_json(self) -> str:
        return json.dumps({"question": self.question,
                           "graph_hash": self.graph_hash,
                           "reasoner_version": self.reasoner_version,
                           "steps": [asdict(s) for s in self.steps]},
                          indent=2, default=str)

    def replay(self) -> None:
        """Deterministic step-through — same session, same sequence, every time."""
        print(f"\n=== SESSION REPLAY ({len(self.steps)} steps) ===")
        print(f"Q: {self.question}")
        print(f"graph_hash={self.graph_hash}  reasoner={self.reasoner_version}\n")
        for s in self.steps:
            print(f"  [{s.index}] {s.stage:16s} {s.summary}")


def record_session(question: str, graph, ledger, hyp, review) -> Session:
    """Build a replayable session from a completed run's artifacts."""
    s = Session(question=question, graph_hash=ledger.graph_hash,
                reasoner_version=ledger.reasoner_version)
    s.record("PLAN", f"intent={ledger.plan.get('intent')}",
             {"plan": ledger.plan})
    s.record("COLLECT", f"{len(graph.nodes)} nodes, {len(graph.edges)} edges",
             {"nodes": list(graph.nodes)})
    lb = {e.src: round(e.load_bearing.point, 2) for e in graph.edges
          if e.edge_type.value in ("cites", "depends_on")}
    s.record("ANALYZE", f"load-bearing weights: {lb}",
             {"contradictions": ledger.contradictions})
    s.record("HYPOTHESIS", hyp.statement[:80],
             {"confidence": hyp.confidence.point,
              "failure_modes": hyp.failure_modes})
    s.record("EXPERIMENT", f"n/arm={hyp.validation_experiment.required_n_per_arm}",
             {"kill_condition": hyp.validation_experiment.kill_condition})
    s.record("REVIEW", f"{review.verdict.value}: {review.weakness[:60]}",
             {"adjusted_confidence": review.adjusted_confidence.point})
    s.record("LEDGER", f"emitted, hash={ledger.graph_hash}", {})
    return s
