"""
Spec acceptance test #7 — internal node ids (e.g. ``N_foundation``, ``N_dep_A``)
must NEVER surface in scientist-facing text. Structural id fields (a node's own
``id``, ``mechanism_path``) may carry them; rendered prose a scientist reads —
integrity findings, the adversary's objection, the reviewer's rationale — may not.

Exercises the deterministic path directly (no live model, no network) so the
guarantee is reproducible and fast.
"""
import re

from keystone.decision_engine import _spec_and_builder
from keystone.orchestrator import orchestrate
from keystone.agents.reasoner import HeuristicReasoner
from keystone.integrity_center import run_integrity_center

# an internal node id looks like N_foundation / N_dep_A / N_reagent / N_molecular
_INTERNAL_ID = re.compile(r"\bN_[A-Za-z]")

# fields a scientist actually reads — NOT structural id arrays (mechanism_path…)
_PROSE_FIELDS = ("output", "role", "challenged_assumption", "why_disagrees",
                 "remaining_uncertainty", "detail")


def _assert_clean(where: str, text) -> None:
    assert not _INTERNAL_ID.search(str(text or "")), \
        f"internal node id leaked into rendered {where}: {text!r}"


def test_integrity_center_details_have_no_internal_ids():
    """The Integrity Gate a scientist reads must name findings, not N_ ids."""
    intg = run_integrity_center("gbm")
    assert intg["checks"], "integrity should produce checks"
    for c in intg["checks"]:
        _assert_clean("integrity check detail", c.get("detail"))


def test_reasoning_trace_prose_has_no_internal_ids():
    """The multi-agent trace (incl. the adversary's challenge) must be human-
    readable — the exact leak fixed in orchestrator/reasoner/integrity."""
    spec, build = _spec_and_builder("gbm")
    trace, _ledger, _hyp, _review = orchestrate(
        spec.QUESTION, build(), HeuristicReasoner())
    assert trace, "orchestrator should produce a trace"
    saw_adversary = False
    for step in trace:
        for f in _PROSE_FIELDS:
            _assert_clean(f"agent_trace.{f}", step.get(f))
        for obj in step.get("objections", []) or []:
            _assert_clean("agent_trace.objections", obj)
        if step.get("challenged_assumption"):
            saw_adversary = True
    # the adversary seat must have run — otherwise the test proves nothing
    assert saw_adversary, "expected an adversary step with a challenged_assumption"


def test_boundary_sanitizer_scrubs_model_echoed_ids():
    """The live path can't be unit-tested for what Claude writes, but the API
    boundary sanitizer must strip any internal id a model echoes into prose —
    replacing it with the human label (spec #7, defence-in-depth)."""
    from keystone.ui import server
    from keystone.core import node_label
    from keystone.data_gbm import build_gbm_graph

    graph = build_gbm_graph()
    id_to_label = {nid: node_label(n) for nid, n in graph.nodes.items()}
    some_id = next(iter(graph.nodes))                       # a real internal id
    echoed = f"Doubt scores indicate {some_id} is fully retracted (1.00)."

    out = server._humanize_ids(echoed, id_to_label)
    assert some_id not in out, f"id {some_id} survived sanitization: {out!r}"
    assert id_to_label[some_id] in out, "label should replace the id"
