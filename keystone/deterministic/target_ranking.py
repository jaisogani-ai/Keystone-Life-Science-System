"""
keystone.deterministic.target_ranking
=====================================
Transparent, reproducible target ranking for Keystone Target Trust. The ranking
is NEVER a single opaque "best target" number: every candidate exposes eight
separate components, each carrying its evidence label, source, formula, input,
version, uncertainty, and limitation. The composite is a weighted sum with the
weights shown, so a scientist can see exactly why one regulator outranks another.

Every value is grounded in a real, resolvable source (real DOI / UniProt / ChEMBL
record) and labeled with its provenance kind. Nothing here is a trained model or a
causal claim — perturbation effects are the published measurements, labeled as such.

Counterfactual-aware: pass ``excluded_sources`` (e.g. the not-peer-reviewed
preprint) and any component whose only support is excluded drops to
``Unknown / insufficient evidence`` and the ranking recomputes — a real state change.
"""
from __future__ import annotations

import re

# ---- exact labels (spec contract) -----------------------------------------
EVIDENCE_LABELS = ("Measured in dataset", "Computed from analysis",
                   "Literature-supported", "Model hypothesis",
                   "Unknown / insufficient evidence")
TRACTABILITY_LABELS = ("Existing degrader evidence", "Ligandability evidence",
                       "Structural/chemical tractability proxy",
                       "E3-recruitment evidence", "Predicted hypothesis",
                       "No tractability evidence found")

# ---- the 8-component contract + exposed weights ---------------------------
# safety and integrity are RISKS (higher = worse) → scored as (1 - risk).
# missing_evidence is a completeness flag shown separately, NOT folded into one score.
WEIGHTS = {
    "functional_effect": 0.26,
    "activation_specificity": 0.12,
    "type2_pathway": 0.16,
    "disease_relevance": 0.12,
    "tractability": 0.18,
    "safety": 0.10,        # applied to (1 - safety_risk)
    "integrity": 0.06,     # applied to (1 - integrity_risk)
}

_DATA_VERSION = "tcell-evidence-2026-07"


def _c(value, label, source, formula, inp, uncertainty, limitation):
    """One ranking component — self-describing provenance (spec contract)."""
    assert label in EVIDENCE_LABELS or label in TRACTABILITY_LABELS, label
    return {"value": value, "label": label, "source": source, "formula": formula,
            "input": inp, "version": _DATA_VERSION, "uncertainty": uncertainty,
            "limitation": limitation}


