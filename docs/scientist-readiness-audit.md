# Keystone — Scientist-Readiness Audit

_2026-07-13. The scope-locked workflow is **Keystone Target Trust**: activated CD4+ T-cell
Perturb-seq → type-2 (Th2) regulator prioritization → integrity/evidence review →
tractability/degrader hypothesis → falsifiable validation plan → reproducibility export.
Every row is backed by a test, an endpoint, or a live browser check performed this session._

## Product definition (honest)
Keystone is a **scientist-controlled evidence-to-experiment workbench**. For the T-cell case it
produces **evidence-audited target hypotheses for scientist review** — it does NOT claim to have
discovered a drug target, run a trained ML model, or make any causal or clinical claim.

## Feature decisions (Keep / Enhance / Rebuild / Hide)
| Feature | Decision | Evidence |
|---|---|---|
| Target Trust program (`tcell`) — real data | **KEEP** | real DOIs/UniProt (Shifrut 2018, GATA3/STAT6/RARA/FBXO32); loads through engine; live Claude decision |
| 8-component target ranking | **KEEP** | `target_ranking.py`; `test_target_ranking` (6); every component sourced + labeled; weights shown |
| Counterfactual (exclude → recompute) | **KEEP** | `/api/target_ranking?exclude=`; UI: FBXO32 0.470→0.195; `test_target_ranking` |
| Graph "Contest" → real recompute | **REBUILT** | was visual-only; now calls `/api/counterfactual?node=`; shows real ranking/FI delta |
| Claim/provenance drawer | **KEEP** | `claim_status.py` (5 tests); rendered in front door; verified≠true |
| Integrity gate | **KEEP** | `run_integrity_center`; real tier-1 checks per domain |
| Reproducibility bundle | **KEEP** | **10 files** incl. `target-ranking.json`, `graph.json`, `dataset-manifest.json`, `environment.txt`; `test_repro_bundle` (4) |
| First screen (demo discipline) | **KEEP** | tcell Discovery shows Question → dataset status → **TOP CANDIDATE STAT6** → integrity gate → action "Review why this target ranks" |
| Claude schema validation | **ENHANCE→KEEP** | `_valid_schema` wired at every call; `test_schema_validation` (5) |
| Field-integrity badge | **ENHANCE** | derived from integrity gate for corpus-less domains (tcell HIGH·88) |
| LIVE ENGINE pages (`/labs /os /neurohem /workbench`) | **HIDE** | removed from demo nav (routes+tests kept) |
| Synthetic LRRK2 domain | **HIDE** | still selectable but flagged; never in the demo path |
| ICH / insulin domains | **KEEP (illustrative)** | real DOIs, illustrative case framing |
| Guided workflow rail (6 steps) | **KEEP (new)** | `renderWorkflowRail()`; verified stepping Discovery→Rank→Compute→Challenge→Design→Export |
| 3D Protein Viewer | **KEEP** | renders real GATA3–DNA from PDB 3DFV (verified visually, WebGL) |
| Reasoning Pipeline (12 agents) | **KEEP (fixed)** | all 12 agents render; **80s cold → cached + `KEYSTONE_WARM=1` startup warm** (0.003s warm) |

## Full-app live sweep (2026-07-13, pass 6)
Clicked through all 10 nav screens on `tcell`; every screen renders and functions. Only defect found:
Reasoning Pipeline first call was **80s** (uncached live orchestration) → fixed with `_PIPELINE_CACHE`
+ background startup warm gated on `KEYSTONE_WARM=1`. 3D viewer confirmed rendering real PDB
coordinates (not an illustration). 209 tests pass.

