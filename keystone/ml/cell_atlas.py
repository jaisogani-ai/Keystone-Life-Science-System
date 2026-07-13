"""
keystone.ml.cell_atlas
======================
The **Keystone Visual Evidence Lab — Cell-State Atlas** (Mode 1). A CELLxGENE-style
low-dimensional embedding of the type-2 (Th2) perturbation experiment: one point per
cell, colourable by perturbation arm / type-2 signature / donor / QC, with each
perturbation arm linked to the real ranking, graph nodes, and the REAL measured
Gladstone metrics.

HONESTY (non-negotiable — the whole point of a Visual Evidence Lab is trustworthy
visuals):
  * The per-cell MATRIX is the same **SYNTHETIC** matrix the classifier uses
    (``th2_signature.synthesize_matrix``). The 2-D embedding is a REAL, deterministic
    PCA of it — but the underlying cells are synthetic, so every panel is tagged
    ``Computed analysis · SYNTHETIC / illustrative`` and it **cannot** be ranking
    evidence. Point ``load_real_matrix()`` at a real .h5ad to promote it.
  * The per-arm **measured** metrics (downstream DE, on-target KD, cross-donor r) are
    the REAL Gladstone–UCSF preprint measurements — tagged ``Measured data`` and
    flagged preprint. They anchor each cluster in real data.
  * "clusters" are the ground-truth **perturbation arms**, not de-novo Leiden clusters
    — named as such, never dressed up as discovered structure.
  * This is NOT radiology. No diagnosis, no patient, no clinical segmentation, no
    tumor measurement. The atlas carries an explicit non-clinical disclaimer.

Provenance tags used on every panel: ``Measured data`` | ``Computed analysis`` |
``Literature-backed biology`` | ``Illustrative context`` | ``Missing / unavailable``.
"""
from __future__ import annotations

import hashlib

import numpy as np

_NON_CLINICAL = ("Research use only. Not a clinical or diagnostic tool. No patient, "
                 "diagnosis, tumor measurement, or treatment claim is made or possible.")
_DOES_NOT_PROVE = [
    "The embedding is a PCA of a SYNTHETIC matrix — it illustrates method + arm "
    "separation, it is not evidence about real cells.",
    "Arm separation here does not establish causality or a real effect size.",
    "It cannot, by itself, change the target ranking (illustrative, gated out).",
]


def load_real_matrix():
    """Hook to swap in a real single-cell matrix (.h5ad). Returns None — the repo
    ships no real per-cell Perturb-seq matrix, so the atlas runs on the clearly
    labelled synthetic matrix and says so. Wire a real loader here to go live."""
    return None


def _pca2(X: np.ndarray) -> np.ndarray:
    """Deterministic 2-component PCA via SVD (numpy only). Returns Nx2 coordinates."""
    Xc = X - X.mean(0)
    U, S, _Vt = np.linalg.svd(Xc, full_matrices=False)
    return U[:, :2] * S[:2]


def _ranking_linkage() -> dict:
    """gene → {node_id, rank, composite} from the real transparent ranking."""
    try:
        from keystone.deterministic.target_ranking import rank_targets
        return {r["gene"]: {"node_id": r["node_id"], "rank": r["rank"],
                            "composite": r["composite"]}
                for r in rank_targets()["ranking"]}
    except Exception:
        return {}


def _measured(gene: str) -> dict | None:
    """Real measured Gladstone metrics for an arm's regulator (or None for control)."""
    try:
        from keystone import gladstone_data
        e = gladstone_data.regulator_effect(gene)
        if not e:
            return None
        return {"n_downstream_de_genes": e.get("n_downstream"),
                "ontarget_effect_size": e.get("ontarget_effect_size"),
                "crossdonor_reproducibility": e.get("crossdonor_correlation_mean"),
                "source": f"DOI:{gladstone_data.provenance()['doi']}",
                "peer_reviewed": gladstone_data.provenance().get("peer_reviewed"),
                "label": "Measured data"}
    except Exception:
        return None


