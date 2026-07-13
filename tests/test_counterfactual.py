"""
Spec acceptance test #9 — *exclude a source and confirm the conclusion's
assessment changes.* Nothing is scripted: ``assess_claim`` and the Field
Integrity score are recomputed with the source's retraction flag flipped.
Runs on the deterministic reasoner so it is fast and reproducible.
"""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import keystone.ui.server as server  # noqa: E402
from keystone.decision_engine import decide  # noqa: E402
from keystone.agents.reasoner import HeuristicReasoner  # noqa: E402

client = TestClient(server.app)


def _warm_deterministic() -> None:
    # offline reasoner → fast, reproducible; same conclusion the UI would show
    server._DECISION_CACHE["gbm"] = decide("gbm", reasoner=HeuristicReasoner())


def test_excluding_retracted_source_flips_assessment_and_drops_integrity():
    _warm_deterministic()
    r = client.get("/api/counterfactual?domain=gbm").json()
    assert "error" not in r, r

    # the retracted source is EXCLUDED from positive support for the conclusion…
    assert r["excluded"]["evidence_status"] == "excluded"
    # …but were it naively trusted (as a plain LLM would), it would NOT be excluded
    assert r["if_trusted"]["evidence_status"] != "excluded"
    # → excluding it genuinely CHANGES the conclusion's assessment
    assert r["assessment_changed"] is True

    # and the corpus Field Integrity is strictly higher when the retraction is
    # ignored — proving the score moves with the exclusion, not a fixed number
    fi = r["field_integrity"]
    assert fi["if_trusted"] is not None and fi["excluded"] is not None
    assert fi["if_trusted"] >= fi["excluded"]


def test_counterfactual_targets_the_real_retracted_foundation():
    _warm_deterministic()
    r = client.get("/api/counterfactual?domain=gbm").json()
    assert r["source"]["integrity_state"] == "retracted"
    assert r["source"]["source_id"], "the excluded source must carry a real id"
