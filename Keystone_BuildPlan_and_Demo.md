# Keystone — Build Plan & Demo

**AI Scientific Research Workbench.** Glioblastoma-deep for the demo; domain-agnostic by construction. Built to be trusted by a real research laboratory: every conclusion grounded, uncertain, independently challenged, human-gated, and reproducible.

---

## 1. What is built and running (verified end-to-end, offline)

The full workbench runs today (`run_workbench.py`, seven passing tests in `tests/test_smoke.py`):

- **The loop:** Plan → Collect → Analyze → Hypothesize → Design Experiment → Review → Human Approval → Ledger.
- **Semantic layer (Claude):** Scientific Planner, Literature, Evidence-Quality (the load-bearing moat), Experiment Design, Reviewer, and a Pathway-Figure vision agent — all wired to the real API; `HeuristicReasoner` runs the same pipeline offline.
- **Deterministic layer:** power analysis (refuses to fabricate n without a grounded effect size), doubt propagation, protocol validator, 12 connectors, provenance/Ledger hashing.
- **Five reasoning-transparency enhancements** (this document's focus), all deterministic projections of what the workbench already computed.
- **Native artifacts rendered as real files:** evidence graph, timeline, 3D protein structure, why-panel, future-experiments tree.

Verified behaviour: load-bearing citer inherits doubt 0.63, incidental citer 0.20, post-retraction citer flagged inexcusable; power analysis computes n=25/arm from a grounded Cohen's d=0.80; Reviewer independently downgrades the hypothesis 0.55→0.35.

---

## 2. The five enhancements (what they add, why they're trustworthy)

**1. "Why did Keystone reach this conclusion?" panel** (`reasoning_panel.why_panel`, rendered `why_panel.html`).
Every hypothesis shows its full reasoning chain, not a score: supporting evidence (with per-node doubt), contradicting evidence, confidence interval, the independent Reviewer's objection and adjusted confidence, remaining uncertainty, failure modes, and the suggested next experiment. Every field is a projection of an object that already exists — the panel invents nothing. This is the single highest-value addition: it turns a verdict into an auditable argument.

**3. Future Experiments decision tree** (`reasoning_panel.future_experiments_tree`, rendered `future_experiments.svg`).
After the validation experiment: if positive → confirmatory (independent panel + rescue) → translational (PDX, MGMT-stratified); if negative → the alternative hypothesis grounded in the *contradicting* evidence node. Branches reference real evidence nodes, so it's a research plan, not decoration. This is what makes Keystone read as a research partner.

**4. Session Replay** (`replay.py`, emitted `session.json`).
Every stage recorded as an ordered, timestamped step; deterministic step-through. A scientist, reviewer, or integrity office can walk exactly how a conclusion was reached. Aligned with the reproducibility/audit-history direction — and tested to be complete and correctly ordered.

**5. Research Readiness — the honest version** (`reasoning_panel.research_readiness`).
**No fabricated percentages.** Each dimension is computed, an interval, or an explicitly-labeled qualitative estimate with its basis:
- *Evidence support* = mean inverse-doubt of grounding nodes, **with a CI** (e.g. 0.40 [0.35, 0.45]).
- *Reproducibility* = checklist completion **ratio** (e.g. 5/9 items).
- *Risk* = derived from Reviewer verdict + confidence-interval width (low/medium/high).
- *Missing evidence* = a real **count** of open gap items.
- *Novelty* = a **qualitative** ordinal with the explicit caveat that a quantitative score needs an embedding-similarity search against the corpus — not computed this week.

This correction is deliberate and it is the point: "Novelty 92%" is fabricated authority a scientist rightly distrusts. A defensible readiness panel that refuses to invent numbers is *more* persuasive, and it's enforced by a test (`test_readiness_never_fabricates_percentages`).

---

## 3. Build This Week vs. Claude Science Roadmap

**This week:** everything above, running offline and live-wired; the five enhancements; all artifacts rendered; reproducible Ledger + Session; collaboration primitive (signable/comparable Ledgers).

**Roadmap:** quantitative novelty via corpus-embedding search; cross-disease ontology packs; live bioinformatics pipelines on HPC; corpus-scale contradiction mining; trial-outcome-vs-hypothesis reasoning; multi-role collaboration UI (PI → postdoc → reviewer → editor); microscopy/spatial-transcriptomics vision (only with validated models).

---

## 4. Demo storyboard (~5 minutes)

1. **Cold open (15s).** "A foundational glioblastoma paper was retracted. Papers were built on it. Which conclusions are unsafe — and what's the strongest experiment still worth running?"
2. **Ask (20s).** Pose the GBM question; the Planner decomposes it, connectors build the graph, the retracted foundation greys out.
3. **The moat (60s).** Two citers side by side: load-bearing (w=1.00, doubt 0.63) vs incidental (w=0.22, doubt 0.20), with per-edge rationale. Temporal reveal: the post-retraction citer flagged inexcusable.
4. **The discovery (30s).** The contradiction surfaces; one falsifiable hypothesis emitted with a named kill-experiment and a real power analysis (n=25/arm from grounded effect size).
5. **The Why-panel (45s).** Open it: supporting/contradicting evidence, confidence interval, remaining uncertainty, failure modes, next experiment. "Not a score — an argument you can audit."
6. **The gate (30s).** Reviewer attacks and downgrades 0.55→0.35. "It red-teams itself."
7. **Future experiments (30s).** The decision tree: positive path, negative path to the alternative hypothesis. "A research partner, not an analysis tool."
8. **Research readiness (30s).** The honest panel — and *call out* that novelty is qualitative because you refuse to fabricate a percentage. This candor is a selling point to a scientific audience.
9. **Replay + reproduce (30s).** Step through the session; re-run to an identical hash.
10. **Close (20s).** "Grounded, uncertain, challenged, human-gated, reproducible. This is a workbench a lab can trust." → roadmap slide.

The winning beats: **#5 (the argument, not the score), #6 (self-downgrade), and #8 (refusing to fake novelty).** Together they say *this system tells the truth about what it knows* — which no chatbot, dashboard, or RAG wrapper does.

---

## 5. Judge Q&A additions

**"Isn't a readiness score just marketing?"** Ours refuses to be. Evidence support carries a confidence interval, reproducibility is a real checklist ratio, and novelty is explicitly qualitative because a real novelty score needs a corpus-embedding search we haven't run. We'd rather show an honest gap than a fabricated 92%.

**"How is this a research partner and not a search tool?"** The future-experiments tree plans the *next* move conditioned on outcome, grounded in real evidence nodes — and the Reviewer challenges the plan. It reasons forward and adversarially, not just retrospectively.

**"How do I audit a conclusion I disagree with?"** Session Replay + the Why-panel: step through every stage, see every grounding node and its doubt, read the Reviewer's objection, and override with attribution in the Ledger. Re-run to an identical hash.

---

## 6. The one risk that still matters

Unchanged and honest: the moat is only proven when `ClaudeReasoner`, run live and calibrated against a hand-labeled GBM set, produces load-bearing judgments that beat a coin flip and a hypothesis a real GBM scientist calls non-obvious. The plumbing — including all five enhancements — is built, tested, and reproducible. The intelligence inside it is proven the day you run live mode against real labels on a real retracted GBM paper's citation graph. Spend the remaining time there.
