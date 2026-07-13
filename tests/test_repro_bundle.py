"""
Spec acceptance test #8 — the reproducibility export must contain dataset, code,
environment, model, prompt, and run metadata so a reviewer can re-run it. Runs on
the deterministic reasoner so it is fast and reproducible.
"""
import io
import json
import zipfile

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import keystone.ui.server as server  # noqa: E402
from keystone.decision_engine import decide  # noqa: E402
from keystone.agents.reasoner import HeuristicReasoner  # noqa: E402

client = TestClient(server.app)

_EXPECTED = {"README.md", "sources.csv", "claims.json", "assessments.json",
             "graph.json", "dataset-manifest.json", "environment.txt",
             "run-manifest.json", "experiment-plan.md"}


def _warm() -> None:
    server._DECISION_CACHE["gbm"] = decide("gbm", reasoner=HeuristicReasoner())


def _bundle():
    _warm()
    r = client.get("/api/export/bundle?domain=gbm")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/zip")
    return zipfile.ZipFile(io.BytesIO(r.content))


def test_bundle_is_a_zip_with_all_reproducibility_files():
    assert _EXPECTED <= set(_bundle().namelist())


def test_run_manifest_carries_dataset_code_model_prompt_run_metadata():
    m = json.loads(_bundle().read("run-manifest.json"))
    for k in ("dataset_version", "code_version", "evidence_hash", "model",
              "prompt_version", "seed", "graph_hash", "environment",
              "generated_at", "reviewer"):
        assert k in m, f"run-manifest missing {k}"
    assert m["environment"].get("python"), "environment must record the python version"
    # code_version is the real git commit to check out (or an honest 'unavailable'),
    # never the evidence hash masquerading as a code version.
    assert m["code_version"].startswith("git:") or "unavailable" in m["code_version"]


def test_bundle_carries_dataset_manifest_and_environment():
    z = _bundle()
    manifest = json.loads(z.read("dataset-manifest.json"))
    assert manifest["datasets"], "dataset manifest must name the real datasets/papers"
    assert all(d.get("source_id") for d in manifest["datasets"])
    env = z.read("environment.txt").decode()
    assert env.startswith("python=") and "anthropic=" in env


def test_exported_assessments_exclude_the_retracted_source():
    z = _bundle()
    claims = json.loads(z.read("claims.json"))
    assessments = json.loads(z.read("assessments.json"))
    assert claims and isinstance(claims, dict)
    assert isinstance(assessments, list) and assessments
    # the retracted foundation must be EXCLUDED in the export, never positive support
    assert "excluded" in {a["evidence_status"] for a in assessments}
