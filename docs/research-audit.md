# Keystone — Research & Audit

_Built with Claude: Life Sciences (Anthropic × Gladstone Institutes). Last updated 2026-07-12._

This document is the honest audit the spec demands: **do not trust existing claims until verified.** Every line below was checked against the running app, the test suite, or a primary source.

---

## 1. What is actually true (verified, not claimed)

| Claim | Verdict | Evidence |
|---|---|---|
| "Live Claude" | ✅ **True** | `GET /healthz` → `{"live_claude": true}`; live decision returns Claude prose in ~35–47 s (now cached → 0.004 s after warm) |
| "Real data" (GBM) | ✅ **True** | Foundation is a **real retracted 2008 paper**; U-87MG flagged misidentified against **Cellosaurus CVCL_0022**; pinned DOIs/PMIDs resolve |
| "Real data" (LRRK2 / Parkinson's) | ⚠️ **Synthetic** | Labeled `Illustrative · synthetic` in the code. **Never demo this domain.** |
| Test suite green | ✅ **True** | `pytest` → **185 passed** (was 183; +2 added this audit) |
| Scientific-honesty claim model | ✅ **Exists, wired, tested** | `deterministic/claim_status.py`; served at `server.py:122,135`; `test_claim_model.py` 5/5 |
| No trained ML model | ✅ **True (by design)** | No torch/sklearn/weights. Architecture = **Claude (reasoning) + deterministic scoring**. This is a *strength*, not a gap (see §3). |
| No secret leaks to browser (#1) | ✅ **Pass** | No `sk-ant-` value in static bundles or API responses; `/healthz` exposes only booleans |
| Internal node ids hidden from UI (#7) | ✅ **Fixed this audit** | Was leaking `N_foundation` etc. in 6 sites; fixed + `test_no_internal_ids.py` |

---

## 2. The problem is real, big, and urgent (primary + secondary sources)

The strongest possible validation for Keystone's thesis — a verification/integrity layer over AI-assisted science — came from the research:

- **The best models cite retracted papers and _cannot know it._** A 2026 audit ran 12 frontier/production models (incl. Claude Opus 4.8, GPT-5.5) through citation questions; on **post-cutoff retractions they flagged 0%**. *"No amount of scaling lets a model know about a retraction that happened after it was trained. That is structural. It closes with a lookup… the verification layer most demos miss, because a demo asks about what the model already knows."* — [sourcecheck study](https://dev.to/mikeeus/the-best-ai-models-cite-retracted-papers-and-they-cannot-know-it-5acj)
- **Fabricated citations are exploding:** 1 in 2,828 papers (2023) → **1 in 277** (early 2026), a 6× rise (Lancet / Topaz, Columbia). — [STAT](https://www.statnews.com/2026/05/07/lancet-study-finds-steep-rise-fraudulent-citations-academic-papers/), [The Scientist](https://www.the-scientist.com/one-in-277-biomedical-papers-carry-fake-references-74480)
- **Cell-line misidentification:** ~1 in 5 lines compromised; ICLAC lists ~600; **~$28 B/yr** US irreproducibility cost. — [PLOS One](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0186281)
- **Determinism is a hard requirement** for regulated (GxP) work; probabilistic LLM output is "disqualifying." Keystone's seed + deterministic numbers answer this. — [BioSkepsis](https://bioskepsis.ai/blog/llms-reproducibility-crisis-life-science)
- **Dual-agent reviewer + mediator** validation reaches κ=0.96 — validates Keystone's Reviewer + Adversary. — [Zenodo 20616544](https://doi.org/10.5281/zenodo.20616544)

**Competitor gap:** Elicit, Consensus, Scite, Scopus AI are all RAG-over-abstracts Q&A. Scite contextualizes citations (supporting/contrasting) but **none gate on retraction/misidentification/provenance as the core decision step.** Mosaic (a hackathon peer) is a queryable knowledge graph — a librarian. **Keystone's open lane: the integrity/decision layer, not another search box.**

### What Anthropic itself is building toward
Claude Science = "literature, data, code, compute in one environment," where **"every output carries an auditable history of how it was made."** Keystone's provenance ledger is exactly this. — [Claude Science](https://www.anthropic.com/news/claude-science-ai-workbench)

_Reddit/X/forums used only as user-sentiment signal (r/MachineLearning on NeurIPS hallucinated citations, etc.), never as scientific evidence._

---

## 3. Three directions compared → decision

| Criterion | A. Evidence→Experiment reproducibility | B. Single-cell / Perturb-seq studio | C. Protocol→Replication integrity |
|---|---|---|---|
| Real dataset available now | ✅ GBM (real retraction + cell line) | ⚠️ needs Gladstone scRNA / CELLxGENE ingest | ✅ reuses GBM |
| Scientist usefulness | High (fund/run decision) | High (but narrower audience) | Medium |
| Claude Science fit | ✅ literature+reasoning+provenance | ✅ code+compute heavy | ✅ integrity |
| Demo clarity | ✅ one conclusion, one arc | ⚠️ needs domain priming | ⚠️ abstract |
| Scientific honesty | ✅ already modeled | ✅ | ✅ |
| Feasibility (1 week) | ✅ mostly built | ❌ new data pipeline | 🟡 |
| Judge memorability | ✅ "your foundation is retracted" | 🟡 | 🟡 |

**Decision: Direction A — Keystone Evidence-to-Experiment.** It has the real dataset, the built claim model, the strongest demo moment, and the clearest fit. B is a strong future extension **if** an official Gladstone dataset (T-cell seq / DNA regulatory / PPI) becomes accessible; note it, don't block on it.

**One-sentence value:** _Keystone helps a researcher trace one conclusion to its sources, challenge its evidence, inspect reproducible computation, and choose the smallest next falsifiable experiment._

---

## 4. Acceptance-test status (spec §TESTING)

| # | Requirement | Status |
|---|---|---|
| 1 | No secret in bundles/responses/logs | ✅ verified |
| 2 | Retracted excluded from positive support | ✅ `test_claim_model` |
| 3 | Unresolved cannot ground a supported conclusion | ✅ `test_claim_model` |
| 4 | A claim supports one conclusion, contradicts another | ✅ `test_claim_model` |
| 5 | Evidence needs source id + exact link | ✅ `test_claim_model` |
| 6 | Source-record verification ≠ evidence status | ✅ `test_claim_model` |
| 7 | Internal node ids never rendered | ✅ **fixed + `test_no_internal_ids`** |
| 8 | Repro export has data+code+model+run | 🟡 partial — bundle exists; verify fields |
| 9 | Browser E2E: exclude retracted → assessment changes | ⬜ **to build** (interactive counterfactual) |
| 10 | All prior tests green | ✅ 185 passed |

---

## 5. Build order (remaining, highest-leverage first)

1. **Surface the claim/provenance drawer in the new front door** (`ks-design.js` currently has 0 refs; the drawer only exists in the classic `components.js`). The scientific honesty must be visible in the main flow.
2. **#9 — interactive "exclude this source → the conclusion's assessment changes"** counterfactual endpoint + browser test. This is the killer demo and the last non-negotiable.
3. **#8 — verify/complete the reproducibility bundle** (README, sources.csv, claims.json, assessments.json, run-manifest.json, protocol.md).
4. **One guided demo flow** stitching Integrity Gate → Agent Team → ranked next experiment → export into a single 90-second arc.

**Do NOT rebuild from scratch.** The engine, claim model, integrity checks, and multi-agent trace are real and tested. The work is _surfacing, the counterfactual loop, and cohesion_ — not reconstruction.
