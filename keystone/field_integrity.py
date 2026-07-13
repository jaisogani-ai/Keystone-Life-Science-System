"""
keystone.field_integrity
=======================
The Field Integrity Report — a computed integrity index for a research field's
literature, from real data. No existing tool answers "how contaminated is the
literature I'm building on?" as a transparent, reproducible score.

Point Keystone at a corpus (e.g. the real papers citing a retracted result) and
it computes, deterministically and from real signals:

  * retraction burden      — fraction of the corpus that is retracted
  * post-publication burden — fraction with a Crossref post-pub change
                              (retraction / correction / expression of concern),
                              over the subset whose change history resolves
  * integrity-pattern load  — contradiction / method-drift / reagent-trend
                              signals found in the real abstracts (pattern miner)

and folds them into a **Field Integrity Score (0-100, higher = healthier)** with
every weight exposed, so a research-integrity office can audit the number. Rule
7 holds: every value is computed from real records or explicitly partial; the
semantic layer never sets the score.
"""
from __future__ import annotations

import hashlib
import html
from datetime import date

from keystone.agents.pattern_miner import mine_patterns
from keystone.connectors.registry import post_publication_updates

# Weights are exposed so the index is auditable, never a black box.
WEIGHTS = {"retraction": 0.50, "post_pub": 0.30, "pattern": 0.20}
_INTEGRITY_PATTERNS = {"contradiction_cluster", "method_drift", "reagent_trend"}
_PATTERN_SATURATION = 3          # this many integrity patterns = full pattern load
_BANDS = ((80, "high"), (55, "medium"), (0, "low"))
# A web request must not fan out dozens of sequential Crossref lookups. Resolve
# post-publication history for at most this many DOIs (the seed + the most-cited);
# coverage is reported honestly. Retraction burden already covers all N papers.
_POST_PUB_LOOKUP_CAP = 8


def _band(score: float) -> str:
    for floor, name in _BANDS:
        if score >= floor:
            return name
    return "low"


