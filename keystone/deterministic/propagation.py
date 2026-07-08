"""
keystone.deterministic.propagation
==================================
Doubt propagation as pure graph math — no LLM. Doubt flows from a doubted node
to everything that *depends on* it (cites / depends_on edges), attenuated by how
load-bearing that reliance is: an incidental citation barely inherits doubt, a
load-bearing one inherits most of it. Reliance recorded *after* a retraction is
"inexcusable" and saturates toward full doubt regardless of weight.

Constants chosen so the canonical demo reproduces the documented behaviour:
a load-bearing citer of a fully-retracted foundation inherits ~0.63, an
incidental citer ~0.20.
"""
from __future__ import annotations

from dataclasses import replace

from keystone.core import EvidenceGraph, Interval

# A small residual prior every empirical node carries, and the maximum share of a
# source's doubt a fully load-bearing edge transfers. Together: prior 0.08 with
# transfer 0.60 maps a source doubt of 1.0 to ~0.63 at w=1.0 and ~0.18 at w=0.22.
_PRIOR_FLOOR = 0.08
_TRANSFER = 0.60
_INEXCUSABLE_FLOOR = 0.90   # post-retraction reliance cannot look trustworthy


def _combine(prior: float, transfers: list[float]) -> float:
    """Saturating combination: doubt = 1 - (1-prior)·∏(1-tᵢ). Independent doubts
    accumulate but never exceed 1.0."""
    survive = 1.0 - min(max(prior, 0.0), 1.0)
    for t in transfers:
        survive *= (1.0 - min(max(t, 0.0), 1.0))
    return 1.0 - survive


def propagate_doubt(graph: EvidenceGraph) -> None:
    """Recompute every node's doubt from its dependencies. Replaces nodes with
    new immutable copies (never mutates in place). Idempotent given fixed edge
    weights, so re-runs are reproducible."""
    priors = {nid: n.doubt.point for nid, n in graph.nodes.items()}
    bands = {nid: (n.doubt.low, n.doubt.high) for nid, n in graph.nodes.items()}

    for nid, node in list(graph.nodes.items()):
        deps = graph.incoming_dependencies(nid)
        if not deps:
            continue
        transfers, transfers_lo, transfers_hi = [], [], []
        inexcusable = node.inexcusable
        for e in deps:
            src_doubt = priors.get(e.dst, 0.0)
            lo, hi = bands.get(e.dst, (src_doubt, src_doubt))
            w = e.load_bearing.point
            transfers.append(src_doubt * _TRANSFER * w)
            transfers_lo.append(lo * _TRANSFER * e.load_bearing.low)
            transfers_hi.append(hi * _TRANSFER * e.load_bearing.high)
            if e.temporal.value == "post_retraction" and graph.nodes[e.dst].retracted:
                inexcusable = True

        # A node's own intrinsic doubt is a floor: propagation only ADDS doubt
        # from doubtful dependencies, it never launders away a node's own doubt
        # (a retracted foundation stays fully doubted regardless of what it cites).
        prior = max(priors[nid], _PRIOR_FLOOR)
        point = _combine(prior, transfers)
        low = _combine(prior, transfers_lo)
        high = _combine(prior, transfers_hi)
        if inexcusable:
            point = max(point, _INEXCUSABLE_FLOOR)
            high = max(high, _INEXCUSABLE_FLOOR)
            low = max(low, _INEXCUSABLE_FLOOR - 0.05)

        graph.nodes[nid] = replace(
            node,
            doubt=Interval(round(point, 4), round(min(low, point), 4),
                           round(max(high, point), 4)).clamp(),
            inexcusable=inexcusable,
        )
