"""
keystone.deterministic.stats
============================
Power analysis with no LLM and no scipy. The normal inverse-CDF is computed with
the Acklam rational approximation. Rule 7 in its sharpest form: the function
*refuses* to return a sample size when there is no grounded effect size — it will
not fabricate an ``n`` to look authoritative.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

# Acklam's algorithm coefficients (abs error < 1.15e-9 across the full range).
_A = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
      1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
_B = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
      6.680131188771972e+01, -1.328068155288572e+01]
_C = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
      -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
_D = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
      3.754408661907416e+00]
_P_LOW = 0.02425
_P_HIGH = 1 - _P_LOW


def norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (quantile function) via Acklam."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    if p < _P_LOW:
        q = math.sqrt(-2 * math.log(p))
        return (((((_C[0]*q+_C[1])*q+_C[2])*q+_C[3])*q+_C[4])*q+_C[5]) / \
               ((((_D[0]*q+_D[1])*q+_D[2])*q+_D[3])*q+1)
    if p <= _P_HIGH:
        q = p - 0.5
        r = q * q
        return (((((_A[0]*r+_A[1])*r+_A[2])*r+_A[3])*r+_A[4])*r+_A[5])*q / \
               (((((_B[0]*r+_B[1])*r+_B[2])*r+_B[3])*r+_B[4])*r+1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((_C[0]*q+_C[1])*q+_C[2])*q+_C[3])*q+_C[4])*q+_C[5]) / \
            ((((_D[0]*q+_D[1])*q+_D[2])*q+_D[3])*q+1)


def sample_size_two_arm(effect_size: Optional[float],
                        sd: Optional[float],
                        alpha: float = 0.05,
                        power: float = 0.80) -> Tuple[Optional[int], str]:
    """Two-arm sample size per group for a difference in means.

    Returns ``(n_per_arm, note)``. If ``effect_size`` (Cohen's d) is missing, the
    function REFUSES: it returns ``(None, <explanation>)`` rather than inventing a
    number. This is the anti-fabrication guarantee in code.
    """
    if effect_size is None or effect_size <= 0:
        return None, ("Sample size cannot be computed: no grounded effect size. "
                      "Provide a Cohen's d from a cited prior result before a "
                      "power analysis is meaningful.")
    z_alpha = norm_ppf(1 - alpha / 2.0)
    z_beta = norm_ppf(power)
    n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
    n_ceil = math.ceil(n)
    note = (f"n/arm={n_ceil} for d={effect_size}, alpha={alpha}, power={power} "
            f"(z_alpha/2={z_alpha:.3f}, z_beta={z_beta:.3f}). Two-sample, "
            f"two-sided, equal allocation.")
    return n_ceil, note
