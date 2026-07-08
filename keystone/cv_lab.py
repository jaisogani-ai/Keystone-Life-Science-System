"""
keystone.cv_lab
=============
Computer Vision Lab — with the integrity boundary that makes it trustworthy.

Claude Vision is used ONLY where it is scientifically justified: reading a
pathway / mechanism / protein-interaction FIGURE to judge whether a doubtful
result is structurally central (the existing PathwayFigureAgent). That is the
one CV capability the design permits.

Extracting MEASUREMENTS from microscopy, CryoEM, western blots, histology, or
radiology is REFUSED — on the record — because it needs a validated
per-modality model and ground truth Keystone does not have; being wrong in
oncology is a harm, not a bug. The refusal returns a structured explanation, not
a fake detection. The lab draws the line and shows why.
"""
from __future__ import annotations

import os

# What Claude Vision may read (a real figure), and what it must refuse.
SUPPORTED = {
    "pathway_figure": "pathway diagram — judge structural centrality of a claim",
    "mechanism_diagram": "mechanism diagram — same justified figure-reading task",
    "protein_interaction_diagram": "interaction diagram — figure-reading task",
}
REFUSED = {
    "microscopy": "cell/protein detection and measurement extraction from "
                  "microscopy needs a validated per-modality model + ground "
                  "truth; not available — refused (no fabricated detections)",
    "cryoem": "CryoEM (.mrc/.map) has no wired source (EMDB/EMPIAR) and no "
              "validated interpretation model — refused, not faked",
    "western_blot": "band quantification needs a validated densitometry model "
                    "with controls — refused (a wrong number here misleads)",
    "histology": "histopathology interpretation is a clinical-grade task needing "
                 "a validated model — refused",
    "radiology": "radiology interpretation is diagnosis — out of scope, refused",
    "spatial_transcriptomics": "spatial-omics needs a real dataset source "
                               "(CELLxGENE/GEO) not wired — refused",
}


def modality_catalogue() -> list[dict]:
    """Every modality with an honest status — supported (Claude vision) or
    refused (with the reason). Never a silent gap."""
    cat = [{"modality": m, "status": "supported", "detail": d}
           for m, d in SUPPORTED.items()]
    cat += [{"modality": m, "status": "refused", "detail": d}
            for m, d in REFUSED.items()]
    return cat


def analyze(modality: str, claim: str = "", image_bytes: bytes | None = None,
            media_type: str = "image/png") -> dict:
    """Analyze an uploaded scientific image. Refuses unsupported modalities;
    runs pathway-figure vision (live Claude) for supported ones. Offline / no
    key returns an honest 'requires live vision' state — never a fabricated
    detection."""
    modality = (modality or "").lower().strip()

    if modality in REFUSED:
        return {"resolved": False, "refused": True, "modality": modality,
                "reason": REFUSED[modality],
                "boundary": "CV is used only where a validated model exists; "
                            "Keystone will not fabricate a measurement."}

    if modality not in SUPPORTED:
        return {"resolved": False, "refused": True, "modality": modality,
                "reason": f"unknown modality '{modality}'. Supported: "
                          f"{', '.join(SUPPORTED)}. All measurement-extraction "
                          f"modalities are refused by policy."}

    # supported figure-reading — needs live Claude vision + a key
    if os.environ.get("KEYSTONE_LIVE") != "1" or not os.environ.get("ANTHROPIC_API_KEY"):
        return {"resolved": False, "requires_live_vision": True,
                "modality": modality,
                "note": "pathway-figure reading runs on Claude vision — set "
                        "KEYSTONE_LIVE=1 + ANTHROPIC_API_KEY. Nothing is inferred "
                        "offline (no fabricated figure interpretation)."}
    if not image_bytes:
        return {"resolved": False, "error": "no image provided"}

    from keystone.agents.claude_reasoner import PathwayFigureAgent
    result = PathwayFigureAgent().assess_figure(image_bytes, media_type, claim)
    # mark provenance + require the human gate (rule 1)
    result.update({"modality": modality, "model_generated": True,
                   "provenance": "Claude vision (PathwayFigureAgent)",
                   "human_verification_required": True})
    return result
