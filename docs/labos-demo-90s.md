# Keystone LabOS — the 90-second demo

**One question, start to finish, every claim traceable.** Front door opens on the
flagship **IMMUNOLOGY · CD4 T-CELL** program (the only program shown to judges;
GBM/ICH/insulin stay reachable at `/?programs=all`). Run `keystone-ui` (offline is
fine — every number is deterministic) and open `/`.

The scientist question:
> *In activated CD4+ T cells, which perturbation-defined intracellular regulator
> most closely reproduces the desired type-2 (Th2) program while staying selective,
> safe, and chemically tractable — and what experiment would settle it?*

## The walk (7 steps, ~90 seconds)

| # | Step | What the judge sees | Why it's real |
|---|------|---------------------|---------------|
| 1 | **Question** | The program, dataset, and the #1 candidate (STAT6, a clinically-validated degrader). | Real run id; real target/biomarker. |
| 2 | **Data readiness** | 4 sources labeled `3 REAL · 1 SYNTHETIC`; the synthetic classifier is tagged **NOT A RANKING INPUT**; the Gladstone Perturb-seq is flagged **PREPRINT**. | Each card carries a resolvable accession, version, QC, and biological limits. |
| 3 | **Research Cell** | Five agents run over the real corpus; each shows tool calls, source-backed claims, run id, timestamp, ledger ✓. The **Reviewer gate** admits peer-reviewed claims as *primary support*, real preprint data as *corroboration*, and **rejects** the synthetic cross-check and the unsupported FBXO32 association. | Deterministic execution; the gate is enforced in code and tested. |
| 4 | **Rank targets** | 8 sourced components per candidate, weights shown, composite = Σ(weight×component). STAT6 #1 (KT-621 degrader). Each card ends with **"Keystone ranks a research hypothesis. This is not a validated drug target."** | Every component has a resolvable source + evidence label. |
| 5 | **Challenge evidence** | Click **EXCLUDE THE PREPRINT** → FBXO32 drops **0.428 → 0.153**, three components flip to "Unknown / insufficient evidence," the ranking re-sorts. | A real server recompute (`/api/target_ranking?exclude=…`), not a visual. |
| 6 | **Design experiment** | The Decision Engine emits a falsifiable next experiment with a named kill-condition and a computed sample size (n per arm). | Deterministic power analysis; refuses to invent an effect size. |
| 7 | **Export receipt** | A 10-file reproducibility `.zip`: sources.csv, claims.json, graph.json, target-ranking.json, dataset-manifest.json, run-manifest.json (real git `code_version` + `evidence_hash`), environment.txt, protocol.md, assessments.json, README. | Every file projects real engine output; a reviewer can re-run it. |

The decisive moment is **step 5**: excluding a not-peer-reviewed source genuinely
changes the conclusion — the thing a naïve "ask-the-LLM" tool cannot do.

---

## Honest final report

**What is real and validated (peer-reviewed, resolvable):**
- The curated literature/registry evidence that drives the ranking (real DOIs,
  UniProt, ChEMBL, Open Targets disease associations).
- KT-621 (Kymera) — the real clinical STAT6 degrader precedent behind STAT6's
  tractability.
- The API-key boundary, schema-validated Claude output, and the whole 8-component
  ranking math — all under test (247 passing).

**What is real but provisional (preprint — labeled everywhere):**
- The Gladstone–UCSF CD4+ T-cell genome-scale Perturb-seq measurements (downstream-DE
  count, on-target knockdown, cross-donor reproducibility). Admitted by the Research
  Cell as **corroboration**, never primary support; FBXO32's low cross-donor r (~0.13)
  is a real, measured reason its nomination stays provisional.

**What is exploratory:**
- The from-scratch logistic-regression pipeline (QC, leakage-safe leave-one-
  perturbation-out CV, baseline vs model). Method is real; it is a cross-check.

**What remains synthetic:**
- The single-cell expression *matrix* the classifier runs on. It is generated from
  the real type-2 signature structure, labeled `SYNTHETIC · EXPLORATORY`, marked
  `affects_ranking: false`, and **proven** numerically unable to change the ranking
  (`test_synthetic_data_cannot_affect_flagship_ranking`). Swap `load_real_matrix()`
  for a real `.h5ad` to promote it.

**What cannot yet generalize:**
- The transparent 8-component ranking and Research Cell are wired for the CD4+ T-cell
  program. Any gene can be *assessed* live via Open Targets, but the full ranking is
  defined for the flagship program; other programs (GBM/ICH/insulin) are secondary
  evidence/integrity cases.

---

## Add-on: Visual Evidence Lab — Cell-State Atlas

A CELLxGENE-style visual proof layer (nav → **Cell-State Atlas**), reachable from the
flagship program. One point per cell in a PCA embedding; color by perturbation arm,
type-2 signature, QC, or donor; **click a cluster** → the right panel shows that arm's
**real measured** Gladstone metrics (downstream DE, on-target KD, cross-donor r), its
**computed** signature shift (illustrative), its **ranking link** (rank + composite →
open ranking), and a **"what this does not prove"** section.

Honesty, enforced and tested (`tests/test_visual_evidence_lab.py`, 9 tests):
- The per-cell **matrix is synthetic** — every panel is tagged `SYNTHETIC / illustrative`
  and the atlas **cannot** be ranking evidence (all arms `affects_ranking: false`; the
  Research Cell reviewer rejects the `atlas:embedding` claim from ranking support).
- The **embedding is really computed** (from-scratch PCA/SVD, seed + code hash + version).
- Each cluster selection is a **real logged server computation** (`/api/atlas/select`
  mints a distinct selection run id), not a visual-only update.
- **Mode 2 (Spatial/Microscopy) is honestly disabled** — "No visual dataset connected" —
  because no real microscopy dataset is pinned; no fake cells, no fake segmentation.
- **Not clinical:** the atlas carries an explicit non-clinical disclaimer and no
  diagnostic/patient language; it does not diagnose, segment scans, or measure tumors.
- The atlas run receipt is exported in the reproducibility bundle (`atlas-run.json`).

Demo add-on (visual proof): open **Cell-State Atlas** → select the FBXO32 arm → see its
**real** low cross-donor r alongside its illustrative shift and its **#4** ranking link →
"open ranking" → exclude the preprint → recompute → export. The visual evidence and the
ranking tell the *same* honest story.

**Why Keystone is useful to a scientist today:**
It turns "which target next?" into an auditable decision: every claim carries a
source and an integrity state, weak/preprint/retracted evidence can be excluded and
the conclusion *actually recomputes*, a controlled five-agent cell keeps unverified
claims out of the ranking, and the whole run exports as a reproducibility receipt a
reviewer can re-run. It recommends and drafts; it never replaces lab validation.