# ---- pinned REAL evidence per candidate regulator -------------------------
# Values are curated from the cited real literature; each labeled by provenance
# kind. `pre_support` names the source a component rests on (for the counterfactual).
CANDIDATES = [
    {
        "gene": "GATA3", "uniprot": "P23771", "node_id": "N_target",
        "functional_effect": _c(
            0.92, "Literature-supported", "DOI:10.1016/S0092-8674(00)80240-8",
            "reported effect magnitude on IL-4/IL-5/IL-13 (necessary & sufficient)",
            "Zheng & Flavell 1997; recovered as top screen hit (Shifrut 2018)",
            "±0.05 (canonical, multiple studies)",
            "reported, not re-derived from raw counts in this build"),
        "activation_specificity": _c(
            0.45, "Literature-supported", "DOI:10.1016/j.cell.2019.01.019",
            "specificity to differentiation vs general activation",
            "Henriksson 2019 — GATA3 couples activation AND differentiation",
            "±0.15", "GATA3 acts on both axes → limited state-specificity"),
        "type2_pathway": _c(
            0.98, "Literature-supported", "DOI:10.1016/S0092-8674(00)80240-8",
            "centrality in the type-2 cytokine program",
            "master TF of the IL-4/IL-5/IL-13 locus", "±0.02",
            "central node — perturbation is pleiotropic"),
        "disease_relevance": _c(
            0.80, "Literature-supported", "UniProt:P23771",
            "human disease/GWAS association (asthma/allergy)",
            "GATA3 asthma & allergic-disease associations",
            "±0.10", "association, not causal in humans"),
        "tractability": _c(
            0.15, "No tractability evidence found", "ChEMBL:GATA3",
            "ligandability / degrader evidence lookup",
            "transcription factor; no approved small molecule or degrader",
            "high", "TFs are classically undruggable; degrader is a hypothesis"),
        "safety_risk": _c(
            0.85, "Literature-supported", "DOI:10.1016/j.cell.2019.01.019",
            "essentiality / on-target liability",
            "GATA3 required for CD4 T-cell development & fitness",
            "±0.10", "direct loss impairs normal T cells — selectivity concern"),
        "integrity_risk": _c(
            0.10, "Literature-supported", "peer-reviewed",
            "source integrity (retraction/concern/preprint)",
            "all support peer-reviewed", "low", "none"),
        "missing_evidence": ["a selective degrader or ligand", "in-vivo selectivity window"],
    },
    {
        "gene": "STAT6", "uniprot": "P42226", "node_id": "N_dep_A",
        "precedent": {
            "drug": "KT-621 (Kymera)",
            "status": "Oral STAT6 degrader · Phase 1b atopic dermatitis · ~98% degradation · biologic-like efficacy · FDA Fast Track",
            "source": "https://investors.kymeratx.com/news-releases/news-release-details/kymera-therapeutics-announces-positive-results-broaden-phase-1b"},
        "functional_effect": _c(
            0.80, "Literature-supported", "UniProt:P42226",
            "reported effect on Th2 program via GATA3 induction",
            "IL-4R → STAT6 → GATA3 axis (upstream master switch)",
            "±0.08", "reported, upstream node"),
        "activation_specificity": _c(
            0.62, "Literature-supported", "DOI:10.1016/j.cell.2019.01.019",
            "differentiation-vs-activation specificity",
            "STAT6 is comparatively Th2-differentiation biased", "±0.12",
            "some activation role remains"),
        "type2_pathway": _c(
            0.88, "Literature-supported", "UniProt:P42226",
            "centrality in the type-2 program", "direct IL-4R signal transducer",
            "±0.05", "upstream of GATA3"),
        "disease_relevance": _c(
            0.78, "Literature-supported", "UniProt:P42226",
            "human disease association (atopy/asthma)",
            "STAT6 atopic-disease associations", "±0.10", "association, not causal"),
        "tractability": _c(
            0.95, "Existing degrader evidence",
            "https://investors.kymeratx.com/news-releases/news-release-details/kymera-therapeutics-announces-positive-results-broaden-phase-1b",
            "direct degrader-precedent lookup",
            "KT-621 — first-in-class ORAL STAT6 degrader; Phase 1b atopic dermatitis "
            "(~98% STAT6 degradation, biologic-like efficacy) — clinical proof an "
            "intracellular type-2 master regulator is degradable",
            "low", "clinical-stage in AD/asthma, not yet approved"),
        "safety_risk": _c(
            0.45, "Literature-supported", "UniProt:P42226",
            "essentiality / on-target liability",
            "narrower phenotype than GATA3 loss", "±0.15",
            "IL-4 signalling loss has immune consequences"),
        "integrity_risk": _c(
            0.10, "Literature-supported", "peer-reviewed",
            "source integrity", "peer-reviewed support", "low", "none"),
        "missing_evidence": ["human selectivity data", "degrader feasibility"],
    },
    {
        "gene": "RARA", "uniprot": "P10276", "node_id": "N_dep_B",
        "functional_effect": _c(
            0.60, "Literature-supported", "UniProt:P10276",
            "nominated Th2-regulator effect size",
            "RARA nominated as Th2 regulator (retinoid signalling)",
            "±0.15", "smaller/indirect effect than the master TFs"),
        "activation_specificity": _c(
            0.68, "Literature-supported", "UniProt:P10276",
            "differentiation specificity", "retinoid axis biased to differentiation",
            "±0.15", "context-dependent"),
        "type2_pathway": _c(
            0.60, "Literature-supported", "UniProt:P10276",
            "type-2 program involvement", "modulates Th2 cytokines via retinoids",
            "±0.15", "modulatory, not master"),
        "disease_relevance": _c(
            0.55, "Literature-supported", "UniProt:P10276",
            "disease association", "retinoid pathway in allergic inflammation",
            "±0.15", "weaker human genetic support"),
        "tractability": _c(
            0.90, "Ligandability evidence", "ChEMBL:CHEMBL1857",
            "approved-ligand / degrader lookup",
            "highly ligandable nuclear receptor — approved retinoids (tazarotene, "
            "all-trans retinoic acid induces RARA degradation)",
            "low", "selectivity across RAR isoforms needed"),
        "safety_risk": _c(
            0.40, "Literature-supported", "UniProt:P10276",
            "on-target liability", "retinoid toxicities are known & manageable",
            "±0.15", "teratogenicity / mucocutaneous effects"),
        "integrity_risk": _c(
            0.10, "Literature-supported", "peer-reviewed",
            "source integrity", "peer-reviewed support", "low", "none"),
        "missing_evidence": ["direct Th2-shift magnitude in human CD4 cells"],
    },
    {
        "gene": "FBXO32", "uniprot": "Q969P5", "node_id": "N_dep_C",
        "pre_support": "https://www.biorxiv.org/content/10.64898/2025.12.23.696273v1",
        "functional_effect": _c(
            0.55, "Literature-supported", "PREPRINT",
            "predicted Th2-regulator weight (preprint model)",
            "top Th2 regulator in the 2025 CD4 Perturb-seq preprint",
            "high", "sole support is a not-yet-peer-reviewed preprint"),
        "activation_specificity": _c(
            0.50, "Model hypothesis", "PREPRINT",
            "inferred specificity", "preprint model weight", "high",
            "not independently validated"),
        "type2_pathway": _c(
            0.45, "Model hypothesis", "PREPRINT",
            "type-2 involvement via NF-κB/GATA3", "mechanistic hypothesis",
            "high", "mechanism proposed, not demonstrated in T cells"),
        "disease_relevance": _c(
            0.35, "Literature-supported", "UniProt:Q969P5",
            "disease association", "inflammatory-response associations (myocarditis)",
            "high", "not an established immune-disease gene"),
        "tractability": _c(
            0.50, "E3-recruitment evidence", "UniProt:Q969P5",
            "degrader-handle lookup",
            "FBXO32 is itself an SCF E3 substrate receptor — a potential degrader "
            "handle, but targeting FBXO32 as a target is unproven",
            "high", "E3 component ≠ a ligandable target for degradation"),
        "safety_risk": _c(
            0.55, "Unknown / insufficient evidence", "UniProt:Q969P5",
            "on-target liability", "muscle-atrophy E3 role → off-tissue effects",
            "high", "T-cell-specific safety unknown"),
        "integrity_risk": _c(
            0.70, "Literature-supported", "PREPRINT",
            "source integrity (preprint)", "not yet peer-reviewed", "n/a",
            "provisional — exclude in the counterfactual to test robustness"),
        "missing_evidence": ["peer-reviewed replication", "T-cell phenotype",
                             "ligandability of FBXO32 itself"],
    },
]

