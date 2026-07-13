"""
Secret-boundary tests — the Anthropic API key is server-side only. It must never
appear in the static frontend bundle, in any API response, or in a server error.
"""
import glob
import json
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

import pytest  # noqa: E402

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from keystone.ui import server                                          # noqa: E402
from keystone.data_gbm import build_gbm_graph                           # noqa: E402
from keystone.artifacts.graph_export import graph_to_dict               # noqa: E402

_SENTINEL = "sk-ant-api03-TESTSENTINEL-must-not-leak-0000"


def test_no_key_literal_in_static_assets():
    """No `sk-ant`-shaped literal anywhere the browser can fetch."""
    for path in glob.glob("keystone/ui/static/**/*", recursive=True):
        if os.path.isfile(path):
            txt = open(path, encoding="utf-8", errors="ignore").read()
            assert "sk-ant" not in txt, f"key-shaped literal in {path}"


def test_key_never_in_api_responses_or_errors(monkeypatch):
    """With a key configured, it must not leak through any endpoint — success,
    not-found, or a triggered server error. Stays offline (no real Claude call)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", _SENTINEL)
    monkeypatch.setenv("KEYSTONE_OFFLINE", "1")
    client = TestClient(server.app, raise_server_exceptions=False)
    for p in ("/", "/healthz", "/api/program?domain=gbm", "/api/decision?domain=gbm",
              "/api/import/sample?kind=gbm", "/does-not-exist",
              "/api/program?domain=@@nonsense@@"):
        r = client.get(p)
        assert _SENTINEL not in r.text, f"key leaked in GET {p}"
    r = client.post("/api/import", json={"unexpected": "payload"})
    assert _SENTINEL not in r.text, "key leaked in a POST error response"


def test_bundle_and_graph_dict_carry_no_key(monkeypatch):
    """The data the browser receives never contains the key value."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", _SENTINEL)
    blob = json.dumps(graph_to_dict(build_gbm_graph(live=False)))
    assert _SENTINEL not in blob and "sk-ant" not in blob
