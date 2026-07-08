"""
keystone.deterministic.ledger_index
==================================
Scientific Memory — a queryable index over a corpus of past Ledgers, NOT a new
database and NOT chat history. It reads a directory of ``Ledger.to_json()``
outputs and answers, deterministically: *has this hypothesis, or one grounded in
the same evidence, been tried before?*

Similarity is exact/overlap, never semantic (embedding similarity is Tier 3 per
Keystone_BuildPlan_and_Demo.md §3):
  - identical evidence graph  -> exact ``graph_hash`` match (reproduced before)
  - overlapping evidence base -> Jaccard overlap of the Ledger's ``sources``
  - overlapping grounding     -> overlap of ``hypothesis_grounding`` node ids

No LLM. The Ledger already IS the memory; this only indexes it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LedgerRecord:
    graph_hash: str
    question: str
    hypothesis_statement: str
    sources: frozenset
    grounding: frozenset
    path: str


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


class LedgerIndex:
    def __init__(self) -> None:
        self._records: list[LedgerRecord] = []

    def add_ledger_dict(self, d: dict, path: str = "") -> None:
        self._records.append(LedgerRecord(
            graph_hash=d.get("graph_hash", ""),
            question=d.get("question", ""),
            hypothesis_statement=d.get("hypothesis_statement") or "",
            sources=frozenset(d.get("sources", []) or []),
            grounding=frozenset(d.get("hypothesis_grounding", []) or []),
            path=path))

    def load_dir(self, directory: str | Path) -> "LedgerIndex":
        """Index every ``*.json`` Ledger in a directory."""
        for p in sorted(Path(directory).glob("*.json")):
            try:
                self.add_ledger_dict(json.loads(p.read_text()), str(p))
            except (json.JSONDecodeError, OSError):
                continue
        return self

    def __len__(self) -> int:
        return len(self._records)

    def find_prior_work(self, sources, grounding, graph_hash: str = "",
                        threshold: float = 0.3) -> dict:
        """Return prior Ledgers matching the given evidence base / grounding.
        Deterministic: sorted by overlap, exact-hash matches first."""
        sources, grounding = frozenset(sources), frozenset(grounding)
        matches = []
        for r in self._records:
            exact = bool(graph_hash) and r.graph_hash == graph_hash
            src_j = _jaccard(sources, r.sources)
            gnd_j = _jaccard(grounding, r.grounding)
            score = max(src_j, gnd_j)
            if exact or score >= threshold:
                matches.append({
                    "graph_hash": r.graph_hash, "question": r.question,
                    "hypothesis": r.hypothesis_statement,
                    "exact_reproduction": exact,
                    "source_overlap": round(src_j, 3),
                    "grounding_overlap": round(gnd_j, 3),
                    "shared_sources": sorted(sources & r.sources),
                    "path": r.path})
        matches.sort(key=lambda m: (not m["exact_reproduction"],
                                    -max(m["source_overlap"], m["grounding_overlap"])))
        return {"tried_before": bool(matches), "n_prior": len(self._records),
                "matches": matches}
