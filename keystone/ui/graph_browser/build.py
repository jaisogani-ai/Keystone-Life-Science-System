"""
keystone.ui.graph_browser.build
==============================
Assemble the static Evidence Graph Browser bundle — a deterministic projection of
one workbench run. Emits a self-contained directory ready for ``aws s3 sync``:

    graph.js               window.KEYSTONE_GRAPH = <graph_to_dict output>
    graph.json             same payload, for programmatic use
    why_panel.html         linked from the browser (existing artifact)
    future_experiments.svg linked from the browser (existing artifact)
    evidence_graph.svg     the doubt-coloured graph render
    index.html             the browser (copied)

    python -m keystone.ui.graph_browser.build --domain gbm --out browser_out/gbm

No new computation happens here or in the browser — everything is read off the
graph/ledger the engine already produced (CONTRIBUTING rule 3).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from keystone.workbench import run
from keystone.reasoning_panel import why_panel, future_experiments_tree
from keystone.artifacts.graph_export import graph_to_dict
from keystone.artifacts.render import evidence_graph_svg
from keystone.artifacts.reasoning_render import (why_panel_html,
                                                 future_experiments_svg)

_HERE = Path(__file__).parent


def _build_graph(domain: str):
    if domain == "insulin":
        from keystone.data_insulin import build_insulin_graph
        from keystone.insulin_spec import QUESTION
        return build_insulin_graph(), QUESTION
    from keystone.data_gbm import build_gbm_graph
    from keystone.gbm_spec import QUESTION
    return build_gbm_graph(), QUESTION


def build(domain: str, out: Path) -> Path:
    from keystone.agents.reasoner import HeuristicReasoner
    graph, question = _build_graph(domain)
    ledger, hyp, review = run(question, graph, HeuristicReasoner())

    out.mkdir(parents=True, exist_ok=True)
    payload = graph_to_dict(graph)
    payload["question"] = question
    payload["hash"] = ledger.graph_hash
    (out / "graph.json").write_text(json.dumps(payload, indent=2))
    (out / "graph.js").write_text(
        "window.KEYSTONE_GRAPH = " + json.dumps(payload) + ";")
    (out / "why_panel.html").write_text(why_panel_html(why_panel(hyp, review, graph)))
    (out / "future_experiments.svg").write_text(
        future_experiments_svg(future_experiments_tree(hyp, graph)))
    (out / "evidence_graph.svg").write_text(evidence_graph_svg(graph))
    shutil.copy(_HERE / "index.html", out / "index.html")
    print(f"built graph browser [{domain}] -> {out}/  (hash {ledger.graph_hash})")
    print(f"  preview locally: python -m http.server -d {out}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=["gbm", "insulin"], default="gbm")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    out = Path(args.out) if args.out else Path("browser_out") / args.domain
    build(args.domain, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
