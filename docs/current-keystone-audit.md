# Keystone — Current Working-System Audit (judge + scientist lens)

_2026-07-13. Every row below is backed by a command, a passing test, or a live browser check performed this session — not by reading claims in the code._

## Verdict up front
- **Genuinely good & judge-worthy:** the integrity-first thesis (catch retraction/misidentification *before* reasoning), the real claim-provenance model, the live exclude-and-recompute counterfactual, the reproducibility bundle, and the honest deterministic-numbers / Claude-prose split. **All 10 spec acceptance tests pass (191 tests).**
- **Weak / risky:** product sprawl (9 routes, mixed styles); the workflow is deep on **one** real domain (GBM); the evidence-graph "Contest" button is visual-only; Claude output is defensively parsed, not strict-schema-validated; one synthetic domain (LRRK2) still shipped (labeled).
- **Would a scientist use it?** For the GBM-style *audit a conclusion → get the next experiment → export a reproducible receipt* loop: yes, credibly. As a general everyday tool across arbitrary papers: not yet.
- **Top-3 realistic?** Yes. The engine is real, the wedge is validated by 2026 evidence, and the demo arc is complete. The gap is **focus + generalization**, not credibility.

## API key & Claude integration (Step 2) — PASS
| Check | Result | Evidence |
|---|---|---|
| Key server-side only (`os.environ`) | ✅ | `claude_reasoner.py:77,90` |
| Not in static bundles / API responses | ✅ | `grep` static + responses: 0 |
| Not in git history | ✅ | `git log -p` for key prefix: 0 |
| `.env` gitignored | ✅ | `git check-ignore .env` |
| Live request succeeds | ✅ | `/healthz live_claude:true`; live decision returns Claude prose |
| Error handling (timeout/invalid/rate-limit/malformed) | ✅ | `_complete_json`: retry+backoff, any exception → deterministic fallback, bad JSON → fallback, no hang |
| Structured output validated | 🟡 | JSON-parsed + defensive `.get()` with fallbacks — **not strict schema validation** |
| Claude statements labeled as model output | ✅ | "CLAUDE · DRAFT / awaiting sign-off" tags; numbers tagged deterministic |

## Feature audit
| Feature | Exists | Works | Real data | Scientist | Judge | Red flag | Decision |
|---|---|---|---|---|---|---|---|
| Live Claude reasoning + fallback | yes | ✅ verified | — | 4 | 5 | none | **KEEP** |
| API-key security | yes | ✅ verified | — | 5 | 4 | none | **KEEP** |
| Claim/provenance model (`claim_status.py`) | yes | ✅ 5 tests | real | 5 | 5 | none | **KEEP** |
| Integrity gate (retraction + cell-line) | yes | ✅ 5ms live | real | 5 | 5 | none | **KEEP** |
| Counterfactual (exclude→recompute, FI 100→93) | yes | ✅ tested+live | real | 5 | 5 | none | **KEEP** |
| Claim provenance drawer (front door) | yes | ✅ live | real | 5 | 4 | none | **KEEP** |
| Reproducibility bundle (.zip, 6 files) | yes | ✅ tested+live | real | 5 | 4 | none | **KEEP** |
| Agent team + adversary (confidence drop) | yes | ✅ live | real | 4 | 5 | none | **KEEP** |
| Decision engine (ranked next experiment) | yes | ✅ live | real | 4 | 4 | none | **KEEP** |
| Evidence graph rendering | yes | ✅ live | real | 4 | 4 | labels ok now | **KEEP** |
| Graph "Contest confidence" button | yes | ⚠ visual-only | n/a | 2 | 2 | **doesn't change the real decision** | **ENHANCE** (wire to counterfactual) or relabel |
| Internal node ids in UI | — | fixed | — | — | — | was leaking → fixed+sanitized+tested | **KEEP (closed)** |
| LRRK2 / Parkinson's domain | yes | renders | **synthetic** | 1 | 0 | fake if demoed | **HIDE from demo** (keep labeled) |
| Legacy surfaces `/classic /labs /os /neurohem /workbench` | yes | load | mixed | 2 | 1 | sprawl, inconsistent style | **REMOVE/HIDE** from demo path |
| 3D protein / 3D brain | yes | load | illustrative | 2 | 3 | nice, not core | **KEEP (P2)** |

## Red-flag register (open)
| # | Red flag | Severity | Proof | Fix | Test to close |
|---|---|---|---|---|---|
| R1 | Product sprawl — 9 routes, 3 styles | **major** | route grep | make `/` the one product; drop legacy from nav/demo | route smoke test |
| R2 | Graph "Contest" changes nothing real | major | `contest()` sets only `dispConf` | wire to `/api/counterfactual` | graph-changes-decision test (Step 9) |
| R3 | Generalization ceiling (full workflow = 1 domain) | major | only GBM fully real | promote "paste any DOI → live integrity verdict" as first-class | live arbitrary-DOI test |
| R4 | Claude output not strict-schema-validated | minor | `_complete_json` | add key/type check → fallback on mismatch | schema-validation test |
| R5 | Synthetic LRRK2 domain shipped | minor | `Illustrative·synthetic` | hide from demo path | — |

## Closed this session (with proof)
Cold-start stall (boot-warm, 0.008s) · internal-id leak (#7, 6 sites + API sanitizer, tested) · counterfactual (#9, tested+live) · claim drawer in front door (#4, +responsive) · reproducibility bundle (#8, tested+live) · deprecation warning (lifespan). **10/10 acceptance tests pass.**

## Top-3 positioning (Step 6)
Direction **A — Evidence-to-Experiment** wins (Keystone already is it): real dataset, built+tested trust model, strongest 90-second demo, unique integrity wedge validated by 2026 evidence (frontier models flag 0% of post-cutoff retractions; $28B/yr cell-line cost). B (single-cell) needs a data pipeline Keystone doesn't have; C (protocol replication) is narrower and less demoable. **Do not broaden — narrow and finish A.**

## The one thing left for a clean top-3 demo
Close **R1 (sprawl)** and **R2 (make the graph's contest trigger the real recompute)** — then the demo is: question → integrity gate fires → click a node's provenance → exclude it → conclusion recomputes on the graph → ranked next experiment → download reproducible bundle. Every step real, every claim sourced.
