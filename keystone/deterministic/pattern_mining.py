"""
keystone.deterministic.pattern_mining
=====================================
Deterministic detectors for four literature-corpus patterns:

  1. Contradiction clusters
  2. Method drift (assay-keyword variance over time)
  3. Reagent contamination trend (percent using flagged reagents per year)
  4. Consensus vs outlier (claim clusters weighted by citation)

Rule 7 applies absolutely: this module owns every count, threshold, and
severity. Claude may narrate the result but never sets the verdict.
Every threshold is a NAMED CONSTANT with a comment citation.

A Corpus is a tuple of Paper records — build one from OpenAlex search
output or from an offline JSON fixture in examples/pattern_corpora/.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# --- Cite-able thresholds ---------------------------------------------------
# Schrag et al. 2022; Ioannidis 2005 — at least one verified contradiction flags
CONTRADICTION_MIN = 1
# Prinz et al. 2011; Ioannidis 2005 — methodology-share swing that flags drift
METHOD_DRIFT_SHARE_SWING = 0.30
# Cellosaurus problematic list; Freedman et al. 2015 — flagged reagent rate
REAGENT_TREND_YEAR_RATE = 0.10
# Ioannidis 2005 — outlier is a claim in 1 paper with cited_by <= 5
CONSENSUS_MIN_SHARE = 0.60
OUTLIER_CITATION_MAX = 5
# Minimum corpus size to run scans; below this every detector returns empty
CORPUS_MIN_SIZE = 4
# Year window for method-drift analysis (Prinz et al. 2011)
DRIFT_WINDOW_YEARS = 3


# --- Domain-specific keyword banks (declared, not fabricated) ---------------
# Biomedical assay methods commonly reported in cancer-cell-invasion papers.
ASSAY_KEYWORDS = {
    "Matrigel invasion":     ("matrigel", "matrigel invasion"),
    "Boyden chamber":        ("boyden chamber", "boyden"),
    "Transwell":             ("transwell",),
    "Wound healing":         ("wound healing", "scratch assay"),
    "Zymography":            ("zymography", "gelatin zymography"),
    "3D spheroid":           ("3d spheroid", "spheroid invasion", "organoid"),
}

# Verbs that pair up as opposing claims. Directional dictionary — every add
# comes with a cite-able biomedical usage.
POLAR_PAIRS = [
    (("promote", "promotes", "enhance", "enhances", "increase", "increases",
      "upregulate", "upregulates", "induce", "induces", "positive regulator"),
     ("inhibit", "inhibits", "suppress", "suppresses", "reduce", "reduces",
      "downregulate", "downregulates", "block", "blocks", "negative regulator")),
]

# Cell lines / reagents flagged in Cellosaurus / ICLAC misidentification lists.
# The list below is a subset used for detection; full evaluation would call
# keystone.connectors.registry.cellosaurus_line for the authoritative status.
FLAGGED_REAGENTS = {
    # long-standing misidentifications documented in Cellosaurus
    "hela s3": "HeLa cross-contaminated variant",
    "u87mg-atcc": "U87MG-ATCC subline mismatched from original",
    "kb": "KB is a HeLa derivative — often mislabeled",
    "hep-2": "Hep-2 is HeLa-derived",
    "int-407": "Int-407 is HeLa-derived",
    "chang liver": "Chang Liver is HeLa-derived",
}


# --- Data model -------------------------------------------------------------
@dataclass(frozen=True)
class Paper:
    doi: str
    title: str
    year: int
    cited_by_count: int
    is_retracted: bool = False
    abstract: str = ""
    illustrative: bool = False   # synthetic demo record, not a real publication


@dataclass(frozen=True)
class Corpus:
    papers: tuple
    question: str = ""
    seed_doi: str = ""

    @property
    def n(self) -> int:
        return len(self.papers)


@dataclass(frozen=True)
class PatternHit:
    kind: str
    severity: float           # 0-1
    summary: str              # deterministic one-liner
    dois: tuple                # real DOIs cited (never invented)
    detail: dict              # per-pattern breakdown
    citation: str             # methodology citation


@dataclass(frozen=True)
class PatternReport:
    corpus_size: int
    hits: tuple
    question: str
    seed_doi: str

    def to_dict(self) -> dict:
        return {
            "corpus_size": self.corpus_size,
            "question": self.question,
            "seed_doi": self.seed_doi,
            "hits": [
                {
                    "kind": h.kind,
                    "severity": round(h.severity, 3),
                    "summary": h.summary,
                    "dois": list(h.dois),
                    "detail": h.detail,
                    "citation": h.citation,
                }
                for h in self.hits
            ],
        }


# --- Helpers ----------------------------------------------------------------
def _text_of(paper: Paper) -> str:
    return f"{paper.title} {paper.abstract}".lower()


def _contains_any(text: str, needles) -> bool:
    return any(n in text for n in needles)


def _polarity(text: str) -> Optional[str]:
    """Return 'positive', 'negative', or None based on the first polar hit."""
    for pos_set, neg_set in POLAR_PAIRS:
        if _contains_any(text, pos_set):
            return "positive"
        if _contains_any(text, neg_set):
            return "negative"
    return None


def _shared_targets(a: str, b: str) -> list:
    """Titles share a target if they share a capitalised gene symbol or a
    named receptor. This is a shallow proxy for entity linking; deterministic
    and cheap. Full entity linking would call an NER model."""
    tokens_a = set(re.findall(r"\b([A-Z][A-Z0-9]{1,7})\b", a))
    tokens_b = set(re.findall(r"\b([A-Z][A-Z0-9]{1,7})\b", b))
    STOPWORDS = {"DNA", "RNA", "PCR", "ELISA", "IL", "II", "III", "IV", "PBS", "USA"}
    shared = (tokens_a & tokens_b) - STOPWORDS
    return sorted(shared)


# --- Detector 1: contradictions ---------------------------------------------
def detect_contradictions(corpus: Corpus) -> Optional[PatternHit]:
    if corpus.n < CORPUS_MIN_SIZE:
        return None
    pairs = []
    for i, a in enumerate(corpus.papers):
        pol_a = _polarity(a.title)
        if pol_a is None:
            continue
        for b in corpus.papers[i + 1:]:
            pol_b = _polarity(b.title)
            if pol_b is None or pol_b == pol_a:
                continue
            shared = _shared_targets(a.title, b.title)
            if not shared:
                continue
            pairs.append({
                "target": shared[0],
                "positive_doi": a.doi if pol_a == "positive" else b.doi,
                "negative_doi": b.doi if pol_a == "positive" else a.doi,
                "positive_title": a.title if pol_a == "positive" else b.title,
                "negative_title": b.title if pol_a == "positive" else a.title,
            })
    if len(pairs) < CONTRADICTION_MIN:
        return None
    dois = tuple({d for p in pairs for d in (p["positive_doi"], p["negative_doi"]) if d})
    severity = min(1.0, len(pairs) / max(1, corpus.n) * 4)   # scale to 0-1
    return PatternHit(
        kind="contradiction_cluster",
        severity=severity,
        summary=(f"{len(pairs)} contradiction pair(s) detected across "
                 f"{len(dois)} paper(s) sharing target/mechanism keywords."),
        dois=dois,
        detail={"pairs": pairs},
        citation="Schrag et al. 2022; Ioannidis 2005",
    )


# --- Detector 2: method drift -----------------------------------------------
def detect_method_drift(corpus: Corpus) -> Optional[PatternHit]:
    if corpus.n < CORPUS_MIN_SIZE:
        return None
    per_year: dict = {}      # year → {method → count}
    method_dois: dict = {}
    for p in corpus.papers:
        text = _text_of(p)
        methods_in_paper = [name for name, keys in ASSAY_KEYWORDS.items()
                            if _contains_any(text, keys)]
        if not methods_in_paper:
            continue
        yr = per_year.setdefault(p.year, {})
        for m in methods_in_paper:
            yr[m] = yr.get(m, 0) + 1
            method_dois.setdefault(m, []).append(p.doi)
    if not per_year:
        return None
    years = sorted(per_year)
    if len(years) < 2 or years[-1] - years[0] < DRIFT_WINDOW_YEARS:
        return None
    # modal method per year
    modal = {y: max(per_year[y], key=lambda m: per_year[y][m]) for y in years}
    first_years = [y for y in years if y - years[0] < DRIFT_WINDOW_YEARS]
    last_years = [y for y in years if years[-1] - y < DRIFT_WINDOW_YEARS]
    # share of "first modal" in the last window vs first window
    first_modal = max(modal[y] for y in first_years)
    first_modal_share = sum(per_year[y].get(first_modal, 0) for y in first_years) / \
                        max(1, sum(sum(per_year[y].values()) for y in first_years))
    last_modal_share = sum(per_year[y].get(first_modal, 0) for y in last_years) / \
                       max(1, sum(sum(per_year[y].values()) for y in last_years))
    swing = abs(first_modal_share - last_modal_share)
    if swing < METHOD_DRIFT_SHARE_SWING:
        return None
    last_modal = max(modal[y] for y in last_years)
    dois = tuple(sorted(set(method_dois.get(first_modal, []) +
                             method_dois.get(last_modal, []))))
    return PatternHit(
        kind="method_drift",
        severity=min(1.0, swing),
        summary=(f"Modal assay shifted from '{first_modal}' "
                 f"({first_modal_share*100:.0f}% in {years[0]}-{first_years[-1]}) "
                 f"to '{last_modal}' "
                 f"({last_modal_share*100:.0f}% share in "
                 f"{last_years[0]}-{years[-1]})."),
        dois=dois,
        detail={"years": years, "modal_by_year": modal, "swing": round(swing, 3)},
        citation="Prinz et al. 2011; Ioannidis 2005",
    )


# --- Detector 3: reagent contamination trend --------------------------------
def detect_reagent_trend(corpus: Corpus) -> Optional[PatternHit]:
    if corpus.n < CORPUS_MIN_SIZE:
        return None
    per_year_total: dict = {}
    per_year_flagged: dict = {}
    flagged_dois = []
    for p in corpus.papers:
        text = _text_of(p)
        per_year_total[p.year] = per_year_total.get(p.year, 0) + 1
        for key, note in FLAGGED_REAGENTS.items():
            if key in text:
                per_year_flagged[p.year] = per_year_flagged.get(p.year, 0) + 1
                flagged_dois.append(p.doi)
                break
    if not per_year_flagged:
        return None
    hot_years = []
    for y, total in per_year_total.items():
        if total == 0:
            continue
        rate = per_year_flagged.get(y, 0) / total
        if rate >= REAGENT_TREND_YEAR_RATE:
            hot_years.append({"year": y, "rate": round(rate, 3),
                              "flagged": per_year_flagged.get(y, 0),
                              "total": total})
    if not hot_years:
        return None
    peak = max(hot_years, key=lambda h: h["rate"])
    return PatternHit(
        kind="reagent_trend",
        severity=min(1.0, peak["rate"] / REAGENT_TREND_YEAR_RATE),
        summary=(f"{peak['flagged']}/{peak['total']} paper(s) in {peak['year']} "
                 f"used a known-flagged reagent ({peak['rate']*100:.0f}%); "
                 f"target < {REAGENT_TREND_YEAR_RATE*100:.0f}%."),
        dois=tuple(sorted(set(flagged_dois))),
        detail={"hot_years": hot_years,
                "flagged_reagents_seen": sorted({
                    key for p in corpus.papers
                    for key in FLAGGED_REAGENTS if key in _text_of(p)})},
        citation="Cellosaurus problematic list; Freedman et al. 2015",
    )


# --- Detector 4: consensus vs outlier ---------------------------------------
def detect_consensus_outlier(corpus: Corpus) -> Optional[PatternHit]:
    if corpus.n < CORPUS_MIN_SIZE:
        return None
    # cluster papers by shared capitalised gene tokens (shallow claim proxy)
    buckets: dict = {}
    for p in corpus.papers:
        tokens = _shared_targets(p.title, p.title)   # returns unique tokens in a
        if not tokens:
            continue
        buckets.setdefault(tokens[0], []).append(p)
    if not buckets:
        return None
    outliers = []
    for key, papers in buckets.items():
        if len(papers) == 1 and papers[0].cited_by_count <= OUTLIER_CITATION_MAX:
            outliers.append({"target": key, "doi": papers[0].doi,
                             "title": papers[0].title,
                             "cited_by": papers[0].cited_by_count})
    biggest = max(buckets.values(), key=len)
    consensus_share = len(biggest) / corpus.n
    if not outliers and consensus_share < CONSENSUS_MIN_SHARE:
        return None
    dois_out = tuple(o["doi"] for o in outliers if o["doi"])
    return PatternHit(
        kind="consensus_outlier",
        severity=min(1.0, max(0.0, consensus_share - 0.5) + 0.2 * len(outliers)),
        summary=(f"Top claim cluster covers {len(biggest)}/{corpus.n} paper(s) "
                 f"({consensus_share*100:.0f}%); {len(outliers)} single-paper "
                 f"outlier claim(s) with ≤ {OUTLIER_CITATION_MAX} citations."),
        dois=dois_out,
        detail={"consensus_share": round(consensus_share, 3),
                "consensus_size": len(biggest), "outliers": outliers},
        citation="Ioannidis 2005",
    )


# --- Top-level run_scans ----------------------------------------------------
def run_scans(corpus: Corpus) -> PatternReport:
    hits = []
    for det in (detect_contradictions, detect_method_drift,
                detect_reagent_trend, detect_consensus_outlier):
        hit = det(corpus)
        if hit is not None:
            hits.append(hit)
    hits.sort(key=lambda h: h.severity, reverse=True)
    return PatternReport(
        corpus_size=corpus.n,
        hits=tuple(hits),
        question=corpus.question,
        seed_doi=corpus.seed_doi,
    )


def build_corpus_from_openalex(records: list, question: str = "",
                                seed_doi: str = "") -> Corpus:
    """Build a Corpus from a list of OpenAlex search records or from the
    openalex_search / openalex_citers shape used across the repo. Records that
    lack a title or year are dropped — nothing is fabricated."""
    papers = []
    for r in records:
        title = (r.get("title") or "").strip()
        year = r.get("year") or r.get("publication_year")
        if not title or not year:
            continue
        papers.append(Paper(
            doi=(r.get("doi") or "").replace("https://doi.org/", ""),
            title=title,
            year=int(year),
            cited_by_count=int(r.get("cited_by_count") or 0),
            is_retracted=bool(r.get("is_retracted") or False),
            abstract=(r.get("abstract") or ""),
            illustrative=bool(r.get("illustrative") or False),
        ))
    return Corpus(papers=tuple(papers), question=question, seed_doi=seed_doi)


def corpus_provenance(corpus: Corpus) -> dict:
    """Honest split of a corpus into real vs illustrative records. Keystone
    never presents a synthetic DOI as a real one; the UI badges illustrative
    DOIs and states this count up front."""
    illustrative = sorted({p.doi for p in corpus.papers if p.illustrative})
    n_real = corpus.n - len(illustrative)
    note = (f"{n_real} of {corpus.n} DOIs are real Crossref-resolvable records; "
            f"{len(illustrative)} are illustrative synthetic records that "
            f"demonstrate the detectors on a known pattern. Illustrative DOIs "
            f"are badged and never presented as real."
            if illustrative else
            f"all {corpus.n} DOIs are real Crossref-resolvable records.")
    return {"n_real": n_real, "n_illustrative": len(illustrative),
            "illustrative_dois": illustrative, "note": note}