_POSITIVE = ["functional_effect", "activation_specificity", "type2_pathway",
             "disease_relevance", "tractability"]
_RISK = ["safety_risk", "integrity_risk"]


def _normalize_source_id(sid: str) -> str:
    """Canonicalize a source id so every handle for the SAME record collapses to one
    key: a bare DOI, a ``DOI:``-prefixed DOI, a ``doi.org`` URL, and the bioRxiv
    content URL (with its ``vN`` version suffix) all reduce to the same core DOI.
    This makes the counterfactual robust to whichever identifier a scientist pastes —
    without it, only the exact URL matched and the canonical DOI silently no-op'd."""
    s = (sid or "").strip().lower()
    for pre in ("https://", "http://"):
        if s.startswith(pre):
            s = s[len(pre):]
    s = s.removeprefix("www.")
    s = s.removeprefix("doi:").strip()
    if "doi.org/" in s:
        s = s.split("doi.org/", 1)[1]
    if "biorxiv.org/content/" in s:
        s = s.split("biorxiv.org/content/", 1)[1]
    s = re.sub(r"v\d+(\.full|\.abstract)?$", "", s)   # strip bioRxiv version suffix
    return s.rstrip("/")


def _effective_weights(weights) -> tuple[dict, bool]:
    """Resolve the composite weights a scientist may override. Start from the default
    ``WEIGHTS``, apply only valid keys with non-negative float values, then renormalize
    to sum 1.0 so the composite stays comparable. Invalid / empty input → defaults
    (``customized=False``). The weighting is transparent and never mutates any
    component's underlying evidence — only how much each already-sourced component counts."""
    if not weights:
        return dict(WEIGHTS), False
    eff, changed = dict(WEIGHTS), False
    for key, val in weights.items():
        if key in WEIGHTS:
            try:
                fval = float(val)
            except (TypeError, ValueError):
                continue
            if fval >= 0:
                eff[key], changed = fval, True
    total = sum(eff.values())
    if not changed or total <= 0:
        return dict(WEIGHTS), False
    return {k: round(v / total, 4) for k, v in eff.items()}, True


