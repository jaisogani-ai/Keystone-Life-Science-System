"""
keystone.agents.bench_reviewer
=============================
The Laboratory Agent's review layer. It ingests bench-instrument output
(96-well plate reader CSV), runs deterministic QC (keystone.deterministic
.bench_qc), and returns a Reviewer verdict that downgrades confidence when
the data fails QC — the same self-challenge Keystone's literature Reviewer
applies, now on experimental data. Multiple plates aggregate into one
operational report.

Rule 7 is absolute: the deterministic layer owns every number AND the
verdict. Claude only narrates the weakness in prose. The refusal boundary
mirrors keystone.cv_lab — instrument formats without a validated
interpretation model are refused, never guessed.

Honest scope: this is NOT "connect every instrument and self-learn." It
reads one validated file format (plate-reader CSV), applies cite-able QC
thresholds, and refuses the rest on the record. That boundary is the
reason a lab could trust it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from keystone.core import Interval, ReviewVerdict
from keystone.deterministic.bench_qc import parse_csv, run_qc


# --- policy constants -------------------------------------------------------
BASE_CONFIDENCE = 0.55          # a result's prior confidence before QC
DOWNGRADE_STEP = 0.20           # one failed check removes this much
HARD_BREACH_SEVERITY = 1.0      # value >= 2x past threshold (relative) -> reject


# --- supported / refused instrument formats (mirror cv_lab.py) --------------
SUPPORTED = {
    "plate_reader_csv": "96-well plate reader CSV (Bio-Rad / generic ELISA)",
}
REFUSED = {
    "western_blot":      "band densitometry needs a validated model + loading "
                         "controls; refused (a wrong number here misleads).",
    "microscopy_image":  "cell/particle measurement needs a validated per-"
                         "modality model + ground truth; refused.",
    "cryoem_map":        "CryoEM (.mrc/.map) has no wired source and no "
                         "validated interpretation model; refused.",
    "flow_cytometry_fcs":"FCS gating needs expert-defined gates + "
                         "compensation; refused.",
    "sequencing_fastq":  "read-quality interpretation needs a validated "
                         "pipeline (FastQC/MultiQC); refused here.",
}

# workflow fixes keyed by the deterministic QC check that failed — the
# "self-correcting" suggestion, grounded in which check breached (not ML).
SUGGESTIONS = {
    "standard_curve_r2": "Re-run the standard curve with fresh calibrators; "
                         "verify the dilution-series pipetting and check for a "
                         "saturated top standard.",
    "replicate_cv":      "Increase replicate count and check pipette "
                         "calibration; high CV usually traces to tip-loading "
                         "or edge evaporation.",
    "edge_effect":       "Randomise plate layout or add edge-well controls; a "
                         "humidified incubation reduces evaporation-driven edge "
                         "bias.",
    "missing_wells":     "Check the flagged wells for read errors, bubbles, or "
                         "evaporation before quantifying.",
}


def format_catalogue() -> list:
    """Every instrument format with an honest status — supported or refused
    (with the reason). The Laboratory Agent's safety boundary."""
    cat = [{"format": k, "status": "supported", "detail": v}
           for k, v in SUPPORTED.items()]
    cat += [{"format": k, "status": "refused", "detail": v}
            for k, v in REFUSED.items()]
    return cat


@dataclass(frozen=True)
class BenchReviewResult:
    label: str
    verdict: str                     # supported | downgraded | rejected | refused
    weakness: str
    adjusted_confidence: dict        # {point, low, high}
    base_confidence: float
    objections: list = field(default_factory=list)
    qc_metrics: list = field(default_factory=list)   # every check as a dict
    suggestions: list = field(default_factory=list)
    refused: bool = False
    reason: str = ""
    reasoner: str = "deterministic"

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "verdict": self.verdict,
            "weakness": self.weakness,
            "adjusted_confidence": self.adjusted_confidence,
            "base_confidence": self.base_confidence,
            "objections": self.objections,
            "qc_metrics": self.qc_metrics,
            "suggestions": self.suggestions,
            "refused": self.refused,
            "reason": self.reason,
            "reasoner": self.reasoner,
        }


def _verdict(checks, base):
    breached = [c for c in checks if c.breached]
    hard = [c for c in breached if c.breach_severity >= HARD_BREACH_SEVERITY]
    if hard:
        adj = max(0.0, base - 2 * DOWNGRADE_STEP)
        return ReviewVerdict.REJECTED, adj, breached
    if breached:
        adj = max(0.0, base - DOWNGRADE_STEP)
        return ReviewVerdict.DOWNGRADED, adj, breached
    return ReviewVerdict.SUPPORTED, base, breached


def _interval(point: float) -> dict:
    iv = Interval(round(point, 3), round(max(0.0, point - 0.1), 3),
                  round(min(1.0, point + 0.1), 3))
    return {"point": iv.point, "low": iv.low, "high": iv.high}


