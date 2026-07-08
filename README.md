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

## The moat is a number, not a claim — on two domains

`calibrate.py` measures the load-bearing classifier against hand-labeled real
citing sentences. The **same classifier**, measured on two unrelated domains:

```
--domain gbm      ACCURACY = 0.818   (44 real GBM citing sentences)
--domain insulin  ACCURACY = 0.818   (44 real insulin-signalling sentences)
```

Two data points near-identical ⇒ "domain-agnostic by construction" is measured
fact, not a claim. Offline, no API key. The live `ClaudeReasoner` runs the
identical harness.

## It measures its own blind spots

`python -m keystone.agents.flaw_catch_eval` plants deterministic flaws (a false
retraction, a corrupted citing sentence, a hidden post-retraction flag, a hidden
reagent misidentification) into the graph and asks whether the agents catch them:

```
accuracy 0.714  precision 1.000  recall 0.500
caught: false-retraction-of-grounding, context-corruption
MISSED: hidden temporal + reagent flaws  (the Reviewer reads the flag the flaw
        clears — catching these needs re-verification against the connector)
```

An honest map of what the current agents catch and where they are blind.

## Quickstart

```bash
pip install -e .                       # or: pip install requests
python -m pytest                        # 17 tests: reproducibility + rules + real data
python run_workbench.py                 # full loop, offline, no API key -> demo_out/
python calibrate.py --domain gbm        # measured load-bearing agreement (GBM)
python calibrate.py --domain insulin    # ...and on the second domain
python -m keystone.agents.flaw_catch_eval   # do the agents catch planted flaws?

pip install fastapi uvicorn             # the Scientific Discovery OS + workbench
python -m keystone.ui.server            # -> http://127.0.0.1:8000  (Discovery OS)
                                        #    /workbench for the reasoning loop UI

python -m keystone.ui.graph_browser.build --domain gbm   # static graph browser
python -m http.server -d browser_out/gbm 8010            # -> http://127.0.0.1:8010

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
  gbm_spec.py             pinned REAL identifiers — GBM (single source of truth)
  insulin_spec.py         pinned REAL identifiers — insulin (second domain)
  data_gbm.py             builds the GBM graph from real connector output
  data_insulin.py         builds the insulin graph (same core types)
  reasoning_panel.py      why-panel / future-experiments / honest readiness
  replay.py               session replay (ordered, timestamped)
  agents/
    reasoner.py           HeuristicReasoner (offline, transparent) + interface
    claude_reasoner.py    ClaudeReasoner + PathwayFigureAgent (real API, vision)
    flaw_catch_eval.py    do the agents catch a planted flaw? (may call Claude)
  deterministic/
    stats.py              power analysis (refuses to fabricate n)
    propagation.py        doubt propagation (graph math)
    protocol.py           protocol completeness validator + checklist
    flaw_injection.py     plant one grounded flaw, immutably (no LLM)
  connectors/
    registry.py           OpenAlex, RetractionWatch, Cellosaurus, S2, UniProt
    http_cache.py         cache -> live -> fixture (never fabricates)
    capture.py            re-pins real fixtures
    fixtures/             committed real API responses
  artifacts/
    render.py             evidence graph / timeline / 3D structure
    reasoning_render.py   why-panel + future-experiments renderers
  calibration/
    gbm_citing_sentences.jsonl       44 hand-labeled real GBM sentences
    insulin_citing_sentences.jsonl   44 hand-labeled real insulin sentences
  artifacts/
    graph_export.py       lossless EvidenceGraph <-> JSON (projection only)
  workspace.py            Disease Workspace assembler — 13 Tier-1 tabs of real
                          data + honest Tier-2 scaffolds (every field tier-tagged)
  connectors/
    clinical.py           Tier-1 real: ClinicalTrials.gov, ChEMBL, Reactome, ClinVar
  deterministic/
    contradiction_mining.py  named loop stage over EdgeType.CONTRADICTS
    gap_detection.py         named loop stage (missing evidence + structural gaps)
    ledger_index.py          Scientific Memory — "has this been tried?" over Ledgers
  ui/
    server.py             FastAPI backend (pure projection of the engine)
    static/os.html        Scientific Discovery OS: research-question home,
                          Disease Workspace tabs, real trials/drugs/pathways/
                          variants, dashboard, 3D, scientific memory
    static/index.html     the reasoning-loop workbench (at /workbench)
    graph_browser/        static, S3-deployable browser: layer filter over
                          NodeType, doubt bands, full-text search (DEPLOY.md)
tests/                    smoke(7) + connectors(10) + ui(4) + flaw(7) + insulin(6)
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