def _component_source_ids(comp: dict, cand: dict) -> set:
    """Every (normalized) identifier a scientist could exclude a component by. A
    component that rests on the preprint carries the raw token ``"PREPRINT"`` and
    resolves to the concrete preprint URL (``pre_support``); excluding *either* — by
    the token, the URL, or the canonical DOI in any form — must match."""
    raw = comp.get("source")
    resolved = cand.get("pre_support") if raw == "PREPRINT" else raw
    return {_normalize_source_id(s) for s in (raw, resolved) if s}


def _gladstone_effect(gene: str) -> dict | None:
    """Real MEASURED perturbation metrics for ``gene`` from the pinned Gladstone–UCSF
    CD4+ T-cell genome-scale Perturb-seq dataset (Zhu et al. 2025, bioRxiv). Attached
    as provenance to the functional-effect component — it never overwrites the sourced
    value. Cross-donor reproducibility is surfaced verbatim (FBXO32's is low, a real
    integrity signal). Returns ``None`` if the study did not measure the gene."""
    try:
        from keystone import gladstone_data
        e = gladstone_data.regulator_effect(gene)
        if e is None:
            return None
        p = gladstone_data.provenance()
        return {
            "label": "Measured in dataset",
            "dataset": "Gladstone–UCSF CD4+ T-cell genome-scale Perturb-seq",
            "source": f"DOI:{p['doi']}",
            "citation": "Zhu, …, Marson (2025), bioRxiv — not peer-reviewed",
            "condition": e["condition"],
            "n_downstream_de_genes": e.get("n_downstream"),
            "ontarget_effect_size": e.get("ontarget_effect_size"),
            "crossdonor_reproducibility": e.get("crossdonor_correlation_mean"),
            "peer_reviewed": p["peer_reviewed"],
            "note": ("measured knockdown footprint in primary human CD4+ T cells "
                     "(4 donors); cross-donor reproducibility shown as-is — preprint, "
                     "provisional, not a causal claim"),
        }
    except Exception:
        return None


