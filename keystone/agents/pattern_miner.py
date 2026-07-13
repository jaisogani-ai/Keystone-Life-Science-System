"""
keystone.agents.pattern_miner
=============================
Semantic wrapper around keystone.deterministic.pattern_mining. Runs the four
deterministic detectors first (Rule 7: engine owns every number), then
optionally narrates each PatternHit with a one-sentence Claude prose line
citing real DOIs. Offline (KEYSTONE_OFFLINE=1) or with no API key: falls
back to a deterministic template — the numbers stay identical.

Refusal boundary mirrors keystone.cv_lab: SUPPORTED scan types run; every
other scan_type gets a structured refusal, never a fabricated conclusion.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from keystone.deterministic.pattern_mining import (
    Corpus, PatternHit, PatternReport, build_corpus_from_openalex,
    corpus_provenance, run_scans,
)


# --- Scan-type catalogue (mirrors cv_lab.py SUPPORTED / REFUSED maps) -------
SUPPORTED = {
    "all":                  "run every supported detector on the corpus",
    "contradiction_scan":   "pair-wise contradiction detection with polarity + shared-target verification",
    "method_drift_scan":    "assay-keyword variance across time",
    "reagent_trend_scan":   "flagged cell-line / antibody trend per year",
    "consensus_scan":       "claim clustering weighted by citation count",
}

REFUSED = {
    "causal_inference": ("causal claims from observational literature "
                         "require intervention data; refused (a wrong "
                         "causal inference here misleads)."),
    "patient_outcome":  ("outcome prediction is a clinical decision-support "
                         "task; out of scope, refused."),
    "drug_efficacy":    ("efficacy prediction requires trial data; the "
                         "literature is not a randomised trial; refused."),
    "clinical_decision":("clinical decision support needs a validated "
                         "system + qualified investigator; refused."),
}


def scan_catalogue() -> list:
    """Every scan type with an honest status. UI renders this as the
    Literature Pattern Miner's boundary panel."""
    cat = [{"scan_type": k, "status": "supported", "detail": v}
           for k, v in SUPPORTED.items()]
    cat += [{"scan_type": k, "status": "refused", "detail": v}
            for k, v in REFUSED.items()]
    return cat


@dataclass(frozen=True)
class PatternReviewResult:
    report: PatternReport
    refused: bool = False
    reason: str = ""
    reasoner: str = "deterministic"   # 'claude' when live prose ran
    provenance: dict = None           # real vs illustrative DOI split

    def to_dict(self) -> dict:
        return {
            "report": self.report.to_dict(),
            "refused": self.refused,
            "reason": self.reason,
            "reasoner": self.reasoner,
            "provenance": self.provenance or {
                "n_real": 0, "n_illustrative": 0,
                "illustrative_dois": [], "note": ""},
        }


# --- Prose layer -----------------------------------------------------------
def _deterministic_prose(hit: PatternHit) -> str:
    """Fallback narration when Claude is offline or unavailable. Reads the
    numbers directly off the hit — no fabrication, no LLM."""
    return hit.summary


def _live_claude_prose(hit: PatternHit) -> Optional[str]:
    """One-sentence adversarial narration by Claude, citing at least one
    real DOI from hit.dois. Numbers and DOIs come from the hit — Claude only
    frames them for a PI. Returns None if Claude is unavailable so the
    caller can fall back safely."""
    if os.environ.get("KEYSTONE_OFFLINE") == "1":
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        from keystone.agents.claude_reasoner import ClaudeReasoner, DEFAULT_MODEL
        client = ClaudeReasoner().client
        doi_hint = hit.dois[0] if hit.dois else ""
        msg = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=180,
            system=("You are a scientific reviewer. In one sentence, "
                    "explain to a grant-writing PI why this pattern matters. "
                    "Cite the DOI given. Never invent numbers; use only the "
                    "values in the pattern summary."),
            messages=[{"role": "user", "content":
                       f"Pattern: {hit.kind}\n"
                       f"Summary (deterministic): {hit.summary}\n"
                       f"Real DOI to cite: {doi_hint}\n"
                       f"Citation methodology: {hit.citation}"}])
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        return text.strip() or None
    except Exception:
        return None


def _narrate(report: PatternReport) -> tuple:
    """Return (updated_hits, reasoner_flag)."""
    narrated = []
    used_claude = False
    for h in report.hits:
        prose = _live_claude_prose(h)
        if prose:
            used_claude = True
            # replace the deterministic summary with Claude's PI-facing prose,
            # keeping every other field (numbers, DOIs, citation) untouched
            narrated.append(PatternHit(
                kind=h.kind,
                severity=h.severity,
                summary=prose,
                dois=h.dois,
                detail=h.detail,
                citation=h.citation,
            ))
        else:
            narrated.append(h)
    return tuple(narrated), ("claude" if used_claude else "deterministic")


# --- Public entry ----------------------------------------------------------
def mine_patterns(records: list,
                  question: str = "",
                  seed_doi: str = "",
                  scan_type: str = "all") -> PatternReviewResult:
    """Run pattern mining on a corpus of OpenAlex-shaped records.

    records:    list of dicts with title / year / doi / cited_by_count keys
                (as returned by keystone.connectors.registry.openalex_*).
    question:   research question the corpus was fetched for.
    seed_doi:   optional seed DOI the search branched off from.
    scan_type:  one of SUPPORTED keys, else a refusal (or one of the REFUSED
                keys → structured refusal).
    """
    scan = (scan_type or "all").strip().lower()

    if scan in REFUSED:
        empty = PatternReport(corpus_size=len(records), hits=(),
                              question=question, seed_doi=seed_doi)
        return PatternReviewResult(
            report=empty, refused=True, reason=REFUSED[scan],
            reasoner="refused")

    if scan not in SUPPORTED:
        empty = PatternReport(corpus_size=len(records), hits=(),
                              question=question, seed_doi=seed_doi)
        return PatternReviewResult(
            report=empty, refused=True,
            reason=(f"unknown scan_type '{scan}'. Supported: "
                    f"{', '.join(SUPPORTED)}."),
            reasoner="refused")

    corpus = build_corpus_from_openalex(records, question=question,
                                         seed_doi=seed_doi)
    provenance = corpus_provenance(corpus)
    report = run_scans(corpus)

    # filter to a single scan when asked
    if scan != "all":
        keep_kind = {
            "contradiction_scan":  "contradiction_cluster",
            "method_drift_scan":   "method_drift",
            "reagent_trend_scan":  "reagent_trend",
            "consensus_scan":      "consensus_outlier",
        }[scan]
        report = PatternReport(
            corpus_size=report.corpus_size,
            hits=tuple(h for h in report.hits if h.kind == keep_kind),
            question=report.question,
            seed_doi=report.seed_doi,
        )

    narrated_hits, reasoner = _narrate(report)
    final = PatternReport(
        corpus_size=report.corpus_size,
        hits=narrated_hits,
        question=report.question,
        seed_doi=report.seed_doi,
    )
    return PatternReviewResult(report=final, reasoner=reasoner,
                               provenance=provenance)
