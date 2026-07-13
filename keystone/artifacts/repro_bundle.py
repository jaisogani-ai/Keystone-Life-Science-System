"""
keystone.artifacts.repro_bundle
================================
The reproducibility bundle — the provenance package a reviewer can re-run.
Every file is a projection of the real engine output; nothing is invented
(spec Phase 4.6 / acceptance test #8). Retracted sources resolve but are
excluded from positive support; missing linkage renders ``not available``.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import platform
import sys

from keystone.deterministic.claim_status import node_claim, assess_claim


def _now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _code_version() -> str:
    """The code version a reviewer would check out to reproduce this run: the git
    commit (short SHA, ``+dirty`` when the working tree has uncommitted changes).
    Falls back to ``unavailable`` when git or the repo is absent — never fabricated."""
    import subprocess
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    try:
        sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if sha.returncode != 0:
            return "unavailable (not a git checkout)"
        rev = sha.stdout.strip()
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                              capture_output=True, text=True, timeout=5)
        return f"git:{rev}{'+dirty' if dirty.stdout.strip() else ''}"
    except Exception:
        return "unavailable"


def _num(v):
    return v.get("value", v) if isinstance(v, dict) else v


def _sources_csv(graph) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["node_id", "type", "source_id", "title",
                "record_verified", "integrity_state", "retracted"])
    for nid, n in graph.nodes.items():
        c = node_claim(n)
        w.writerow([nid, n.node_type.value, n.source or "", n.text,
                    c["source_record_verified"], c["integrity_state"], n.retracted])
    return buf.getvalue()


def _claims_json(graph) -> str:
    return json.dumps({nid: node_claim(n) for nid, n in graph.nodes.items()},
                      indent=2)


def _assessments_json(graph, hyp, review) -> str:
    conclusion = {"id": getattr(hyp, "id", "H1"),
                  "supporting_evidence": getattr(hyp, "supporting_evidence", []),
                  "contradicting_evidence": getattr(hyp, "contradicting_evidence", []),
                  "reviewer_decision": review.verdict.value}
    # assess everything the conclusion cites — PLUS every retracted node, so the
    # bundle documents that retracted sources resolved yet were excluded.
    involved = (set(conclusion["supporting_evidence"])
                | set(conclusion["contradicting_evidence"])
                | {nid for nid, n in graph.nodes.items()
                   if getattr(n, "retracted", False)})
    return json.dumps([assess_claim(nid, graph.nodes[nid], conclusion)
                       for nid in sorted(involved) if nid in graph.nodes], indent=2)


def _run_manifest(domain, ledger, decision, live_meta) -> str:
    rec = (decision or {}).get("recommendation") or {}
    manifest = {
        "domain": domain,
        "question": ledger.question,
        "dataset_version": f"graph:{ledger.graph_hash}",
        "graph_hash": ledger.graph_hash,
        "seed": "0x1f",
        "reasoner_version": ledger.reasoner_version,
        "engine": "deterministic scoring (every number) + Claude (prose/judgment)",
        "model": (live_meta.get("model", "claude (live)")
                  if live_meta.get("live") else "deterministic fallback (no live model)"),
        "live_claude": bool(live_meta.get("live")),
        "prompt_version": "keystone-reasoner-1.0",
        "code_version": _code_version(),  # git commit to check out (real, or "unavailable")
        "evidence_hash": ledger.graph_hash,  # content-addressed over the evidence graph
        "environment": {"python": sys.version.split()[0],
                        "platform": platform.platform()},
        "generated_at": _now(),
        "reviewer": getattr(ledger, "human_signoff", None) or "pending scientist sign-off",
        "recommendation_id": rec.get("hypothesis_id"),
        "sources": list(getattr(ledger, "sources", []) or []),
        "note": ("Deterministic numbers reproduce from graph_hash + seed. Claude "
                 "prose is drafted and versioned; it never sets a number. Retracted "
                 "sources are excluded from positive support."),
    }
    return json.dumps(manifest, indent=2)


def _protocol_md(domain, decision) -> str:
    rec = (decision or {}).get("recommendation") or {}
    if not rec:
        return f"# Draft protocol — {domain.upper()}\n\nNo recommendation available.\n"
    return "\n".join([
        f"# Draft protocol — {domain.upper()}",
        "",
        "> **Draft — requires scientist approval.** Generated by Keystone; every "
        "number is computed by the deterministic engine, not the model.",
        "",
        f"## Hypothesis to test\n{rec.get('statement', '—')}",
        "",
        f"## Why this experiment first\n{rec.get('why_first', '—')}",
        "",
        f"## Kill-condition — what result would falsify it\n{rec.get('how_to_falsify', '—')}",
        "",
        "## Computed parameters",
        f"- Expected information gain: {_num(rec.get('information_gain'))}",
        f"- Priority score: {_num(rec.get('priority_score'))}",
        f"- Risk: {rec.get('risk', '—')}",
        f"- Estimated cost (USD): {rec.get('cost_usd', '—')}",
        f"- Estimated duration (weeks): {rec.get('duration_weeks', '—')}",
        "",
        f"## Experiment\n{rec.get('experiment', '—')}",
        "",
    ])


def _readme(domain, ledger) -> str:
    return (f"# Keystone reproducibility bundle — {domain.upper()}\n\n"
            f"Question: {ledger.question}\n\n"
            f"Graph hash: `{ledger.graph_hash}` · seed `0x1f`\n\n"
            "## Files\n"
            "- `sources.csv` — every source record: id, verified, integrity state\n"
            "- `claims.json` — per-claim provenance (type, integrity, exact linkage)\n"
            "- `assessments.json` — conclusion-specific evidence status per claim\n"
            "- `graph.json` — the evidence graph (nodes + edges)\n"
            "- `dataset-manifest.json` — every dataset/paper the case rests on\n"
            "- `environment.txt` — python + package versions for reproducibility\n"
            "- `target-ranking.json` — the transparent 8-component regulator ranking (T-cell)\n"
            "- `run-manifest.json` — dataset/code/model/prompt/seed/run metadata\n"
            "- `experiment-plan.md` — the recommended next experiment as a draft, "
            "falsifiable protocol (scientist approval required)\n\n"
            "Reproduce: the deterministic numbers regenerate from the same graph hash "
            "and seed. Retracted sources resolve but are excluded from positive "
            "support. Nothing here is invented — every claim carries a resolvable "
            "identifier or is honestly marked `not available`.\n")


def _graph_json(graph) -> str:
    from keystone.artifacts.graph_export import graph_to_dict
    return json.dumps(graph_to_dict(graph), indent=2, default=str)


def _dataset_manifest(domain, graph) -> str:
    """Names every real dataset/paper the case rests on — id, version, peer-review
    and integrity state — so a reviewer can fetch and check each one."""
    datasets = [{"node_id": n.id, "kind": n.node_type.value, "source_id": n.source,
                 "title": n.text, "date": n.date or "not available",
                 "peer_reviewed": (n.meta or {}).get("peer_reviewed"),
                 "retracted": bool(getattr(n, "retracted", False)),
                 "integrity_note": (n.meta or {}).get("integrity_note")}
                for n in graph.nodes.values()
                if n.node_type.value in ("dataset", "paper")]
    return json.dumps({
        "domain": domain, "generated_at": _now(),
        "note": ("Every id is real and resolvable. Perturbation effects are the "
                 "published measurements (Literature-supported), not re-derived from "
                 "raw counts in this build; no trained model is used."),
        "datasets": datasets}, indent=2)


def _environment() -> str:
    """Environment capture for reproducibility (python + key package versions)."""
    import platform
    lines = [f"python={sys.version.split()[0]}", f"platform={platform.platform()}",
             f"generated_at={_now()}"]
    try:
        import importlib.metadata as md
        for pkg in ("anthropic", "fastapi", "uvicorn", "pydantic"):
            try:
                lines.append(f"{pkg}={md.version(pkg)}")
            except Exception:
                lines.append(f"{pkg}=not installed")
    except Exception:
        pass
    return "\n".join(lines) + "\n"


def build_repro_bundle(domain, graph, ledger, hyp, review,
                       decision, live_meta=None) -> dict:
    """Return ``{filename: text}`` for the whole bundle — the caller zips it."""
    live_meta = live_meta or {}
    files = {
        "README.md": _readme(domain, ledger),
        "sources.csv": _sources_csv(graph),
        "claims.json": _claims_json(graph),
        "assessments.json": _assessments_json(graph, hyp, review),
        "graph.json": _graph_json(graph),
        "dataset-manifest.json": _dataset_manifest(domain, graph),
        "environment.txt": _environment(),
        "run-manifest.json": _run_manifest(domain, ledger, decision, live_meta),
        "experiment-plan.md": _protocol_md(domain, decision),
    }
    # Target Trust: the transparent regulator ranking + its provenance.
    if domain == "tcell":
        from keystone.deterministic.target_ranking import rank_targets
        files["target-ranking.json"] = json.dumps(rank_targets(), indent=2)
        # Visual Evidence Lab: the Cell-State Atlas run receipt (arms + provenance,
        # without the full per-cell array — dataset/model/code/run metadata only).
        try:
            from keystone.ml.cell_atlas import compute_atlas
            a = compute_atlas(domain)
            files["atlas-run.json"] = json.dumps({
                "run_id": a["run_id"], "data_kind": a["data_kind"],
                "data_label": a["data_label"], "embedding": a["embedding"],
                "n_cells": a["n_cells"], "reproducibility": a["reproducibility"],
                "arms": a["arms"], "does_not_prove": a["does_not_prove"],
                "not_clinical": a["not_clinical"]}, indent=2)
        except Exception:
            pass
    return files