def _arm_stats(arm, coords, sig, qc, group, ctrl_mean, link, gene) -> dict:
    mask = group == arm
    n = int(mask.sum())
    mean_sig = float(sig[mask].mean())
    is_ctrl = arm == "NTC"
    measured = None if is_ctrl else _measured(gene)
    integrity = ("control (non-targeting)" if is_ctrl else
                 "preprint — not peer-reviewed" if gene == "FBXO32" else "peer-reviewed")
    return {
        "arm": arm,
        "gene": None if is_ctrl else gene,
        "n_cells": n,
        "centroid": [round(float(coords[mask, 0].mean()), 3),
                     round(float(coords[mask, 1].mean()), 3)],
        # COMPUTED (on the synthetic matrix) — illustrative, never ranking evidence
        "computed": {
            "mean_type2_signature": round(mean_sig, 3),
            "delta_vs_control": round(mean_sig - ctrl_mean, 3),
            "mean_qc_signal": round(float(qc[mask].mean()), 3),
            "label": "Computed analysis · SYNTHETIC / illustrative",
        },
        # MEASURED (real Gladstone preprint) — anchors the arm in real data
        "measured": measured,
        # LITERATURE-backed ranking linkage
        "linkage": (None if is_ctrl else {
            "node_id": (link.get(gene) or {}).get("node_id"),
            "rank": (link.get(gene) or {}).get("rank"),
            "composite": (link.get(gene) or {}).get("composite"),
            "label": "Literature-backed biology",
        }),
        "integrity_state": integrity,
        "affects_ranking": False,   # illustrative visual — gated out of ranking
    }


def _run_id(domain: str, data_kind: str, salt: str = "") -> str:
    return "atlas_" + hashlib.sha256(
        f"{domain}:{data_kind}:{salt}".encode()).hexdigest()[:12]


def compute_atlas(domain: str = "tcell", cells_per_arm: int = 80) -> dict:
    """Compute the Cell-State Atlas for a program. Defined for the flagship CD4+
    T-cell program; other programs get an honest stub."""
    if domain != "tcell":
        return {"domain": domain, "available": False,
                "note": "The Cell-State Atlas is defined for the flagship CD4+ "
                        "T-cell (tcell) program.", "cells": [], "arms": []}
    from keystone.ml.th2_signature import (synthesize_matrix, signature_score,
                                           TH2_SIGNATURE_GENES, SEED, DATA_VERSION)
    real = load_real_matrix()
    is_synthetic = real is None
    X, y, group, donor, genes, sig_idx = real or synthesize_matrix(
        SEED, cells_per_arm=cells_per_arm)

    coords = _pca2(X)
    sig = signature_score(X, sig_idx)
    qc = np.abs(X).sum(1)                       # per-cell total signal (QC proxy)
    ctrl_mean = float(sig[group == "NTC"].mean())

    # normalise coords + sig + qc to friendly 0..1 ranges for the client
    def _norm(a):
        lo, hi = float(a.min()), float(a.max())
        return (a - lo) / ((hi - lo) or 1.0)
    nx, ny, nsig, nqc = _norm(coords[:, 0]), _norm(coords[:, 1]), _norm(sig), _norm(qc)

    cells = [{"x": round(float(nx[i]), 4), "y": round(float(ny[i]), 4),
              "arm": str(group[i]), "donor": str(donor[i]),
              "sig": round(float(nsig[i]), 4), "qc": round(float(nqc[i]), 4)}
             for i in range(len(group))]

    link = _ranking_linkage()
    gene_for = {"GATA3": "GATA3", "STAT6": "STAT6", "RARA": "RARA",
                "FBXO32": "FBXO32", "NTC": "NTC"}
    arms = [_arm_stats(a, coords, sig, qc, group, ctrl_mean, link, gene_for.get(a, a))
            for a in ["NTC", "GATA3", "STAT6", "RARA", "FBXO32"] if (group == a).any()]

    code_hash = None
    try:
        import pathlib
        code_hash = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]
    except Exception:
        code_hash = "unavailable"

    return {
        "domain": domain,
        "available": True,
        "data_kind": "synthetic" if is_synthetic else "real",
        "provenance_tag": ("Computed analysis · SYNTHETIC / illustrative"
                           if is_synthetic else "Computed analysis · real matrix"),
        "data_label": ("PCA embedding of a SYNTHETIC single-cell matrix built from the "
                       "real type-2 signature — illustrative of method + arm "
                       "separation, NOT real Perturb-seq and NOT ranking evidence."
                       if is_synthetic else "real dataset"),
        "embedding": {"method": "PCA (2 components, from-scratch SVD)",
                      "n_components": 2, "label": "Computed analysis"},
        "colorings": [
            {"id": "arm", "name": "Perturbation arm", "kind": "categorical"},
            {"id": "sig", "name": "Type-2 signature score", "kind": "computed"},
            {"id": "qc", "name": "QC signal (proxy)", "kind": "computed"},
            {"id": "donor", "name": "Donor (batch)", "kind": "categorical"},
        ],
        "signature_genes": TH2_SIGNATURE_GENES,
        "n_cells": len(cells),
        "cells": cells,
        "arms": arms,
        "run_id": _run_id(domain, "synthetic" if is_synthetic else "real"),
        "reproducibility": {"seed": hex(SEED), "code_hash": code_hash,
                            "numpy": np.__version__, "data_version": DATA_VERSION},
        "does_not_prove": _DOES_NOT_PROVE,
        "not_clinical": _NON_CLINICAL,
        "note": ("A CELLxGENE-style atlas: one point per cell, coloured by metadata. "
                 "The embedding is computed; the matrix is synthetic (illustrative); "
                 "each arm links to the REAL measured Gladstone metrics + the ranking."),
    }