## Top-3 release gate
| # | Gate | Status |
|---|---|---|
| 1 | One real workflow works end-to-end | 🟢 tcell: question→ranking→exclude→recompute→experiment→export |
| 2 | Every major claim has provenance | 🟢 claim model + ranking components sourced |
| 3 | Every score/ranking explainable | 🟢 8 components, weights shown, no opaque score |
| 4 | Every graph action changes real state or removed | 🟢 Contest → `/api/counterfactual` real recompute |
| 5 | Retracted/weak evidence changes the result | 🟢 exclude preprint → FBXO32 collapses |
| 6 | Claude output schema-validated | 🟢 `_valid_schema` + tests |
| 7 | API key safe + improves a real task | 🟢 server-side only, 0 leaks; live Claude decision/reviewer |
| 8 | ML claims real-evaluated or labeled exploratory | 🟢 no trained-model claim; effects = published, `Literature-supported` |
| 9 | Scientist completes 5 tasks < 3 min | 🟡 flows exist; time end-to-end before final demo |
| 10 | Tests: secrets/provenance/retraction/recompute/export/errors | 🟢 **202 tests** |
| 11 | 90-second demo, no hidden steps | 🟢 see script below |

## Red flags — status
| Red flag | Status |
|---|---|
| `_spec_and_builder` duplicated in 6 files (integrity showed GBM under tcell) | 🟢 fixed |
| Graph contest was visual-only | 🟢 rebuilt to real recompute |
| Field-integrity badge blank for tcell | 🟢 derived from integrity gate |
| Internal ids in UI | 🟢 fixed + sanitizer + test (prior) |
| Cold-start 47s | 🟢 boot-warm (prior) |
| Product sprawl | 🟢 legacy nav hidden |
| 6 named immunology agents not renamed | 🟡 generic multi-agent trace runs for tcell; renaming pending |
| Docs (README/architecture) | 🟡 this file + research/current-keystone audits; README refresh pending |

## 90-second demo script (Target Trust)
1. Open Keystone → it loads on **IMMUNOLOGY · CD4 T-CELL**, FIELD INTEGRITY **HIGH · 88**, CLAUDE·LIVE.
2. **Discovery Run** — the question ("which Th2 regulator to pursue"), the real dataset (Shifrut CRISPR screen), integrity gate (real checks).
3. **Target Ranking** — ranked regulators. Point out **GATA3 ranks #3 despite the biggest effect** — undruggable + essential. STAT6 #1 (ligandable, safer).
4. Tap a candidate → **"Review why this target ranks"** — 8 sourced components, each labeled (`Literature-supported`, `Ligandability evidence`, …), weights shown.
5. Click **"Exclude the preprint (not peer-reviewed)"** → the ranking **recomputes live**: FBXO32 0.470 → 0.195, its components become `Unknown / insufficient evidence`.
6. (Or, in **Evidence Graph**, select the preprint node → **Contest** → server recomputes the ranking in the drawer.)
7. **Decision Engine** → the ranked next experiment with a kill-condition (falsifiable).
8. **Grant Export → Reproducibility bundle (.zip)** — `sources.csv · claims.json · target-ranking.json · graph.json · run-manifest.json · protocol.md` — a reviewer can re-run every number.

## Honest final report
**Works:** the whole Target Trust loop on real data, with transparent ranking, a real counterfactual
(both on the ranking screen and the graph), schema-validated live Claude, and a reproducibility export.
**Rebuilt:** the graph Contest button (real recompute); the field-integrity badge; the domain dispatch.
**Hidden:** legacy LIVE ENGINE surfaces and the synthetic LRRK2 domain from the demo nav.
**Unvalidated / limited:** no trained ML model (effects are published measurements, labeled as such);
perturbation effects are curated from the cited literature, not re-derived from raw counts in this build;
ICH/insulin are illustrative cases on real sources; the 6 agents run as a generic trace, not renamed to
the immunology roster. **"Designed for scientist review," not "scientist validated."**
**Why a scientist would use it:** it turns "which regulator do I pursue?" into an auditable, recomputable
decision — every component sourced, weak evidence excludable, the ranking honest about the effect-vs-
tractability-vs-safety trade-off, and the whole thing exportable and reproducible.