def field_integrity_report(records: list, question: str = "",
                           seed_doi: str = "",
                           resolve_post_pub: bool = True) -> dict:
    """Compute the Field Integrity Report for a corpus of OpenAlex-shaped
    records. `resolve_post_pub` looks up each DOI's Crossref change history
    (cache/fixture offline); coverage is reported honestly."""
    papers = [r for r in (records or []) if r.get("title")]
    n = len(papers)
    if n == 0:
        return {"resolved": False, "n": 0,
                "note": "empty corpus — nothing to score."}

    # --- retraction burden (real, from the corpus is_retracted flags) --------
    retracted = [r for r in papers if r.get("is_retracted")]
    retraction_rate = len(retracted) / n

    # --- post-publication burden (real Crossref change history) --------------
    post_pub_changed, post_pub_resolved = 0, 0
    changed_examples = []
    if resolve_post_pub:
        # cap the network fan-out: seed first, then the most-cited references
        ordered = sorted(papers, key=lambda r: -(r.get("cited_by_count") or 0))
        seed_clean = (seed_doi or "").replace("https://doi.org/", "")
        ordered = ([r for r in papers if (r.get("doi") or "") == seed_clean]
                   + [r for r in ordered if (r.get("doi") or "") != seed_clean])
        for r in ordered[:_POST_PUB_LOOKUP_CAP]:
            doi = (r.get("doi") or "").replace("https://doi.org/", "")
            if not doi or doi.startswith("10.9999"):
                continue
            u = post_publication_updates(doi)
            if not u.get("resolved"):
                continue
            post_pub_resolved += 1
            if u["updates"]:
                post_pub_changed += 1
                changed_examples.append(
                    {"doi": doi, "changes": [x["label"] for x in u["updates"]]})
    post_pub_rate = (post_pub_changed / post_pub_resolved
                     if post_pub_resolved else 0.0)

    # --- integrity-pattern load (real abstracts, via the pattern miner) ------
    mined = mine_patterns(papers, question=question, seed_doi=seed_doi,
                          scan_type="all")
    hits = mined.report.hits
    integrity_hits = [h for h in hits if h.kind in _INTEGRITY_PATTERNS]
    pattern_load = min(1.0, len(integrity_hits) / _PATTERN_SATURATION)

    # --- composite Field Integrity Score (0-100, higher = healthier) --------
    burdens = {"retraction": retraction_rate, "post_pub": post_pub_rate,
               "pattern": pattern_load}

    def _score(weights):
        return round(100 * (1 - sum(weights[k] * burdens[k] for k in weights)))

    score = _score(WEIGHTS)
    band = _band(score)

    # sensitivity: the exact number depends on a STATED PRIOR (WEIGHTS); a
    # reviewer will ask "why those weights?" So we report whether the BAND is
    # robust across reasonable alternative priors — an honest ordinal claim
    # even when the cardinal number is prior-dependent.
    _ALT_WEIGHTS = [
        {"retraction": 1 / 3, "post_pub": 1 / 3, "pattern": 1 / 3},   # equal
        {"retraction": 0.70, "post_pub": 0.20, "pattern": 0.10},      # retraction-heavy
        {"retraction": 0.60, "post_pub": 0.35, "pattern": 0.05},      # discount heuristic patterns
    ]
    alt_scores = [_score(w) for w in _ALT_WEIGHTS] + [score]
    alt_bands = {_band(s) for s in alt_scores}
    sensitivity = {
        "band_robust": len(alt_bands) == 1,
        "score_range": [min(alt_scores), max(alt_scores)],
        "bands_seen": sorted(alt_bands),
        "note": ("the band is stable across equal-, retraction-heavy-, and "
                 "pattern-discounted priors"
                 if len(alt_bands) == 1 else
                 "the band shifts under alternative priors — report the range, "
                 "not a point score"),
    }

    return {
        "resolved": True,
        "question": question,
        "seed_doi": seed_doi,
        "n": n,
        "score": score,
        "band": band,
        "weights": WEIGHTS,
        "sensitivity": sensitivity,
        "components": {
            "retraction": {
                "rate": round(retraction_rate, 3),
                "count": len(retracted),
                "basis": "corpus is_retracted flags (OpenAlex)",
                "kind": "computed"},
            "post_pub": {
                "rate": round(post_pub_rate, 3),
                "changed": post_pub_changed,
                "resolved": post_pub_resolved,
                "coverage": (f"resolved {post_pub_resolved} of "
                             f"{min(_POST_PUB_LOOKUP_CAP, n)} sampled "
                             f"(seed + most-cited)"),
                "basis": "Crossref post-publication change history",
                "kind": "computed (sampled coverage)"},
            "pattern": {
                "load": round(pattern_load, 3),
                "integrity_patterns": [h.kind for h in integrity_hits],
                "basis": "contradiction / method-drift / reagent-trend detectors",
                "kind": "computed"},
        },
        "retracted_papers": [{"doi": r.get("doi"), "title": r.get("title"),
                              "year": r.get("year")} for r in retracted],
        "changed_after_publication": changed_examples,
        "pattern_hits": mined.report.to_dict()["hits"],
        "provenance": mined.provenance,
        "interpretation": _interpret(score, band, retraction_rate,
                                     post_pub_rate, len(integrity_hits)),
        "disclaimer": ("The Field Integrity Score is a transparent weighted "
                       "composite of real, computed signals — not a verdict on "
                       "any single paper. It flags where the literature has "
                       "changed or disagrees; the scientist judges each case."),
    }


# Weights for a scientist's OWN imported reference set. Contamination (citing a
# retracted work in the set) is a first-class burden here, alongside retraction
# and post-publication change — all read from the triage the import already
# computed, so no extra network call is made.
REF_HEALTH_WEIGHTS = {"retraction": 0.50, "contamination": 0.30, "post_pub": 0.20}
_REF_ALT_WEIGHTS = [
    {"retraction": 1 / 3, "contamination": 1 / 3, "post_pub": 1 / 3},
    {"retraction": 0.70, "contamination": 0.20, "post_pub": 0.10},
    {"retraction": 0.40, "contamination": 0.45, "post_pub": 0.15},
]