def regulator_map(domain: str = "tcell") -> dict:
    """The Visual Evidence Lab's PRIMARY layer: a REAL measured-data map of the ranked
    regulators from the pinned Gladstone Perturb-seq metrics — nothing synthetic. Each
    regulator is positioned by its **measured** cross-donor reproducibility (x) and
    downstream DE-gene count (y), sized by on-target knockdown. This makes the ranking's
    weakest link visible: FBXO32 has a large footprint at very low reproducibility
    (r≈0.13) — the measured reason its preprint nomination stays provisional."""
    if domain != "tcell":
        return {"domain": domain, "available": False,
                "note": "The Regulator Effect Map is defined for the flagship CD4+ "
                        "T-cell (tcell) program.", "points": []}
    from keystone import gladstone_data
    prov = gladstone_data.provenance()
    link = _ranking_linkage()
    threshold = 0.3   # cross-donor r below which an effect is "not reproducible"
    points = []
    for gene, e in gladstone_data.all_regulator_effects().items():
        if not e:
            continue
        r = e.get("crossdonor_correlation_mean")
        lk = link.get(gene) or {}
        points.append({
            "gene": gene,
            "n_downstream_de": e.get("n_downstream"),
            "crossdonor_r": (round(r, 3) if r is not None else None),
            "r_measured": r is not None,
            "ontarget_kd": e.get("ontarget_effect_size"),
            "rank": lk.get("rank"),
            "composite": lk.get("composite"),
            "node_id": lk.get("node_id"),
            # provisional = a real, MEASURED fragility: reproducibility below threshold
            "provisional": (r is not None and r < threshold),
            "reproducibility_missing": r is None,
        })
    points.sort(key=lambda p: (p["rank"] is None, p["rank"]))
    return {
        "domain": domain,
        "available": True,
        "provenance_tag": "Measured data",
        "dataset": "Gladstone–UCSF CD4+ T-cell genome-scale Perturb-seq",
        "source": f"DOI:{prov['doi']}",
        "peer_reviewed": prov.get("peer_reviewed"),
        "condition": gladstone_data.load().get("polarization_condition"),
        "axes": {"x": "cross-donor reproducibility (Pearson r)",
                 "y": "downstream DE genes (n)",
                 "size": "on-target knockdown magnitude"},
        "reproducibility_threshold": threshold,
        "points": points,
        "insight": ("FBXO32 has a large footprint (747 DE genes) at the lowest cross-donor "
                    "reproducibility (r≈0.13) and weakest knockdown — a MEASURED reason its "
                    "preprint nomination stays provisional. STAT6/GATA3 replicate across "
                    "donors (r≈0.72–0.74)."),
        "does_not_prove": [
            "A measured effect size is not a causal or clinical claim.",
            "Cross-donor r reflects reproducibility, not biological importance alone.",
            "These are preprint measurements — real, but not yet peer-reviewed.",
        ],
        "not_clinical": _NON_CLINICAL,
    }


def cluster_detail(domain: str, arm: str, cells_per_arm: int = 80) -> dict:
    """Server-side computation for ONE selected arm — the real state change a
    selection triggers (never a purely visual update). Recomputes the arm's stats
    on demand and returns its full provenance + linkage + a selection run id."""
    atlas = compute_atlas(domain, cells_per_arm=cells_per_arm)
    if not atlas.get("available"):
        return {"domain": domain, "arm": arm, "available": False,
                "note": atlas.get("note")}
    match = next((a for a in atlas["arms"] if a["arm"] == arm), None)
    if match is None:
        return {"domain": domain, "arm": arm, "found": False,
                "note": f"no perturbation arm '{arm}' in this atlas"}
    return {
        "domain": domain,
        "arm": arm,
        "found": True,
        "selection_run_id": _run_id(domain, atlas["data_kind"], salt=f"select:{arm}"),
        "atlas_run_id": atlas["run_id"],
        "detail": match,
        "does_not_prove": _DOES_NOT_PROVE,
        "not_clinical": _NON_CLINICAL,
        "reviewer_note": ("Illustrative visual (synthetic matrix) — the Reviewer Agent "
                          "admits it for display only; it cannot become primary ranking "
                          "support. Real measured metrics for this arm are shown above."),
    }
