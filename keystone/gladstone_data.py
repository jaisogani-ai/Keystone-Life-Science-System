"""
keystone.gladstone_data
=======================
Loader for the REAL, pinned Gladstone–UCSF CD4+ T-cell Perturb-seq measurements.

Source (real, resolvable, not peer-reviewed):
  Zhu, Dann, Yan, …, Pritchard, Marson.
  "Genome-scale perturb-seq in primary human CD4+ T cells maps context-specific
   regulators of T cell programs and human immune traits." bioRxiv 2025.12.23.696273
  Gladstone-UCSF Institute of Genomic Immunology.

What is REAL here (measured in the study, pinned verbatim from the supplement):
  * per-regulator perturbation effect metrics (Supplementary Table 5) — number of
    downstream DE genes, on-target knockdown effect size, and CROSS-DONOR
    reproducibility, per culture condition, for the four ranked regulators.
  * the Th2-vs-Th1 signature (Supplementary Table 11, Ota 2021) — real log fold
    changes for the type-2 signature genes.

Honesty (non-negotiable):
  * This is a PREPRINT: ``source_record_verified`` is true (the record resolves and
    the numbers are the authors'), but the claims are NOT peer-reviewed — provisional.
  * These are MEASURED quantities, not causal estimates.
  * Cross-donor reproducibility is reported as-is: FBXO32's is low (~0.13), which is a
    real, measured reason to treat the preprint's FBXO32 nomination cautiously.
"""
from __future__ import annotations

import functools
import json
import pathlib

_FIXTURE = (pathlib.Path(__file__).parent / "connectors" / "fixtures"
            / "gladstone_cd4t_perturbseq.json")

RANKED_REGULATORS = ("GATA3", "STAT6", "RARA", "FBXO32")


@functools.lru_cache(maxsize=1)
def load() -> dict:
    """Return the pinned real Gladstone dataset (parsed). Raises if the fixture is
    missing — this is real data the product depends on, never silently faked."""
    with _FIXTURE.open() as fh:
        return json.load(fh)


def provenance() -> dict:
    """The full, resolvable source record for the dataset (DOI, authors, tables)."""
    return dict(load()["_provenance"])


def regulator_effect(gene: str, condition: str | None = None) -> dict | None:
    """Real measured perturbation metrics for one regulator in one culture condition
    (default: the polarization-relevant condition the study uses). Returns ``None``
    if the regulator was not measured — never a fabricated value."""
    data = load()
    cond = condition or data["polarization_condition"]
    per_reg = data["regulator_perturbation_effects"].get(gene)
    if not per_reg:
        return None
    row = per_reg.get(cond)
    if not row:
        return None
    return {**row, "gene": gene, "condition": cond}


def all_regulator_effects(condition: str | None = None) -> dict:
    """Real per-regulator metrics for every ranked regulator (measured; missing ones
    are reported as ``None`` rather than invented)."""
    return {g: regulator_effect(g, condition) for g in RANKED_REGULATORS}


def th2_signature() -> list[dict]:
    """The real Th2-vs-Th1 signature genes (log_fc + z-score), most Th2-enriched
    first. These are measured differential-expression values, not typed weights."""
    return list(load()["th2_signature_th2_vs_th1_ota2021"])


def gata3_th2_footprint() -> dict | None:
    """GATA3's REAL, direction-resolved effect on the type-2 signature genes —
    measured log2 fold-changes under GATA3 knockdown in the study (Suppl. Table 7,
    Stim8hr), for the 12 canonical type-2 genes. Includes the ``th2_collapse_score``
    (mean log2FC across measured signature genes — a real signature-shift, negative =
    the program collapses). This is measured differential expression, not a synthetic
    matrix and not a causal estimate. Returns ``None`` if the footprint is unpinned."""
    return load().get("gata3_th2_footprint")


def functional_effect_scores(condition: str | None = None) -> dict:
    """Per-regulator functional effect on the type-2 program, DERIVED FROM THE REAL
    DATA and normalised to 0..1 for the ranking's cross-check.

    Definition (transparent, reproducible): the breadth of a regulator's real
    transcriptional footprint — ``n_downstream`` DE genes in the polarization
    condition — min-max scaled across the ranked regulators. This is a MEASURED
    magnitude, not a causal or Th2-directional claim; direction/selectivity live in
    the separate sourced ranking components. Regulators the study did not measure are
    omitted (never imputed)."""
    effects = all_regulator_effects(condition)
    downstream = {g: e["n_downstream"] for g, e in effects.items()
                  if e and e.get("n_downstream") is not None}
    if not downstream:
        return {}
    lo, hi = min(downstream.values()), max(downstream.values())
    span = (hi - lo) or 1.0
    return {g: round((v - lo) / span, 3) for g, v in downstream.items()}
