"""
keystone.deterministic.protocol
==============================
Deterministic protocol validator + the reproducibility checklist. The Experiment
Design agent *proposes* a plan; this module *checks* it. That proposer/checker
split (semantic proposes, deterministic verifies) is the core trust primitive —
so nothing here calls an LLM.
"""
from __future__ import annotations

from keystone.core import ExperimentPlan

# Nine items a reproducible perturbation experiment should address. The readiness
# panel reports how many are addressable from the current plan (e.g. "5/9"); the
# rest are wet-lab execution details the scientist logs at the bench.
REPRO_CHECKLIST = [
    "positive control defined",
    "negative control defined",
    "isogenic / matched genetic background",
    "sample size grounded in a power analysis",
    "effect size sourced from a cited prior result",
    "randomization / blinding of readout",
    "pre-registered analysis plan",
    "independent biological replicates",
    "orthogonal method / rescue experiment",
]


def validate_protocol(plan: ExperimentPlan) -> list[str]:
    """Return a list of warnings (empty == clean). Checks completeness and the
    most common confounds; never raises — a warning informs the scientist, it
    does not silently block."""
    warnings: list[str] = []
    if not plan.positive_controls:
        warnings.append("no positive control specified")
    if not plan.negative_controls:
        warnings.append("no negative control specified")
    if plan.assumed_effect_size is None:
        warnings.append("effect size not grounded — power analysis is undefined")
    if plan.required_n_per_arm is None:
        warnings.append("no sample size (follows from missing effect size)")
    if not plan.kill_condition.strip():
        warnings.append("no falsifiable kill-condition")
    system = plan.system.lower()
    if "isogenic" not in system and "matched" not in system:
        warnings.append("system may not be isogenic — genetic-background confound")
    if plan.assumed_effect_size is not None and plan.assumed_effect_size >= 1.2:
        warnings.append("assumed effect size is large (>=1.2 d) — may be optimistic")
    return warnings