def _deterministic_weakness(verdict: ReviewVerdict, breached: list) -> str:
    if verdict is ReviewVerdict.SUPPORTED:
        return "No QC check breached; the plate supports quantification."
    names = ", ".join(c.name.replace("_", " ") for c in breached)
    lead = ("Data is rejected" if verdict is ReviewVerdict.REJECTED
            else "Confidence is downgraded")
    return (f"{lead}: {len(breached)} QC check(s) breached ({names}). "
            f"Any hypothesis grounded on this plate inherits that doubt.")


def _live_weakness(verdict, breached) -> str | None:
    """One-sentence Claude critique. Numbers come from the checks — Claude
    only frames them for a scientist. None → caller falls back."""
    if os.environ.get("KEYSTONE_OFFLINE") == "1":
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        from keystone.agents.claude_reasoner import ClaudeReasoner, DEFAULT_MODEL
        client = ClaudeReasoner().client
        detail = "; ".join(f"{c.name}: {c.detail}" for c in breached) or "none"
        msg = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=180,
            system=("You are an adversarial bench-data reviewer. In one "
                    "sentence, tell a scientist why this plate's QC result "
                    "should change their confidence. Use ONLY the numbers "
                    "given; never invent a value."),
            messages=[{"role": "user", "content":
                       f"Verdict: {verdict.value}\nBreached checks: {detail}"}])
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        return text.strip() or None
    except Exception:
        return None


def review_plate(csv_text: str, label: str = "plate",
                 fmt: str = "plate_reader_csv",
                 base_confidence: float = BASE_CONFIDENCE) -> BenchReviewResult:
    """Review one bench-data file. Refuses unsupported formats with a
    structured explanation; never fabricates a reading."""
    fmt = (fmt or "plate_reader_csv").strip().lower()

    if fmt in REFUSED:
        return BenchReviewResult(
            label=label, verdict="refused", weakness=REFUSED[fmt],
            adjusted_confidence=_interval(0.0), base_confidence=base_confidence,
            refused=True, reason=REFUSED[fmt], reasoner="refused")
    if fmt not in SUPPORTED:
        reason = (f"unknown format '{fmt}'. Supported: {', '.join(SUPPORTED)}. "
                  f"All measurement-extraction formats without a validated "
                  f"model are refused by policy.")
        return BenchReviewResult(
            label=label, verdict="refused", weakness=reason,
            adjusted_confidence=_interval(0.0), base_confidence=base_confidence,
            refused=True, reason=reason, reasoner="refused")

    plate = parse_csv(csv_text)
    checks = run_qc(plate)
    verdict, adj, breached = _verdict(checks, base_confidence)

    weakness = _live_weakness(verdict, breached)
    reasoner = "claude" if weakness else "deterministic"
    if not weakness:
        weakness = _deterministic_weakness(verdict, breached)

    return BenchReviewResult(
        label=label,
        verdict=verdict.value,
        weakness=weakness,
        adjusted_confidence=_interval(adj),
        base_confidence=base_confidence,
        objections=[c.detail for c in breached],
        qc_metrics=[{
            "name": c.name, "value": c.value, "threshold": c.threshold,
            "breached": c.breached, "severity": round(c.breach_severity, 3),
            "detail": c.detail, "citation": c.citation,
        } for c in checks],
        suggestions=[SUGGESTIONS[c.name] for c in breached
                     if c.name in SUGGESTIONS],
        reasoner=reasoner,
    )


def review_batch(files: list) -> dict:
    """Aggregate multiple plate files into one operational report. `files` is
    a list of {name, csv_text, format?} dicts. Every plate is reviewed
    independently; the report rolls up the verdict counts and the worst
    verdict across the batch."""
    reviews = []
    for f in files or []:
        r = review_plate(
            f.get("csv_text", ""),
            label=f.get("name", "plate"),
            fmt=f.get("format", "plate_reader_csv"))
        reviews.append(r.to_dict())

    counts = {"supported": 0, "downgraded": 0, "rejected": 0, "refused": 0}
    for r in reviews:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    # worst verdict across the batch — the operational headline
    order = ["supported", "downgraded", "rejected", "refused"]
    worst = "supported"
    for r in reviews:
        if order.index(r["verdict"]) > order.index(worst):
            worst = r["verdict"]

    return {
        "n_plates": len(reviews),
        "counts": counts,
        "worst_verdict": worst,
        "operational_headline": _headline(len(reviews), counts, worst),
        "reviews": reviews,
    }


def _headline(n: int, counts: dict, worst: str) -> str:
    if n == 0:
        return "No plates submitted."
    ok = counts.get("supported", 0)
    bad = counts.get("downgraded", 0) + counts.get("rejected", 0)
    ref = counts.get("refused", 0)
    parts = [f"{n} plate(s) reviewed", f"{ok} passed QC"]
    if bad:
        parts.append(f"{bad} downgraded/rejected")
    if ref:
        parts.append(f"{ref} refused (unsupported format)")
    return " · ".join(parts)