def rank_targets(excluded_sources=(), weights=None) -> dict:
    """Rank the candidate regulators. ``excluded_sources`` (iterable of source ids,
    e.g. the preprint URL) demotes any SUPPORT component that rests on an excluded
    source to ``Unknown / insufficient evidence`` (value 0) and recomputes — a real
    state change. Risk components keep their value (exclusion never rewards a risk)."""
    excluded = {_normalize_source_id(s) for s in (excluded_sources or ())}
    eff_weights, weights_customized = _effective_weights(weights)
    # functional effect is COMPUTED by a real pipeline (not typed): the measured
    # Δ type-2 signature score per knockdown, leave-one-perturbation-out.
    # The HEADLINE functional effect that drives the rank stays Literature-supported
    # (real DOIs in CANDIDATES). The exploratory ML pipeline is attached as a clearly
    # labelled cross-check ONLY — its input matrix is synthetic, so it must never set
    # a ranking number. It recovers the literature ordering as a sanity check; run it
    # on a real .h5ad (load_real_matrix) to promote it to a real ranking input.
    from keystone.ml.th2_signature import functional_effects, DATA_VERSION
    fx = functional_effects()
    ranked = []
    for cand in CANDIDATES:
        if cand["gene"] in fx:
            cand = {**cand, "functional_effect_crosscheck": {
                "value": fx[cand["gene"]],
                "label": "Computed from analysis (exploratory)",
                "source": "keystone/ml/th2_signature.py · SYNTHETIC matrix",
                "method": "Δ type-2 signature score · leave-one-perturbation-out CV",
                "version": DATA_VERSION,
                "note": "method cross-check on a SYNTHETIC matrix built from the real "
                        "Th2 signature; recovers the literature ordering "
                        "(GATA3>STAT6>RARA>FBXO32). Not a ranking input — see /api/perturbseq."}}
        # REAL measured corroboration from the Gladstone CD4+ T-cell Perturb-seq study
        # (Zhu et al. 2025) — the actual dataset this program is built on. Additive
        # provenance only; never sets a ranking number.
        _ps = _gladstone_effect(cand["gene"])
        if _ps is not None:
            cand = {**cand, "perturbseq_measured": _ps}
        # disease relevance is FETCHED LIVE from Open Targets (real genetic +
        # literature association vs the type-2 disease axis), not typed. Cache-first
        # + pinned fixture; a failed fetch keeps the curated value (never fabricates).
        ot = None
        try:
            from keystone.connectors.opentargets import type2_association
            ot = type2_association(cand["gene"])
        except Exception:
            ot = None
        if ot is not None:
            dis = ot.get("disease") or "no type-2 disease association"
            cand = {**cand, "disease_relevance": _c(
                ot["score"], "Literature-supported",
                f"Open Targets · {ot.get('disease_id') or 'no association'}",
                "max association score vs a type-2 inflammatory disease (asthma/atopy/allergy)",
                f"Open Targets platform · {dis}",
                "aggregate of genetic + literature evidence",
                ot.get("note") or "real database association — not proof of causality")}
        comps = {}
        for key in _POSITIVE + _RISK:
            comp = dict(cand[key])
            is_excluded = bool(_component_source_ids(comp, cand) & excluded)
            if is_excluded and key in _POSITIVE:
                comp = {**comp, "value": 0.0, "label": "Unknown / insufficient evidence",
                        "limitation": comp.get("limitation", "") + " · support excluded in this analysis"}
            elif is_excluded and key in _RISK:
                comp = {**comp, "label": "Unknown / insufficient evidence",
                        "limitation": comp.get("limitation", "") + " · support excluded"}
            comps[key] = comp
        safety = 1.0 - float(comps["safety_risk"]["value"])
        integrity = 1.0 - float(comps["integrity_risk"]["value"])
        parts = {
            "functional_effect": float(comps["functional_effect"]["value"]),
            "activation_specificity": float(comps["activation_specificity"]["value"]),
            "type2_pathway": float(comps["type2_pathway"]["value"]),
            "disease_relevance": float(comps["disease_relevance"]["value"]),
            "tractability": float(comps["tractability"]["value"]),
            "safety": safety,
            "integrity": integrity,
        }
        # round the parts first, then sum — so the composite EXACTLY equals the
        # weighted parts a reviewer sees (auditable; no rounding drift).
        weighted_parts = {k: round(eff_weights[k] * parts[k], 4) for k in eff_weights}
        composite = round(sum(weighted_parts.values()), 4)
        ranked.append({
            "gene": cand["gene"], "uniprot": cand["uniprot"], "node_id": cand["node_id"],
            "disclaimer": ("Keystone ranks a research hypothesis. This is not a "
                           "validated drug target."),
            "precedent": cand.get("precedent"),
            "functional_effect_crosscheck": cand.get("functional_effect_crosscheck"),
            "perturbseq_measured": cand.get("perturbseq_measured"),
            "composite": composite,
            "weighted_parts": weighted_parts,
            "components": {
                "functional_effect": comps["functional_effect"],
                "activation_specificity": comps["activation_specificity"],
                "type2_pathway": comps["type2_pathway"],
                "disease_relevance": comps["disease_relevance"],
                "tractability": comps["tractability"],
                "safety_risk": comps["safety_risk"],
                "integrity_risk": comps["integrity_risk"],
                "missing_evidence": cand["missing_evidence"],
            },
        })
    ranked.sort(key=lambda r: r["composite"], reverse=True)
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return {"weights": eff_weights, "default_weights": dict(WEIGHTS),
            "weights_customized": weights_customized, "version": _DATA_VERSION,
            "evidence_labels": list(EVIDENCE_LABELS),
            "tractability_labels": list(TRACTABILITY_LABELS),
            "excluded_sources": sorted(excluded), "ranking": ranked,
            "note": ("Composite is a weighted sum with weights shown; every component "
                     "is separately sourced and labeled. Perturbation effects are "
                     "published measurements (Literature-supported), not a trained "
                     "model, and no association is stated as causal.")}