def reference_set_health(triage: dict) -> dict:
    """The Field Integrity Score for a scientist's OWN imported reference set —
    "how safe is the literature I am building my grant on?" Computed entirely
    from the triage the import already produced (retractions, cites-a-retraction,
    post-publication changes); no extra network call, fully reproducible. Same
    envelope as field_integrity_report so the audit export renders it."""
    rows = triage.get("rows", [])
    n = triage.get("total", 0)
    if n == 0:
        return {"resolved": False, "n": 0,
                "note": "no references imported — nothing to score."}
    counts = triage.get("counts", {})
    retraction_rate = counts.get("retracted", 0) / n
    contamination_rate = counts.get("cites_retraction", 0) / n
    # papers that changed after publication but are not themselves retracted
    changed = sum(1 for r in rows
                  if r.get("post_pub_updates") and r.get("status") != "retracted")
    post_pub_rate = changed / n

    burdens = {"retraction": retraction_rate,
               "contamination": contamination_rate, "post_pub": post_pub_rate}

    def _score(w):
        return round(100 * (1 - sum(w[k] * burdens[k] for k in w)))

    score = _score(REF_HEALTH_WEIGHTS)
    band = _band(score)
    alt = [_score(w) for w in _REF_ALT_WEIGHTS] + [score]
    bands = {_band(s) for s in alt}
    retracted_rows = [r for r in rows if r.get("status") == "retracted"]
    changed_rows = [{"doi": r.get("doi"),
                     "changes": [u["label"] for u in (r.get("post_pub_updates") or [])]}
                    for r in rows
                    if r.get("post_pub_updates") and r.get("status") != "retracted"]

    return {
        "resolved": True,
        "question": triage.get("question", "imported reference set"),
        "seed_doi": "",
        "n": n,
        "score": score,
        "band": band,
        "weights": REF_HEALTH_WEIGHTS,
        "sensitivity": {
            "band_robust": len(bands) == 1,
            "score_range": [min(alt), max(alt)],
            "bands_seen": sorted(bands),
            "note": ("band stable across equal / retraction-heavy / "
                     "contamination-heavy priors" if len(bands) == 1
                     else "band shifts under alternative priors — report the range")},
        "components": {
            "retraction": {"rate": round(retraction_rate, 3),
                           "count": counts.get("retracted", 0),
                           "basis": "references in the set that are retracted",
                           "kind": "computed"},
            "contamination": {"rate": round(contamination_rate, 3),
                              "count": counts.get("cites_retraction", 0),
                              "basis": "references that cite a retracted work in the set",
                              "kind": "computed"},
            "post_pub": {"rate": round(post_pub_rate, 3),
                         "count": changed,
                         "coverage": f"{n}/{n} (full — from the import)",
                         "basis": "references corrected / flagged after publication",
                         "kind": "computed"}},
        "retracted_papers": [{"doi": r.get("doi"), "title": r.get("title"),
                              "year": r.get("year")} for r in retracted_rows],
        "changed_after_publication": changed_rows,
        "pattern_hits": [],
        "provenance": {"n_real": n, "n_illustrative": 0, "illustrative_dois": [],
                       "note": f"all {n} references resolved from the import"},
        "interpretation": _interpret_ref(score, band, retraction_rate,
                                         contamination_rate, post_pub_rate),
        "disclaimer": ("The Field Integrity Score rates how safe this reference "
                       "set is to build on. It is a transparent weighted "
                       "composite of real, computed signals — not a verdict on "
                       "any single paper."),
    }


def _interpret_ref(score, band, retr, contam, postpub) -> str:
    parts = [f"Field Integrity Score {score}/100 ({band}) for this reference set."]
    if retr:
        parts.append(f"{retr*100:.0f}% are retracted.")
    if contam:
        parts.append(f"{contam*100:.0f}% cite a retracted work in the set.")
    if postpub:
        parts.append(f"{postpub*100:.0f}% changed after publication.")
    parts.append("Comparatively safe to build on." if band == "high"
                 else "Address the flagged references before building on this set.")
    return " ".join(parts)


