# Keystone LabOS — Reality Audit

**Date:** 2026-07-13  ·  **Method:** hands-on. Ran the server (`keystone-ui`, offline
config), exercised every API with `curl`, walked the flagship workflow in a real
browser (front door → rank → exclude preprint → recompute → export), inspected the
exported reproducibility bundle byte-for-byte, and ran the full test suite
(**237 passed**). Nothing below is asserted from the README alone — each row was
observed.

> **Headline finding:** Keystone is **not** a fake demo. The core scientist
> workflow (question → transparent ranking → real Perturb-seq evidence →
> integrity/counterfactual → real recompute → falsifiable experiment →
> reproducibility export) **actually works end to end** against real, resolvable
> data, with the API key held server-side and every number computed, not typed.
> The gaps are (a) one crash on a secondary surface, (b) a brittle counterfactual
> token, (c) a mislabeled reproducibility field, and (d) one honestly-labeled
> *synthetic* ML matrix. (a)–(c) are **fixed this session**; (d) is disclosed, not
> hidden. Details below.

---

## The reality table

Scientist-value is 0–5 (decision-changing = high, decorative = low). Actions:
**KEEP** (proven, useful) · **ENHANCE** (useful, incomplete) · **REBUILD** (good
concept, weak/fake) · **HIDE** (legacy/secondary, dilutes the one workflow) ·
**REMOVE** (misleading/irreparable).

