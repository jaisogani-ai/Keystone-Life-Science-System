# Keystone — Scientific Decision Engine

**Keystone answers one question: what should the scientist do next — and why,
over every alternative?** It is the reasoning layer that sits on top of a research
workbench: it generates *competing* hypotheses, scores each on real decision
dimensions, and ranks the experiments so a PI knows which one to run before
spending six months and $500k.

The trust guarantee that makes the ranking usable: **every score is computed,
a transparent estimate, or an explicit qualitative label — never fabricated.**
Expected information gain, cost, duration, and risk are deterministic models with
their assumptions shown (like the power analysis computes `n` from a stated
effect size). A ranking built on invented numbers is decoration; this one is
auditable.

Under the decision engine is the evidence engine — one loop (**Plan → Collect →
Analyze → Hypothesize → Design → Review → Human Approval → Ledger**) over a
reproducible, content-hashed provenance graph, with an independent Reviewer that
challenges every conclusion. **Demo domains:** glioblastoma and insulin
resistance. Domain-agnostic by construction (measured: 0.818 on both).

## The decision engine

`python -m keystone.decision_engine` (or the UI home `/`) produces, for a
research question:

- **5–20 competing hypotheses**, each grounded in a real graph element (a
  retracted node, a contradiction, a doubtful reagent, an undrugged target).
- a **Scientific Decision Board**: priority, expected information gain, evidence
  strength, contradiction score, novelty, risk, cost, duration, validation
  difficulty, reviewer confidence — each tagged computed / estimate / qualitative.
- an **experiment portfolio** (Quick Win / High Impact / High Risk / Cheap
  Validation / Mechanism / Clinical Translation / Negative Control).
- a **scientific debate** per hypothesis (Proponent / Skeptic / Reviewer),
  resolved by explicit evidence, never by voting.
- a **knowledge-gap engine** — "what evidence is preventing publication?"
- a single **recommendation**: which experiment first, why, how to falsify it,
  and why it beats the runner-up.

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

python -m keystone.decision_engine      # the decision engine (CLI)

pip install fastapi uvicorn             # the UI
python -m keystone.ui.server            # -> http://127.0.0.1:8000  Decision Engine
                                        #    /workspace  evidence view
                                        #    /workbench   reasoning loop

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
  decision_engine.py      THE PRODUCT — competing hypotheses ranked into a
                          next-experiment recommendation (what to do, and why)
  deterministic/
    hypothesis_space.py      generate 5-20 competing hypotheses from the graph
    decision_metrics.py      score + rank (computed/estimate/qualitative, no fabrication)
    experiment_portfolio.py  bucket experiments + explain ordering
    scientific_debate.py     Proponent/Skeptic/Reviewer, resolved by evidence
    gap_engine.py            categorized "what's preventing publication?"
  workspace.py            Disease Workspace (evidence view, at /workspace)
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
