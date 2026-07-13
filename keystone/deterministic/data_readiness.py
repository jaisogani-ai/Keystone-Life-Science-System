"""
keystone.deterministic.data_readiness
=====================================
The **Data Readiness Gate** (Phase 2 · Priority 1). Every dataset, matrix, ranking
input, and biological result that the flagship CD4+ T-cell workflow touches is
audited here into a structured, visible manifest — source accession, version,
data type, QC, biological limits, and the single most important flag:
**can this source change the target ranking?**

Non-negotiable rules enforced/surfaced here:
  * Synthetic / exploratory classifier output is labeled ``synthetic fixture`` and
    marked ``affects_ranking: False`` — and `test_synthetic_cannot_affect_ranking`
    proves the ranking is numerically independent of it.
  * Real data (Gladstone preprint measurements, Open Targets, curated literature)
    is labeled by exactly what it is; preprints are flagged not-peer-reviewed.
  * Nothing is invented. A source that cannot be resolved is ``unavailable`` with a
    repair note, never faked.

`source_type` is one of: ``real_public`` | ``gladstone`` | ``synthetic_fixture`` |
``unavailable``.
"""
from __future__ import annotations

SOURCE_TYPES = ("real_public", "gladstone", "synthetic_fixture", "unavailable")


def _entry(*, name, source_type, source_id, url, version, preprocessing, qc,
           limitations, affects_ranking, affects_how, peer_reviewed=None):
    assert source_type in SOURCE_TYPES, source_type
    return {
        "name": name,
        "source_type": source_type,
        "source_id": source_id,
        "url": url,
        "version": version,
        "peer_reviewed": peer_reviewed,
        "preprocessing": preprocessing,
        "qc": qc,
        "biological_limitations": limitations,
        "affects_ranking": affects_ranking,
        "affects_how": affects_how,
    }


def _gladstone_entry() -> dict:
    """Real, pinned Gladstone–UCSF CD4+ T-cell Perturb-seq measurements."""
    try:
        from keystone import gladstone_data
        p = gladstone_data.provenance()
        effects = gladstone_data.all_regulator_effects()
        measured = [g for g, e in effects.items() if e]
        low_repro = [g for g, e in effects.items()
                     if e and (e.get("crossdonor_correlation_mean") or 1) < 0.3]
        return _entry(
            name="Gladstone–UCSF CD4+ T-cell genome-scale Perturb-seq",
            source_type="gladstone",
            source_id=f"DOI:{p['doi']}",
            url=p.get("url"),
            version=f"bioRxiv {p['doi']} · tables {', '.join(p.get('tables_used', []) or [])}",
            peer_reviewed=bool(p.get("peer_reviewed")),
            preprocessing="authors' Supplementary Tables pinned verbatim "
                          "(downstream-DE count, on-target KD, cross-donor r)",
            qc=f"measured for {len(measured)}/4 ranked regulators; cross-donor "
               f"reproducibility reported as-is"
               + (f" (low for {', '.join(low_repro)})" if low_repro else ""),
            limitations=[
                "PREPRINT — not peer-reviewed; provisional.",
                "Measured quantities, not causal estimates.",
                "Cross-donor r is low for FBXO32 (~0.13) — a real reason its "
                "nomination stays provisional.",
            ],
            affects_ranking=True,
            affects_how="attached to each candidate as MEASURED corroboration "
                        "(downstream DE / on-target KD / cross-donor r); surfaced, "
                        "not folded into the composite number",
        )
    except Exception as exc:
        return _entry(
            name="Gladstone CD4+ T-cell Perturb-seq", source_type="unavailable",
            source_id="DOI:10.64898/2025.12.23.696273", url=None, version=None,
            preprocessing="unavailable", qc="unavailable",
            limitations=[f"dataset fixture failed to load: {exc}"],
            affects_ranking=False,
            affects_how="unavailable — repair the pinned fixture in "
                        "keystone/connectors/fixtures/gladstone_cd4t_perturbseq.json")


def _opentargets_entry() -> dict:
    """Real Open Targets disease-association evidence → disease_relevance component."""
    resolved = None
    try:
        from keystone.connectors.opentargets import type2_association
        resolved = type2_association("STAT6")
    except Exception:
        resolved = None
    return _entry(
        name="Open Targets — type-2 disease associations",
        source_type="real_public",
        source_id="Open Targets Platform (GraphQL)",
        url="https://platform.opentargets.org/",
        version="cache-first → live → pinned fixture (per gene)",
        peer_reviewed=True,
        preprocessing="max association score vs a type-2 disease (asthma/atopy/allergy)",
        qc=("live/fixture resolved" if resolved else
            "offline — pinned fixtures for the 4 ranked genes"),
        limitations=[
            "Aggregate of genetic + literature evidence — association, not causality.",
            "A gene with no type-2 association scores 0 (a real negative signal).",
        ],
        affects_ranking=True,
        affects_how="sets the disease_relevance component (labeled Literature-supported)",
    )


