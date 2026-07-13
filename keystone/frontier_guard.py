"""
keystone.frontier_guard
======================
Keystone's responsible-AI layer for three frontier claims the field is racing
toward: AI-designed phages / phage therapy, organoid-to-patient response
prediction, and biological-age-acceleration ("aging clock") estimation.

Keystone DOES something useful on each frontier — it VETS a candidate and
SCORES a study — while REFUSING the unsafe core (generating pathogen
sequences; predicting a patient's outcome). Rule 7 holds: every verdict is a
deterministic screen against a DECLARED, cited marker/standard set. Nothing
is generated; no patient data or image is ever read.

Honest boundary, stated on the record:
  * The phage vet is a FIRST-PASS annotation screen against a declared
    marker set — NOT a validated pipeline (PhageAI / CheckV) and NOT a
    substitute for institutional biosafety review (IBC).
  * The organoid score rates STUDY reproducibility risk — it does NOT
    predict patient response, read images, or touch patient data.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Declared marker sets — named constants, each with a citation. A phage
# genome carrying any of the first three families is unsuitable for therapy.
# ---------------------------------------------------------------------------
TOXIN_GENES = {
    "stx": "Shiga toxin (stx1/stx2) — enterohaemorrhagic toxin",
    "ctxa": "cholera toxin subunit A", "ctxb": "cholera toxin subunit B",
    "diphtheria toxin": "diphtheria toxin",
    "enterotoxin": "bacterial enterotoxin",
    "hlya": "alpha-haemolysin", "hemolysin": "haemolysin",
    "leukocidin": "Panton-Valentine leukocidin",
    "cdtb": "cytolethal distending toxin B",
}
LYSOGENY_MARKERS = {
    "integrase": "phage integrase — hallmark of a temperate (lysogenic) phage",
    "excisionase": "excisionase (xis) — prophage excision",
    "repressor ci": "cI repressor — lysogenic maintenance",
    "attp": "phage attachment site (attP) — integration",
    "prophage": "prophage / lysogen signature",
    "temperate": "temperate lifecycle annotation",
}
AMR_GENES = {
    "bla": "beta-lactamase family (blaTEM/blaKPC/blaNDM …)",
    "tet": "tetracycline resistance (tetM/tetA …)",
    "meca": "methicillin resistance (mecA)",
    "vana": "vancomycin resistance (vanA)", "vanb": "vancomycin resistance (vanB)",
    "aac": "aminoglycoside acetyltransferase", "aph": "aminoglycoside phosphotransferase",
    "erm": "macrolide resistance (erm)", "sul": "sulfonamide resistance (sul)",
    "qnr": "quinolone resistance (qnr)",
}
HOST_RANGE_MARKERS = {
    "receptor binding": "receptor-binding protein — defines host range",
    "receptor-binding": "receptor-binding protein — defines host range",
    "tail fiber": "tail fibre — host recognition",
    "tail fibre": "tail fibre — host recognition",
    "tailspike": "tailspike — host recognition",
    "tail spike": "tailspike — host recognition",
    "depolymerase": "capsule depolymerase — host range",
    "rbp": "receptor-binding protein",
}

_TOXIN_CITE = "Philipson et al. 2018; FDA phage-therapy guidance"
_LYSOGENY_CITE = "Kortright et al. 2019 (Cell Host & Microbe) — lytic phages for therapy"
_AMR_CITE = "Hyman 2019; only AMR-free phages are therapeutic candidates"
_HOSTRANGE_CITE = "Ross et al. 2016 — host-range characterization"

# ---------------------------------------------------------------------------
# Organoid drug-screening study rigor standard — each item cite-able. Two
# items are CRITICAL (their absence alone is a major reproducibility risk).
# ---------------------------------------------------------------------------
ORGANOID_RIGOR = [
    ("authenticated", True,
     "organoid authenticated (Cellosaurus/STR profile or a biobank ID)?",
     "ICLAC / Cellosaurus authentication standard"),
    ("matched_normal", True,
     "matched-normal (patient-paired non-tumour) organoid control present?",
     "Vlachogiannis et al. 2018 (Science) — matched-normal control"),
    ("passage_recorded", False,
     "passage number recorded and within a validated range?",
     "Drost & Clevers 2018 — passage drift"),
    ("matrigel_batch", False,
     "Matrigel/BME lot/batch recorded?",
     "Kozlowski et al. 2021 — batch effects in ECM"),
    ("replicates_adequate", False,
     "biological replicate n >= 3?",
     "NIH Rigor & Reproducibility"),
    ("blinded", False,
     "response scoring blinded to treatment arm?",
     "Landis et al. 2012 (Nature) — blinding"),
    ("viability_validated", False,
     "viability/response readout validated (orthogonal assay)?",
     "Kondo et al. 2019 — organoid viability readouts"),
    ("data_deposited", False,
     "raw data deposited to a public repository?",
     "FAIR data principles"),
]

# ---------------------------------------------------------------------------
# Frontier catalogue — what Keystone does, and what it refuses, per frontier.
# ---------------------------------------------------------------------------
FRONTIERS = {
    "phage_design": {
        "title": "AI-designed phages / phage-therapy prediction",
        "does": "Vets a user-provided phage-genome candidate for biosafety "
                "(toxin / lysogeny / AMR gene screen + host-range evidence) "
                "and scans the phage-therapy literature.",
        "refuses": [
            "generating or designing novel genetic sequences (no DNA "
            "language model call — a generated sequence is an unvalidated, "
            "dual-use claim)",
            "predicting the 'optimal' phage or phage combination as a "
            "treatment recommendation for a resistant strain — that needs "
            "phage susceptibility typing, IRB, and a clinician; Keystone "
            "vets safety and shows the evidence, it does not prescribe a phage",
            "treating this screen as biosafety clearance — it does NOT "
            "replace a validated pipeline (PhageAI/CheckV) or institutional "
            "biosafety review (IBC)",
        ],
    },
    "organoid_response": {
        "title": "Organoid imaging + genomics → patient response",
        "does": "Scores a described patient-derived-organoid drug-screening "
                "STUDY for reproducibility risk against published rigor "
                "standards, and scans the organoid drug-screening literature.",
        "refuses": [
            "predicting an individual patient's treatment response "
            "(clinical decision support needs a validated diagnostic + IRB "
            "+ a qualified physician)",
            "reading patient images or ingesting patient data — Keystone "
            "extracts no measurements from live-cell imaging and touches no "
            "PHI",
        ],
    },
    "aging_clock": {
        "title": "Biological age acceleration from single-cell / omics data",
        "does": "Benchmarks a CLAIMED biological-age-acceleration result "
                "against published aging clocks, scores an aging-clock STUDY "
                "for reproducibility rigor, and scans the aging literature.",
        "refuses": [
            "computing an individual patient's biological age or age "
            "acceleration from raw patient scRNA-seq — that is a clinical "
            "prediction on patient data needing a validated clock, IRB, and "
            "data governance",
            "reading patient samples or ingesting PHI — Keystone benchmarks a "
            "claimed result and scores study rigor; it does not run a clock "
            "on patient data",
        ],
    },
}


def frontier_catalogue() -> list:
    return [{"frontier": k, **v} for k, v in FRONTIERS.items()]


# ---------------------------------------------------------------------------
# Frontier A — phage candidate biosafety vetting
# ---------------------------------------------------------------------------
def _gene_tokens(genes: list, text: str):
    joined = (" ".join(genes or []) + " " + (text or "")).lower()
    toks = [t for t in re.split(r"[^a-z0-9]+", " ".join(genes or []).lower()) if t]
    return toks, joined


def _match_family(tokens: list, joined: str, family: dict) -> list:
    hits = []
    for marker, desc in family.items():
        m = marker.lower()
        if " " in m or "-" in m:
            if m in joined:
                hits.append({"marker": marker, "detail": desc})
        else:
            if any(t == m or t.startswith(m) for t in tokens):
                hits.append({"marker": marker, "detail": desc})
    return hits


def vet_phage_candidate(genes: list | None = None, text: str = "") -> dict:
    """First-pass biosafety screen of a phage-genome candidate's gene
    annotations against declared marker sets. Returns a go / caution / no-go
    verdict. Never generates a sequence; never claims clearance."""
    tokens, joined = _gene_tokens(genes, text)

    toxin = _match_family(tokens, joined, TOXIN_GENES)
    lyso = _match_family(tokens, joined, LYSOGENY_MARKERS)
    amr = _match_family(tokens, joined, AMR_GENES)
    host = _match_family(tokens, joined, HOST_RANGE_MARKERS)

    checks = [
        {"category": "toxin genes", "hit": bool(toxin),
         "markers": toxin, "citation": _TOXIN_CITE,
         "rule": "a therapeutic phage must be toxin-free"},
        {"category": "lysogeny / temperate", "hit": bool(lyso),
         "markers": lyso, "citation": _LYSOGENY_CITE,
         "rule": "therapeutic phages must be strictly lytic"},
        {"category": "AMR genes", "hit": bool(amr),
         "markers": amr, "citation": _AMR_CITE,
         "rule": "must not carry or transfer antimicrobial resistance"},
        {"category": "host-range evidence", "hit": bool(host),
         "markers": host, "citation": _HOSTRANGE_CITE,
         "rule": "receptor-binding / tail-fibre annotation characterizes host range"},
    ]

    disqualifying = []
    if toxin:
        disqualifying.append("toxin gene(s)")
    if lyso:
        disqualifying.append("lysogeny marker(s)")
    if amr:
        disqualifying.append("AMR gene(s)")

    if disqualifying:
        verdict = "no-go"
        reason = ("Candidate carries " + ", ".join(disqualifying)
                  + " — unsuitable for therapy on this first-pass screen.")
    elif not host:
        verdict = "caution"
        reason = ("No toxin/lysogeny/AMR marker found, but host-range "
                  "annotation is absent — host range is uncharacterized.")
    else:
        verdict = "go"
        reason = ("No toxin/lysogeny/AMR marker found and host-range "
                  "annotation is present — screen-clear (first pass only).")

    return {
        "input_kind": "phage_candidate",
        "n_genes_screened": len(genes or []),
        "verdict": verdict,
        "reason": reason,
        "checks": checks,
        "refusal": ("This is a first-pass annotation screen against a "
                    "declared marker set — NOT a validated pipeline "
                    "(PhageAI/CheckV) and NOT institutional biosafety "
                    "clearance (IBC). Keystone does not generate sequences."),
    }


# ---------------------------------------------------------------------------
# Frontier B — organoid study reproducibility-risk scorecard
# ---------------------------------------------------------------------------
_ORGANOID_FIX = {
    "authenticated": "Authenticate the organoid line (STR profile or biobank "
                     "accession) and report it.",
    "matched_normal": "Include a patient-paired matched-normal organoid "
                      "control for every tumour line.",
    "passage_recorded": "Record passage number at assay and cap it within a "
                        "validated range.",
    "matrigel_batch": "Record the Matrigel/BME lot and control for batch "
                      "effects across arms.",
    "replicates_adequate": "Run >= 3 biological replicates per condition.",
    "blinded": "Blind response scoring to the treatment arm.",
    "viability_validated": "Validate the viability readout with an orthogonal "
                           "assay.",
    "data_deposited": "Deposit raw data in a public repository at publication.",
}


def score_organoid_study(params: dict | None = None) -> dict:
    """Score a described PDO drug-screening study for reproducibility risk.
    `params` maps rigor-item keys to truthy = present. Missing = a gap. Never
    predicts patient response; reads no patient data."""
    params = params or {}
    checks, gaps, fixes = [], [], []
    critical_gaps = 0
    for key, critical, question, cite in ORGANOID_RIGOR:
        present = bool(params.get(key))
        checks.append({"item": key, "question": question, "present": present,
                       "critical": critical, "citation": cite})
        if not present:
            gaps.append({"item": key, "question": question, "critical": critical,
                         "citation": cite})
            fixes.append(_ORGANOID_FIX[key])
            if critical:
                critical_gaps += 1

    n_gaps = len(gaps)
    if critical_gaps >= 1 or n_gaps >= 5:
        verdict = "high"
    elif n_gaps >= 2:
        verdict = "medium"
    else:
        verdict = "low"

    reason = (f"{n_gaps} of {len(ORGANOID_RIGOR)} rigor item(s) unmet"
              + (f", including {critical_gaps} critical" if critical_gaps else "")
              + f" → {verdict} reproducibility risk.")

    return {
        "input_kind": "organoid_study",
        "verdict": verdict,
        "reason": reason,
        "n_gaps": n_gaps,
        "critical_gaps": critical_gaps,
        "checks": checks,
        "gaps": gaps,
        "fixes": fixes,
        "refusal": ("Keystone scores STUDY reproducibility risk only. It does "
                    "NOT predict an individual patient's treatment response, "
                    "read patient images, or ingest patient data — that is "
                    "clinical decision support requiring a validated "
                    "diagnostic, IRB approval, and a qualified physician."),
    }


# ---------------------------------------------------------------------------
# Frontier C — biological-age-acceleration study rigor + published-clock benchmark
# ---------------------------------------------------------------------------
# Published aging clocks a claimed result must be benchmarked against — each
# with its citation. Keystone shows this reference table; it does not run a
# clock on patient data.
PUBLISHED_CLOCKS = [
    ("Horvath multi-tissue", "353-CpG pan-tissue DNA-methylation clock",
     "Horvath 2013 (Genome Biology)"),
    ("Hannum blood", "71-CpG blood DNA-methylation clock",
     "Hannum et al. 2013 (Molecular Cell)"),
    ("PhenoAge", "phenotypic-age DNAm clock, mortality-trained",
     "Levine et al. 2018 (Aging)"),
    ("GrimAge", "lifespan/mortality DNAm clock",
     "Lu et al. 2019 (Aging)"),
    ("scRNA transcriptomic clock", "single-cell RNA transcriptomic aging clock",
     "Buckley et al. 2023 (Nature Aging)"),
]

# Aging-clock STUDY rigor standard — each item cite-able. Two are CRITICAL.
AGING_RIGOR = [
    ("clock_selection_justified", True,
     "aging clock named + selection justified (which clock, why)?",
     "Bell et al. 2019 (Genome Biology) — clock-choice sensitivity"),
    ("chronological_age_controlled", True,
     "chronological-age confound controlled (age-acceleration = residual)?",
     "Horvath & Raj 2018 (Nat Rev Genetics)"),
    ("healthy_controls_matched", False,
     "healthy controls matched on age / sex / tissue?",
     "El Khoury et al. 2019 — control matching"),
    ("batch_corrected", False,
     "batch effects corrected across samples/plates?",
     "Leek et al. 2010 — batch effects in high-throughput data"),
    ("tissue_matched", False,
     "clock trained on the SAME tissue as the samples?",
     "Horvath 2013 — tissue specificity"),
    ("replicates_adequate", False,
     "biological replicate n adequate + reported?",
     "NIH Rigor & Reproducibility"),
    ("data_code_deposited", False,
     "raw data + analysis code deposited?",
     "FAIR data principles"),
]

_AGING_FIX = {
    "clock_selection_justified": "Name the aging clock and justify the choice "
        "for your tissue and data type; benchmark against a second clock.",
    "chronological_age_controlled": "Define age acceleration as the residual "
        "of biological vs chronological age; control the chronological-age "
        "confound explicitly.",
    "healthy_controls_matched": "Match healthy controls on age, sex, and tissue "
        "before comparing acceleration.",
    "batch_corrected": "Apply and report batch correction across samples/plates.",
    "tissue_matched": "Use a clock trained on the same tissue, or state the "
        "cross-tissue limitation.",
    "replicates_adequate": "Report biological replicate n and power.",
    "data_code_deposited": "Deposit raw data + analysis code at publication.",
}


def score_aging_study(params: dict | None = None) -> dict:
    """Score a described biological-age-acceleration STUDY for reproducibility
    risk, and return the published-clock reference table to benchmark against.
    Never computes a biological age from patient data; reads no PHI."""
    params = params or {}
    checks, gaps, fixes, critical_gaps = [], [], [], 0
    for key, critical, question, cite in AGING_RIGOR:
        present = bool(params.get(key))
        checks.append({"item": key, "question": question, "present": present,
                       "critical": critical, "citation": cite})
        if not present:
            gaps.append({"item": key, "question": question, "critical": critical,
                         "citation": cite})
            fixes.append(_AGING_FIX[key])
            if critical:
                critical_gaps += 1

    n_gaps = len(gaps)
    if critical_gaps >= 1 or n_gaps >= 5:
        verdict = "high"
    elif n_gaps >= 2:
        verdict = "medium"
    else:
        verdict = "low"

    return {
        "input_kind": "aging_study",
        "verdict": verdict,
        "reason": (f"{n_gaps} of {len(AGING_RIGOR)} rigor item(s) unmet"
                   + (f", including {critical_gaps} critical" if critical_gaps else "")
                   + f" → {verdict} reproducibility risk."),
        "n_gaps": n_gaps,
        "critical_gaps": critical_gaps,
        "checks": checks,
        "gaps": gaps,
        "fixes": fixes,
        "benchmark_clocks": [{"clock": c, "detail": d, "citation": cite}
                             for c, d, cite in PUBLISHED_CLOCKS],
        "refusal": ("Keystone benchmarks a CLAIMED age-acceleration result and "
                    "scores study rigor. It does NOT compute a patient's "
                    "biological age from raw scRNA-seq, read patient samples, "
                    "or touch PHI — that is a clinical prediction needing a "
                    "validated clock, IRB approval, and data governance."),
    }


# ---------------------------------------------------------------------------
# Rigor checklists (cite-able + "provide your own"), reused by the UI + report.
# ---------------------------------------------------------------------------
PHAGE_RIGOR = [
    "Host-range characterization across a validated bacterial panel.",
    "Whole-genome sequencing + annotation, explicitly screened for "
    "lysogeny / toxin / AMR genes (provide your own annotation).",
    "Endotoxin removal + measured endotoxin limit (EU/mL).",
    "PFU titer method and stability data.",
    "In-vitro efficacy before any in-vivo work; staged escalation.",
    "Regulatory path (FDA eIND for compassionate use) documented.",
    "Biosafety level (BSL) and institutional IBC approval on file.",
]
ORGANOID_RIGOR_CHECKLIST = [
    "Organoid authentication (Cellosaurus/STR or biobank ID) — provide your own.",
    "Passage number at assay, within a validated range.",
    "Matrigel/BME lot recorded; batch effects controlled.",
    "Drug source (ChEMBL id) + concentration range + vehicle control.",
    ">= 3 biological replicates; blinded scoring.",
    "Matched-normal organoid control.",
    "Validated viability/response readout.",
    "Raw data + analysis code deposited (provide your own accessions).",
]
AGING_RIGOR_CHECKLIST = [
    "Aging clock named + selection justified (Horvath / PhenoAge / GrimAge / …).",
    "Age acceleration defined as the residual of biological vs chronological age.",
    "Healthy controls matched on age / sex / tissue.",
    "Clock trained on the SAME tissue as the samples (or limitation stated).",
    "Batch effects corrected and reported.",
    "Biological replicate n reported + powered.",
    "Benchmarked against >= 2 published clocks.",
    "Raw data + analysis code deposited (provide your own accessions).",
]


def assess_frontier(frontier: str, genes: list | None = None,
                    text: str = "", study: dict | None = None,
                    records: list | None = None, question: str = "",
                    seed_doi: str = "") -> dict:
    """Compose the frontier response: the ACTIVE verdict + the refusal + an
    optional literature evidence scan + the rigor checklist. Unknown frontiers
    are refused, never guessed."""
    frontier = (frontier or "").strip().lower()
    if frontier not in FRONTIERS:
        return {"frontier": frontier, "refused": True,
                "reason": (f"unknown frontier '{frontier}'. Supported: "
                           f"{', '.join(FRONTIERS)}.")}

    meta = FRONTIERS[frontier]
    if frontier == "phage_design":
        active = vet_phage_candidate(genes=genes, text=text)
        rigor = PHAGE_RIGOR
    elif frontier == "aging_clock":
        active = score_aging_study(study)
        rigor = AGING_RIGOR_CHECKLIST
    else:
        active = score_organoid_study(study)
        rigor = ORGANOID_RIGOR_CHECKLIST

    evidence = None
    if records:
        from keystone.agents.pattern_miner import mine_patterns
        evidence = mine_patterns(records, question=question, seed_doi=seed_doi,
                                 scan_type="all").to_dict()

    return {
        "frontier": frontier,
        "title": meta["title"],
        "does": meta["does"],
        "refuses": meta["refuses"],
        "active": active,
        "evidence": evidence,
        "rigor_checklist": rigor,
    }