| System feature | Exists | Actually works | Real inputs | Real output | Value | Red flag | Action |
|---|---|---|---|---|---|---|---|
| Front door (single instrument, 6-step stepper) | yes | proven — opens on CD4+ T-cell program by default, dark/serious UI, no fake KPI cards | real (engine projections) | decision-changing | 5 | none | **KEEP** |
| Transparent 8-component target ranking (`target_ranking.py`) | yes | proven — STAT6 #1 (KT-621 precedent), weights shown, every component sourced + labeled, composite = weighted sum (auditable) | real DOIs / UniProt / ChEMBL / Open Targets | decision-changing | 5 | none | **KEEP** |
| Counterfactual recompute (exclude the preprint) | yes | proven — excluding the preprint URL drops FBXO32 0.428→0.153, 3 components → "Unknown / insufficient evidence", ranking re-sorts; server call, not a visual | real | decision-changing | 5 | `exclude=PREPRINT` token silently no-op'd (only the exact URL worked) | **ENHANCE → fixed** (token now recomputes identically to the URL) |
| Real Gladstone CD4+ Perturb-seq metrics (`gladstone_data.py`) | yes | proven — measured downstream-DE count, on-target KD, cross-donor r per regulator, DOI-sourced, marked preprint | real (pinned fixture from the actual study) | decision-changing (FBXO32 r≈0.13 is the measured reason it stays provisional) | 5 | none — clearly separated from the synthetic classifier | **KEEP** |
| Perturb-seq ML classifier (`ml/th2_signature.py`) | yes | works as a **method cross-check only** — QC → leave-one-perturbation-out CV → baseline vs logistic reg → metrics | **synthetic** matrix built from the real Th2 signature (honestly labeled `SYNTHETIC · EXPLORATORY`) | not a ranking input by design | 2 | matrix is synthetic; would mislead if unlabeled | **KEEP (labeled)** — swap `load_real_matrix()` for a real `.h5ad` to promote |
| Evidence graph (11 nodes / 14 edges, breathing-by-confidence) | yes | proven — real nodes/edges, contradiction edge, retracted/preprint nodes resolve but are excluded; select→contest recomputes server-side | real | decision-changing | 4 | node "contest" and ranking "exclude" are two separate paths (minor UX seam) | **KEEP** |
| Research Cell (8 auditable agents + gates) | yes | proven — roster of 8 (Coordinator, Perturb-seq, Literature, Tractability, Network, Integrity, Reviewer, Experiment Planner); Swarm-vs-Cell control is a computed no-gate policy over the same corpus (labeled — not 300 live models) | real corpus | decision-changing | 4 | "swarm cost" is a labeled estimate (disclosed) | **KEEP** |
| Reproducibility bundle (`repro_bundle.py`, 10-file zip) | yes | proven — sources.csv, claims.json, assessments.json, graph.json, dataset-manifest.json, environment.txt (pkg versions), run-manifest.json, protocol.md (falsifiable experiment + kill-condition + computed n), target-ranking.json, README | real | decision-changing | 5 | `code_hash` duplicated the evidence hash (a reviewer couldn't check out the code) | **ENHANCE → fixed** (real git `code_version` + renamed `evidence_hash`) |
| API-key safety (server-side `.env`, `claude_reasoner.py`) | yes | proven — dependency-free `.env` loader, key never in static assets/responses/errors; schema-validated Claude output; deterministic fallback; offline guard | real | (infrastructure) | 5 | none — covered by `test_safety_invariants.py` | **KEEP** |
| Decision Engine (`/api/decision`, competing hypotheses → next experiment) | yes | proven — ranks competing hypotheses, emits a falsifiable next experiment with computed sample size | real | decision-changing | 5 | none | **KEEP** |
| Biology chain (`biology_chain.py`, Cell→…→Trial linkage) | yes | **was 500 on tcell** (KeyError `cellosaurus`) — now works for all 4 domains | real connectors | supporting | 3 | crashed on the flagship domain, leaked a stack trace | **ENHANCE → fixed** (primary cells → honest "no Cellosaurus accession", + endpoint guard) |
| Integrity center / Field Integrity | yes | works — real provenance-depth + post-pub stability factors | real | supporting | 4 | none | **KEEP** |
| Secondary programs (GBM · ICH · Insulin) | yes | work (all endpoints 200 across every domain) | real | supporting | 3 | breadth can dilute the one flagship workflow (Phase 2 focus rule) | **KEEP as secondary** — keep tcell the default and primary demo path |
| Live debate / CV lab / pattern-miner / frontier-guard / prior-art | yes | work (200) | real | supporting/experimental | 2–3 | extra surfaces beyond the core workflow | **KEEP but de-emphasize** — do not let them lead the demo |

---

## Red flags found and resolved this session

1. **Biology chain crashed on the flagship domain (500).**
   `build_biology_chain("tcell")` did `spec.REAGENT["cellosaurus"]`, but the CD4+
   T-cell program uses *primary human cells* — which correctly have no Cellosaurus
   cell-line accession. It raised `KeyError` and leaked a stack trace.
   **Fix:** handle the missing accession honestly (show the primary-cell reagent
   and state "no Cellosaurus cell-line accession"), plus a top-level endpoint guard
   that returns an "unavailable + repair" JSON instead of a 500. All four domains
   now build. Regression test added.

2. **Counterfactual was brittle to the obvious token.**
   Excluding `PREPRINT` (the token surfaced in the source field) silently did
   nothing — only the exact bioRxiv URL recomputed. The shipped UI passes the URL,
   so the demo worked, but the API violated least-surprise.
   **Fix:** a component is now excluded by *either* its raw source token or its
   resolved URL. `exclude=PREPRINT` and `exclude=<url>` recompute identically.
   Regression test added.

3. **Reproducibility field mislabeled.**
   `run-manifest.json` set `code_hash` = the evidence-graph hash, so a reviewer
   could not use it to check out the code that produced the run.
   **Fix:** added a real `code_version` (`git:<sha>[+dirty]`, honest `unavailable`
   fallback) and renamed the content hash to `evidence_hash`. Test updated.

**Result:** 235 → **237 tests pass**; zero non-200 responses across every endpoint ×
every domain.

---

## Honest limits (disclosed, not hidden)

- Keystone ranks **hypotheses**; it does not discover a target.
- The headline functional-effect component is **Literature-supported / Measured in
  dataset** (real DOIs + real Gladstone metrics), **not a trained model**.
- The single-cell **classifier matrix is synthetic/exploratory** and labeled as
  such; it is a method cross-check, never a ranking input.
- The Gladstone Perturb-seq source is a **preprint (not peer-reviewed)** and is
  labeled everywhere it appears.
- "Swarm" cost in the Research Cell control is a **labeled estimate**; the swarm is
  a deterministic no-gate *policy* over the same corpus, not 300 live models.

---

## Release-gate status (Phase 10)

| # | Gate | Status |
|---|---|---|
| 1 | Real end-to-end scientist task works | ✅ verified in browser |
| 2 | Every major claim has provenance | ✅ per-component source + label |
| 3 | Every agent performs a real logged task | ✅ roster + gates + trace |
| 4 | Every ranking is explainable | ✅ 8 components, weights shown |
| 5 | Every graph interaction changes real state | ✅ contest/exclude → server recompute |
| 6 | Retractions/weak evidence change the conclusion | ✅ FBXO32 0.428→0.153 |
| 7 | Claude output schema-validated | ✅ `_valid_schema` + deterministic fallback |
| 8 | API key safe and useful | ✅ server-side, tested |
| 9 | ML claims evaluated or labeled exploratory | ✅ labeled synthetic |
| 10 | Tests prove secrets/provenance/recompute/export/errors | ✅ 237 pass |
| 11 | Scientist completes core workflow < 3 min | ✅ 7-step stepper, cached |
| 12 | Demo works in 90 s with no hidden manual repair | ✅ warm-cache on boot |

---

## Phase 2 additions (2026-07-13) — LabOS focus

Built on top of the verified Phase-1 engine; nothing from Phase 1 was rebuilt.

- **Data Readiness gate** (`deterministic/data_readiness.py`, `/api/data_readiness`,
  UI screen): every source classified `real_public | gladstone | synthetic_fixture |
  unavailable` with accession, version, QC, biological limits, and an
  `affects_ranking` flag. Synthetic classifier marked `affects_ranking: false` — and
  `test_synthetic_data_cannot_affect_flagship_ranking` proves the composite is
  numerically independent of it.
- **Research Cell — five real agents** (`deterministic/research_cell_run.py`,
  `/api/research_cell/run`, UI screen): Data Analysis · Literature · Target Biology ·
  Integrity · Reviewer, each emitting inputs, tool calls, source-backed claims, run
  id, timestamp, reviewer status, and a ledger entry. Hard gate: a claim is primary
  ranking support only if the Reviewer approves it (peer-reviewed → approved; preprint
  measured → corroboration; no-source / unsupported / synthetic → rejected). Proven
  by `test_agent_output_cannot_affect_ranking_without_reviewer_approval`.
- **Focus** (Priority 2): the front door shows only the flagship CD4+ T-cell program;
  GBM/ICH/insulin stay fully working via `/?programs=all`. Nothing deleted.
- **Hypothesis disclaimer** (Priority 4): every candidate card and the ranking JSON
  now carry *"Keystone ranks a research hypothesis. This is not a validated drug
  target."*
- **8 required Phase-2 tests** added (`tests/test_phase2_labos.py`). Total: 237 → **247
  passing**; zero non-200 across every endpoint × domain; zero browser console errors.
- **Demo + honest final report:** `docs/labos-demo-90s.md`.

## Visual Evidence Lab (2026-07-13) — Cell-State Atlas

Grounded in real tools (CELLxGENE Explorer's precomputed-embedding + linked-metadata
model; 3D Slicer's layer model). Built **only** what real data supports.

- **Cell-State Atlas** (`ml/cell_atlas.py`, `/api/atlas` + `/api/atlas/select`, UI
  screen): PCA embedding (one point/cell), color by arm / signature / QC / donor,
  cluster selection → provenance panel (measured Gladstone / computed / ranking link /
  does-not-prove). The matrix is **synthetic** (labeled everywhere) and `affects_ranking:
  false`; each selection is a real logged server computation (distinct run id).
- **Mode 2 (Spatial/Microscopy):** honestly **disabled** — no real dataset pinned, so no
  fake cells/scans/segmentation. Mode 3 (3D): not built (correctly — no fake brain).
- **Multi-agent integration:** the Research Cell's Data Analysis Agent calls
  `compute_atlas()`; the Reviewer rejects the `atlas:embedding` claim from ranking
  support (illustrative visuals can't become evidence).
- **Non-clinical:** explicit disclaimer + no diagnostic/patient language (tested). Not a
  radiology product.
- **Export:** `atlas-run.json` added to the reproducibility bundle (now 11 files).
- **9 tests** (`tests/test_visual_evidence_lab.py`) covering all 8 required guarantees.
  Total: 247 → **256 passing**; atlas endpoints 200 across every domain; no console errors.