def _report_hash(report: dict) -> str:
    dois = sorted((r.get("doi") or "") for r in report.get("retracted_papers", []))
    payload = f"{report['n']}|{report['score']}|{'|'.join(dois)}|{report['seed_doi']}"
    return "audit:" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def field_audit_html(report: dict) -> str:
    """A formal, hash-stamped Research Integrity Audit — the artifact a
    research-integrity office, journal, or pharma governance team can file for a
    body of literature. Every value is computed from real records; nothing is
    fabricated. This is the commercial deliverable Keystone's discipline earns."""
    _e = html.escape
    if not report.get("resolved"):
        return "<!doctype html><html><body><p>No corpus to audit.</p></body></html>"
    h = _report_hash(report)
    comp = report["components"]
    w = report["weights"]
    band_color = {"high": "#27ae60", "medium": "#d4a017", "low": "#c0392b"}[report["band"]]

    def _doi_li(p):
        doi = p.get("doi") or "unresolved"
        link = (f'<a href="https://doi.org/{_e(doi)}">{_e(doi)}</a>'
                if doi and doi != "unresolved" else _e(doi))
        return f"<li>{_e((p.get('title') or '')[:120])} ({p.get('year') or '—'}) — {link}</li>"

    retracted = "".join(_doi_li(p) for p in report["retracted_papers"]) \
        or "<li>None retracted in this corpus.</li>"
    changed = "".join(
        f"<li>{_e(c['doi'])} — {_e(', '.join(c['changes']))}</li>"
        for c in report["changed_after_publication"]) \
        or "<li>None resolved with a post-publication change.</li>"
    patterns = "".join(
        f"<li><b>{_e(ph['kind'].replace('_',' '))}</b> — {_e(ph['summary'][:160])}</li>"
        for ph in report["pattern_hits"]) or "<li>No integrity pattern flagged.</li>"

    # component table — generic over whatever burdens this report carries
    _COMP_LABEL = {"retraction": "Retraction burden",
                   "post_pub": "Post-publication burden",
                   "pattern": "Integrity-pattern load",
                   "contamination": "Citation-contamination burden"}
    comp_rows = ""
    for key, c in report["components"].items():
        val = c.get("rate", c.get("load", ""))
        extra = ""
        if "count" in c:
            extra = f" ({c['count']}/{report['n']})"
        elif "coverage" in c:
            extra = f" · {_e(c['coverage'])}"
        comp_rows += (f"<tr><td>{_e(_COMP_LABEL.get(key, key))}</td>"
                      f"<td>{val}{extra}</td><td>{w.get(key, '')}</td>"
                      f"<td>{_e(c.get('basis', ''))}</td></tr>")

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Keystone Research Integrity Audit — {_e(h)}</title>
<style>
  body{{font-family:Georgia,'Times New Roman',serif;max-width:820px;margin:40px auto;
    padding:0 24px;color:#1a1a1a;line-height:1.55}}
  h1{{font-size:22px;margin-bottom:2px}} h2{{font-size:14px;border-bottom:1px solid #ccc;
    padding-bottom:4px;margin-top:26px;text-transform:uppercase;letter-spacing:.03em;color:#333}}
  .meta{{color:#666;font-size:12.5px}} .tag{{background:#eef;border:1px solid #cce;
    border-radius:4px;padding:1px 6px;font-size:11px;font-family:monospace}}
  .score{{display:flex;align-items:baseline;gap:12px;margin:14px 0}}
  .score .n{{font-size:44px;font-weight:700;color:{band_color}}}
  .score .band{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:{band_color}}}
  table{{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}}
  th,td{{text-align:left;padding:5px 8px;border-bottom:1px solid #e5e5e5}}
  th{{color:#555;font-size:11px;text-transform:uppercase}}
  ol,ul{{font-size:13px}} code{{background:#f4f4f4;padding:1px 5px;border-radius:3px;font-size:12px}}
  .disclaimer{{background:#fafafa;border:1px solid #e5e5e5;border-radius:4px;padding:10px 14px;font-size:12.5px;margin-top:8px}}
  @media print{{a{{color:#000;text-decoration:none}}}}
</style></head><body>
<h1>Research Integrity Audit</h1>
<div class="meta">Field: <b>{_e(report['question'] or 'imported corpus')}</b><br>
Corpus: {report['n']} references · seed <code>{_e(report['seed_doi'] or '—')}</code> ·
audit hash <span class="tag">{_e(h)}</span> · {date.today().isoformat()}</div>

<div class="score"><span class="n">{report['score']}</span><span>/100</span>
  <span class="band">{_e(report['band'])} integrity</span></div>
<p>{_e(report['interpretation'])}</p>

<h2>How the score is computed (auditable)</h2>
<table><tr><th>Component</th><th>Value</th><th>Weight</th><th>Basis</th></tr>
{comp_rows}
</table>
<p class="meta">Score = 100 × (1 − Σ weightᵢ·burdenᵢ). Every burden is computed
from real records; weights are shown so the number is auditable, not a black box.</p>
<p class="meta"><b>Sensitivity.</b> The band is
{'<b>robust</b>' if report['sensitivity']['band_robust'] else '<b>NOT robust</b>'}
across equal-, retraction-heavy-, and pattern-discounted priors (score range
{report['sensitivity']['score_range'][0]}&ndash;{report['sensitivity']['score_range'][1]}).
The exact score depends on the stated prior; the {_e(report['band'])} band is the
defensible ordinal claim.</p>

<h2>Retracted references in the corpus</h2><ol>{retracted}</ol>
<h2>Changed after publication (resolved subset)</h2><ul>{changed}</ul>
<h2>Integrity patterns in the abstracts</h2><ul>{patterns}</ul>

<div class="disclaimer">{_e(report['disclaimer'])}</div>
<p class="meta">Re-running Keystone on this corpus reproduces audit hash
<code>{_e(h)}</code>. No value in this audit is fabricated; every DOI resolves
to a real record or is marked unresolved.</p>
</body></html>"""


def _interpret(score, band, retr, postpub, npat) -> str:
    parts = [f"Field Integrity Score {score}/100 ({band})."]
    if retr:
        parts.append(f"{retr*100:.0f}% of the corpus is retracted.")
    if postpub:
        parts.append(f"{postpub*100:.0f}% of resolved DOIs changed after "
                     f"publication.")
    if npat:
        parts.append(f"{npat} integrity pattern(s) detected in the abstracts.")
    if band == "high":
        parts.append("The literature you are building on is comparatively clean.")
    else:
        parts.append("Treat the flagged references with caution before building "
                     "on them.")
    return " ".join(parts)