def _literature_entry() -> dict:
    """Curated, real, resolvable literature/UniProt/ChEMBL/clinical evidence."""
    return _entry(
        name="Curated primary literature + registries (DOI / UniProt / ChEMBL / clinical)",
        source_type="real_public",
        source_id="per-component source ids (see target-ranking.json)",
        url="https://doi.org/",
        version="tcell-evidence-2026-07",
        peer_reviewed=True,
        preprocessing="expert-curated effect magnitudes from cited primary sources; "
                      "each component carries its own resolvable source id + label",
        qc="every component exposes source + evidence label + uncertainty + limitation",
        limitations=[
            "Reported effects, not re-derived from raw counts in this build.",
            "KT-621 (STAT6 degrader) is clinical-stage, not approved.",
        ],
        affects_ranking=True,
        affects_how="sets functional_effect, activation_specificity, type2_pathway, "
                    "tractability, safety/integrity risk (the composite drivers)",
    )


def _synthetic_classifier_entry() -> dict:
    """The SYNTHETIC single-cell matrix classifier — a labeled method cross-check
    that must NEVER touch the ranking."""
    try:
        from keystone.ml.th2_signature import run_analysis
        a = run_analysis()
        version = a["reproducibility"]["data_version"]
        qc = (f"{a['n_genes_excluded_qc']} genes excluded; "
              f"leave-one-perturbation-out CV (no cell leakage)")
        kind = a["data_kind"]
    except Exception as exc:
        version, qc, kind = "synthetic-th2-v1", f"pipeline error: {exc}", "synthetic"
    return _entry(
        name="Type-2 classifier pipeline (single-cell matrix)",
        source_type="synthetic_fixture" if kind == "synthetic" else "real_public",
        source_id="keystone/ml/th2_signature.py",
        url=None,
        version=version,
        peer_reviewed=None,
        preprocessing="matrix generated deterministically from the REAL type-2 "
                      "signature structure — NOT real Perturb-seq",
        qc=qc,
        limitations=[
            "SYNTHETIC matrix — exploratory only; replace via load_real_matrix() "
            "with a real .h5ad before any biological claim.",
            "Recovers the literature ordering as a sanity check; not a deployed model.",
        ],
        affects_ranking=False,
        affects_how="method cross-check ONLY — attached as functional_effect_crosscheck; "
                    "the composite is numerically independent of it "
                    "(proven by test_synthetic_cannot_affect_ranking)",
    )


def _atlas_entry() -> dict:
    """The Visual Evidence Lab Cell-State Atlas — a computed PCA embedding of the
    SYNTHETIC matrix. Illustrative; cannot affect the ranking."""
    try:
        from keystone.ml.cell_atlas import compute_atlas
        a = compute_atlas("tcell")
        version = a["reproducibility"]["data_version"] + " · " + a["run_id"]
        qc = f"{a['n_cells']} cells · PCA(2) · arms = perturbation ground-truth groups"
        synthetic = a["data_kind"] == "synthetic"
    except Exception as exc:
        version, qc, synthetic = "atlas-v1", f"atlas error: {exc}", True
    return _entry(
        name="Cell-State Atlas embedding (Visual Evidence Lab)",
        source_type="synthetic_fixture" if synthetic else "real_public",
        source_id="keystone/ml/cell_atlas.py",
        url=None,
        version=version,
        peer_reviewed=None,
        preprocessing="PCA (2-component, from-scratch SVD) of the synthetic type-2 "
                      "matrix; per-arm stats computed on selection",
        qc=qc,
        limitations=[
            "SYNTHETIC matrix — illustrative of method + arm separation, not real cells.",
            "PCA of a synthetic matrix is not evidence about real biology.",
            "Research use only — not clinical, not diagnostic.",
        ],
        affects_ranking=False,
        affects_how="visual evidence layer — links each arm to the real ranking + "
                    "measured Gladstone metrics, but is gated OUT of ranking support",
    )


def data_readiness(domain: str = "tcell") -> dict:
    """The full readiness manifest for a program. Defined for the flagship CD4+
    T-cell workflow; other programs report a short honest stub."""
    if domain != "tcell":
        return {
            "domain": domain,
            "note": "The Data Readiness gate is defined for the flagship CD4+ "
                    "T-cell (tcell) program.",
            "sources": [],
        }
    sources = [
        _gladstone_entry(),
        _opentargets_entry(),
        _literature_entry(),
        _synthetic_classifier_entry(),
        _atlas_entry(),
    ]
    counts = {t: sum(1 for s in sources if s["source_type"] == t) for t in SOURCE_TYPES}
    ranking_inputs = [s["name"] for s in sources if s["affects_ranking"]]
    excluded_from_ranking = [s["name"] for s in sources if not s["affects_ranking"]]
    return {
        "domain": domain,
        "sources": sources,
        "counts_by_type": counts,
        "ranking_inputs": ranking_inputs,
        "excluded_from_ranking": excluded_from_ranking,
        "invariant": ("Synthetic/exploratory outputs are marked affects_ranking:false "
                      "and the ranking composite is numerically independent of them."),
        "note": ("Every source is labeled by exactly what it is. Real data drives the "
                 "ranking; the synthetic classifier is a transparent cross-check that "
                 "cannot change the ranking. Preprints are flagged not-peer-reviewed."),
    }
