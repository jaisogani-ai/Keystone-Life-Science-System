# Keystone discovery spine (reference)

One connected workflow. Every station reuses the same evidence graph and the
same reproducibility hash. Nothing loses context between stations.

```
Scientist → Question → Evidence → Integrity → Decision → Experiment →
Publication → Claude Desktop → Scientist
```

## Station 1 — Question

The scientist arrives with a real research question — e.g. *"Is the cathepsin B
/ MMP-9 invasion axis a safe target for glioblastoma, given the retracted
foundational paper?"* The question anchors every downstream station.

## Station 2 — Evidence

Real connectors (`keystone.connectors.registry`) assemble a provenance-tagged
evidence graph: OpenAlex works, Crossref (with Retraction Watch), Cellosaurus
cell-lines, Semantic Scholar citing contexts, UniProt proteins, Reactome
pathways, ClinVar variants, ClinicalTrials.gov trials, ChEMBL targets. A miss
is marked `unresolved`; nothing is fabricated.

## Station 3 — Integrity (the entry workflow)

The `keystone.integrity_report` module triages every reference against real
signals — retracted / cites-retraction / high-inherited-doubt / unresolved /
clean — and propagates doubt from doubtful nodes to their downstream dependents
(the *blast radius*). Also runs the `integrity_center` checks: cell-line
authentication (Cellosaurus + ICLAC), publication validation (Retraction
Watch), protocol validity, and evidence quality (the calibrated 0.818
load-bearing classifier).

**Use the MCP tool `check_reference_integrity(dois)` here.**

## Station 4 — Decision

The multi-agent Decision Engine (`keystone.decision_engine`) generates 5–20
**competing hypotheses** and ranks them on a Scientific Decision Board:
priority, expected information gain, evidence strength, contradiction score,
novelty, risk, cost, duration, validation difficulty, reviewer confidence.
Every value is tagged **computed**, **estimate**, or **qualitative** — never
fabricated. The independent Reviewer challenges the top hypothesis; the
Principal Investigator synthesizes one recommendation with its kill-condition.

**Use the MCP tools `competing_hypotheses(domain)` and
`next_experiment(domain)` here.**

## Station 5 — Experiment

The recommended hypothesis carries a full validation experiment: perturbation,
system, positive controls, negative controls, readout, kill-condition, sample
size (power-analysis-computed, refuses to fabricate `n` from an ungrounded
effect size), and a reproducibility checklist. This is the experimental design
the scientist takes to the bench.

## Station 6 — Publication

`keystone.artifacts.report` composes the imported evidence + the decision +
the Reviewer critique + the provenance appendix into publication-ready HTML.
Two artifacts:

- **Research report** — full paper-adjacent HTML with figures.
- **NIH R&R + STAR Methods rigor statement** — the mandatory grant-submission
  artifact, projected from the imported reference set with the reproducibility
  hash embedded.

**Use the MCP tool `publication_report(domain)` here.**

## Station 7 — Claude Desktop

Same tools, exposed via `keystone.mcp_server` as MCP tools. A scientist in
Claude Desktop asks *"check my references"* / *"what should I run next?"* /
*"draft the rigor statement"* — Keystone answers with real evidence, no app
open.

## Loop back — Scientist

Every recommendation is a proposal; the scientist accepts, rejects, or
overrides. The decision is written to the Ledger with attribution
(`keystone.core.Ledger`) and reproduces to the same content hash. Scientific
memory persists across sessions.

## The one rule that governs every station

**AI proposes. Scientists decide. Experiments verify.**
