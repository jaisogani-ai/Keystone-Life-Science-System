"""
keystone.reasoning_receipt
==========================
The auditable "who reasoned what" receipt for a discovery run.

Keystone's discovery loop produces a next-experiment recommendation. This module
makes the *provenance of that reasoning* legible in one artifact: which parts are
deterministic engine computation (and covered by the reproducibility hash), which
part is Fable 5 (Claude) advisory prose (recorded SEPARATELY, never hashed), and
the human sign-off that gates release.

Rule 7 is enforced structurally here: ``build_receipt`` computes NOTHING — it reads
the numbers straight off the deterministic run result. ``reasoning_narrative`` asks
Fable 5 only for plain-language prose over those fixed facts, and returns ``None``
offline or without a key, so the receipt degrades honestly to the deterministic
template. No number, ID, DOI, or hash is ever produced by the model.
"""
from __future__ import annotations

from typing import Optional

_DISCIPLINE = (
    "Every number above is computed by the deterministic engine and covered by "
    "the reproducibility hash; the reasoning prose is advisory, recorded "
    "separately, and never hashed; a human signs off before entry. "
    "AI proposes, scientists decide, experiments verify."
)


def reasoning_narrative(run_result: dict, reasoner) -> Optional[dict]:
    """Ask Fable 5 for a 2-3 sentence advisory narrative over the DETERMINISTIC
    recommendation. Returns ``None`` for the deterministic reasoner, offline, or
    on any failure — so the caller falls back to the engine's own statement. The
    model is given only fixed facts and may not invent a number or DOI."""
    if reasoner is None:
        return None
    # Only a live Claude-style reasoner carries a semantic client; the offline
    # HeuristicReasoner returns None here and the receipt stays deterministic.
    if not str(getattr(reasoner, "version", "")).startswith("claude"):
        return None
    complete = getattr(reasoner, "_complete_json", None)
    if complete is None:
        return None

    rec = run_result.get("recommendation", {}) or {}
    exp = rec.get("experiment", {}) or {}
    facts = {
        "recommended_experiment": rec.get("statement"),
        "priority_score": rec.get("priority_score"),
        "information_gain": rec.get("information_gain"),
        "n_per_arm": exp.get("n_per_arm"),
        "how_to_falsify": rec.get("how_to_falsify"),
        "contradictions_found": run_result.get("contradictions_found"),
    }
    try:
        out = complete(
            system=(
                "You are a translational scientist. In 2-3 plain sentences, "
                "explain WHY this is the right next experiment GIVEN the evidence. "
                "Use ONLY the facts provided — never invent a number, DOI, or "
                "result, and never restate a number I did not give you. Reply "
                'ONLY with JSON: {"narrative": str}. End with '
                '"AI proposes, scientists decide, experiments verify."'),
            user=str(facts), max_tokens=400)
    except Exception:
        return None
    if out and isinstance(out.get("narrative"), str) and out["narrative"].strip():
        return {"text": out["narrative"].strip(), "owner": "Fable 5 (Claude)"}
    return None


def build_receipt(run_result: dict, narrative: Optional[dict] = None) -> dict:
    """Structure a discovery run into an auditable reasoning receipt. Pure: reads
    numbers off ``run_result``, computes none. ``narrative`` (from
    ``reasoning_narrative``) is Fable 5's advisory prose when live, else ``None``
    and the receipt is honestly labelled a deterministic template."""
    rec = run_result.get("recommendation", {}) or {}
    exp = rec.get("experiment", {}) or {}
    illustrative = list(run_result.get("illustrative_dois", []) or [])
    reasoner_label = narrative["owner"] if narrative else "deterministic template"

    steps = [
        {
            "n": 1,
            "step": "Evidence in",
            "owner": "deterministic engine",
            "covered_by_hash": True,
            "detail": (
                f"{run_result.get('n_graph_hypotheses', 0)} graph hypothesis(es) "
                f"+ {run_result.get('n_literature_hypotheses', 0)} literature "
                f"contradiction(s), from "
                f"{run_result.get('contradictions_found', 0)} mined pair(s)"),
        },
        {
            "n": 2,
            "step": "Ranked & sized by the engine",
            "owner": "deterministic engine",
            "covered_by_hash": True,
            "facts": [
                {"name": "priority score", "value": rec.get("priority_score")},
                {"name": "information gain", "value": rec.get("information_gain")},
                {"name": "n per arm", "value": exp.get("n_per_arm")},
                {"name": "risk", "value": rec.get("risk")},
            ],
        },
        {
            "n": 3,
            "step": "Reasoning",
            "owner": reasoner_label,
            "covered_by_hash": False,
            "statement": rec.get("statement"),
            "why_first": rec.get("why_first"),
            "narrative": narrative["text"] if narrative else None,
            "note": ("Advisory prose — recorded separately from the "
                     "reproducibility hash."),
        },
        {
            "n": 4,
            "step": "Human sign-off",
            "owner": "principal investigator",
            "covered_by_hash": False,
            "status": "pending",
            "gate": "Release gated on principal-investigator sign-off before entry.",
        },
    ]

    return {
        "title": "Reasoning receipt",
        "run_hash": run_result.get("run_hash"),
        "graph_hash": run_result.get("graph_hash"),
        "reasoner": reasoner_label,
        "steps": steps,
        "provenance": {
            "n_illustrative": len(illustrative),
            "illustrative_dois": illustrative,
            "note": ("all grounding DOIs are real Crossref-resolvable records"
                     if not illustrative else
                     f"{len(illustrative)} illustrative DOI(s) badged — never "
                     f"shown as real"),
        },
        "discipline": _DISCIPLINE,
    }
