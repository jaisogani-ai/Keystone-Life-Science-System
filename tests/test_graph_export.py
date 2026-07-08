"""
Graph-export tests. The export is a projection and MUST round-trip the graph
without loss (rule 3 — the browser renders exactly what the engine computed, and
must never need to recompute anything). Offline.
"""
import os

os.environ["KEYSTONE_OFFLINE"] = "1"

import json  # noqa: E402

from keystone.data_gbm import build_gbm_graph                        # noqa: E402
from keystone.data_insulin import build_insulin_graph                # noqa: E402
from keystone.artifacts.graph_export import graph_to_dict, graph_from_dict  # noqa: E402


def _roundtrip_lossless(build):
    g = build()
    once = graph_to_dict(g)
    twice = graph_to_dict(graph_from_dict(once))
    assert once == twice                                   # lossless
    assert once["hash"] == g.snapshot_hash()               # hash preserved
    # intervals and integrity flags survive intact
    reb = graph_from_dict(once)
    for nid, n in g.nodes.items():
        r = reb.nodes[nid]
        assert (r.doubt.point, r.doubt.low, r.doubt.high) == \
               (n.doubt.point, n.doubt.low, n.doubt.high)
        assert r.retracted == n.retracted and r.inexcusable == n.inexcusable
        assert r.node_type == n.node_type


def test_gbm_export_round_trips_without_loss():
    _roundtrip_lossless(build_gbm_graph)


def test_insulin_export_round_trips_without_loss():
    _roundtrip_lossless(build_insulin_graph)


def test_export_is_json_serializable_and_carries_the_layer_axis():
    d = graph_to_dict(build_gbm_graph())
    json.dumps(d)                                          # must be serializable
    assert "node_types" in d and "paper" in d["node_types"]
    # every node exposes its NodeType (the browser's 'layer' axis) + doubt band
    for n in d["nodes"]:
        assert n["node_type"] in d["node_types"]
        assert {"point", "low", "high"} <= set(n["doubt"])
    for e in d["edges"]:
        assert {"point", "low", "high"} <= set(e["load_bearing"])


def test_browser_build_emits_static_bundle(tmp_path):
    from keystone.ui.graph_browser.build import build
    out = build("gbm", tmp_path / "b")
    for f in ("index.html", "graph.js", "graph.json", "why_panel.html",
              "future_experiments.svg", "evidence_graph.svg"):
        assert (out / f).exists(), f"missing {f}"
    assert "KEYSTONE_GRAPH" in (out / "graph.js").read_text()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn) and name != "tmp_path":
            try:
                fn()
            except TypeError:
                import tempfile, pathlib
                fn(pathlib.Path(tempfile.mkdtemp()))
            print(f"  ok  {name}")
    print("all graph-export tests passed")
