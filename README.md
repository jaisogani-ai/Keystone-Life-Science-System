# Keystone — AI Scientific Research Workbench

A trustworthy AI workbench that accelerates biomedical research while keeping
scientists fully in control. It runs one loop — **Plan → Collect → Analyze →
Hypothesize → Design Experiment → Review → Human Approval → Ledger** — over the
real evidence base, grounds every conclusion in a reproducible provenance graph,
forces every hypothesis to carry a falsifiable validation experiment, and has an
independent Reviewer agent challenge every conclusion.

**Demo domain:** glioblastoma. The engine is domain-agnostic by construction.

## This is built on *real* evidence

The demo is not synthetic. It is assembled live from public research databases
and pinned as offline fixtures:

- **Foundation:** a real 2004 *Oncogene* paper claiming RNAi knockdown of
  cathepsin B (CTSB) and MMP-9 suppresses glioblastoma invasion
  ([10.1038/sj.onc.1207616](https://doi.org/10.1038/sj.onc.1207616)) — **retracted
  2025-04-29** (Retraction Watch record 64194, confirmed via Crossref).
- **The moat, on real data:** real downstream citers with their *real Semantic
  Scholar citing sentences*, classified load-bearing vs. incidental. A citer that
  restates the retracted result inherits doubt **0.55**; an incidental one
  **0.21**; a citer that cited it **8 months after retraction** (Jan 2026) is
  flagged **inexcusable** (doubt 0.90).
- **Reagent doubt:** the U-87MG line ([Cellosaurus CVCL_0022](https://www.cellosaurus.org/CVCL_0022))
  carries its real, famous *misidentification* flag.
- **Target:** cathepsin B ([UniProt P07858](https://www.uniprot.org/uniprotkb/P07858)),
  rendered as a real 3D structure.

## The moat is a number, not a claim

`calibrate.py` measures the load-bearing classifier against **44 hand-labeled
real GBM citing sentences**:

```
ACCURACY = 0.773   (coin flip 0.500 | human-agreement band 0.69-0.75)
precision=0.889  recall=0.667
```

Offline, no API key. The live `ClaudeReasoner` runs the identical harness.

## Quickstart

```bash
pip install -e .                       # or: pip install requests
python -m pytest                        # 17 tests: reproducibility + rules + real data
python run_workbench.py                 # full loop, offline, no API key -> demo_out/
python calibrate.py                     # measured load-bearing agreement

pip install fastapi uvicorn             # the interactive workbench UI
python -m keystone.ui.server            # -> http://127.0.0.1:8000

# refresh the pinned real data from the live APIs:
KEYSTONE_LIVE=1 python -m keystone.connectors.capture

# run the semantic layer with real Claude agents (spends API budget):
KEYSTONE_LIVE=1 ANTHROPIC_API_KEY=... python run_workbench.py
```

## Structure

```
keystone/
  core.py                 data model + rule-3-enforced Hypothesis + Ledger
  workbench.py            orchestrator: the full loop + timeline projection
  gbm_spec.py             pinned REAL identifiers (single source of truth)
  data_gbm.py             builds the graph from real connector output
  reasoning_panel.py      why-panel / future-experiments / honest readiness
  replay.py               session replay (ordered, timestamped)
  agents/
    reasoner.py           HeuristicReasoner (offline, transparent) + interface
    claude_reasoner.py    ClaudeReasoner + PathwayFigureAgent (real API, vision)
  deterministic/
    stats.py              power analysis (refuses to fabricate n)
    propagation.py        doubt propagation (graph math)
    protocol.py           protocol completeness validator + checklist
  connectors/
    registry.py           OpenAlex, RetractionWatch, Cellosaurus, S2, UniProt
    http_cache.py         cache -> live -> fixture (never fabricates)
    capture.py            re-pins real fixtures
    fixtures/             committed real API responses
  artifacts/
    render.py             evidence graph / timeline / 3D structure
    reasoning_render.py   why-panel + future-experiments renderers
  calibration/
    gbm_citing_sentences.jsonl   44 hand-labeled real sentences
  ui/
    server.py             FastAPI backend (pure projection of the engine)
    static/index.html     one-page workbench: graph, why-panel, tree,
                          readiness, timeline, 3D, replay, approval gate
tests/                    test_smoke.py (7) + test_connectors.py (10) + test_ui.py (4)
run_workbench.py          end-to-end CLI
calibrate.py              the moat, measured
```

## Why a lab would trust it

Every conclusion is grounded in a cited node, carries a confidence interval, is
independently challenged, is human-gated, and lives in a version-pinned Ledger
that re-runs to an identical hash. Statistics are never fabricated. Identifiers
and citing sentences are never invented — a failed lookup is marked `unresolved`.
Computer vision is used only where scientifically justified, and refused
everywhere else, on the record. See [ARCHITECTURE.md](ARCHITECTURE.md) and
[CONTRIBUTING.md](CONTRIBUTING.md) (the semantic/deterministic boundary).
