# Keystone — AI Scientific Research Workbench (Architecture)

*A capability Anthropic could add to Claude Science tomorrow. Built to be trusted by a real research laboratory.*

The mission is not to discover cures. It is to build the most trustworthy AI scientific workbench that accelerates biomedical research while keeping scientists fully in control.

---

## Design rules (enforced in code, not aspiration)

1. Never replace scientists — every result is human-gated.
2. Every conclusion is reproducible — the evidence graph is content-hashed.
3. Every hypothesis carries supporting + contradicting evidence, confidence, uncertainty, a required validation experiment, expected outcome, and failure modes — enforced by `Hypothesis.validate()`.
4. Every AI conclusion is independently challenged — the Reviewer agent argues to disprove.
5. Every result produces an auditable artifact — the Ledger.
6. Every recommendation carries citations + provenance — every node has a source and timestamp.
7. Deterministic algorithms wherever possible — stats, propagation, protocol checks, connectors.
8. Claude only where semantic reasoning is required — five agents, nothing more.
9. Software a real lab would trust.

**What these rules removed from the original spec:** "OS AI" (undefined and trust-violating — cut); Statistical Review Agent (statistics is deterministic → a module, not an agent); Protocol Review Agent merged into a deterministic validator the Experiment Design agent calls. Fewer parts, more real work.

---

## The separation that makes it trustworthy

```
        SEMANTIC LAYER (Claude — rule 8)          DETERMINISTIC LAYER (rule 7)
        ────────────────────────────────          ────────────────────────────
        Scientific Planner                        Connectors (12 databases)
        Literature Agent                          Doubt propagation (graph math)
        Evidence-Quality Agent                    Statistics / power analysis
        Experiment Design Agent                   Protocol validator
        Reviewer Agent (independent)              Provenance / Ledger hashing
        [Pathway-Figure Vision Agent]             Timeline projection
```

The proposer is always semantic; the checker is always deterministic. The Experiment Design agent *proposes* a design; the protocol + stats modules *validate* it. This proposer/checker split is the core trust primitive.

---

## The loop

```
Scientific Planner (semantic: decompose the question)
   → Collect         (deterministic connectors → evidence graph)
   → Evidence-Quality (semantic: per-edge load-bearing) + propagate doubt (det.)
   → Literature      (contradictions as a graph operation → discovery opportunity)
   → Hypothesis      (semantic, rule-3 complete or rejected)
   → Experiment Design (semantic) + Stats/Protocol (deterministic validation)
   → Reviewer        (semantic: independent challenge, rule 4)
   → Human Approval  (the gate — rule 1)
   → Ledger          (deterministic, reproducible artifact — rule 5)
```

Verified end-to-end offline (`run_workbench.py`): load-bearing citer inherits doubt 0.63, incidental citer 0.20, post-retraction citer flagged inexcusable; power analysis computes n=25/arm from a *grounded* effect size (Cohen's d=0.80) and refuses when none exists; Reviewer independently downgrades the hypothesis 0.55→0.35; timeline and evidence-graph artifacts render.

---

## Agents (semantic — rule 8)

| Agent | Does what no deterministic program can |
|---|---|
| **Scientific Planner** | Parse an ambiguous research question into a bounded task plan |
| **Literature Agent** | Synthesize claims; judge directional conflict between studies |
| **Evidence-Quality Agent** | Classify each citation edge load-bearing vs incidental (the moat), calibrated to the 69–75% human-agreement band with leniency correction |
| **Experiment Design Agent** | Propose perturbation, controls, readout, and a falsifiable kill-condition |
| **Reviewer Agent** | Argue *against* the hypothesis; downgrade when it rests on doubt |

## Deterministic modules (rule 7)

Statistics (power analysis via Acklam normal-inverse — no scipy dependency, refuses to fabricate n without a grounded effect size), doubt propagation (saturating flow attenuated by load-bearing weight, with CI propagation), protocol validator (completeness + confounding checklist), provenance/Ledger (content hashing), timeline projection, and 12 connectors.

## Connectors (rule 6 provenance; determinism boundary)

PubMed, OpenAlex, GEO, SRA, ClinVar, UniProt, PDB, ChEMBL, Reactome, ClinicalTrials.gov, Retraction Watch, Cellosaurus. Each calls a database, caches, returns — never invents an identifier; a failed lookup marks a node `unresolved`.

## Computer Vision — one justified capability

**Pathway/mechanism-figure reading** (`PathwayFigureAgent`, wired to Claude vision): when a load-bearing claim's evidence lives in a figure rather than text, it judges whether the doubtful result is structurally central to the depicted pathway. A real extension of the load-bearing moat.

**Deliberately excluded:** microscopy interpretation, spatial-transcriptomics annotation, image-manipulation detection, radiology — they need validated domain models and ground truth the workbench does not have; being wrong in oncology is a harm, not a bug. Roadmap, with that reason stated.

## Native artifacts (rule 5)

Evidence graph (SVG — doubt-coloured nodes, load-bearing-weighted edges, contradictions, retraction rings), Research Timeline (SVG projection), 3D protein structure (3Dmol.js, rendered because a hypothesis points at the target). Pathway diagrams, genome tracks, and molecular structures follow the same "artifact tied to the reasoning that produced it" pattern.

## Local vs HPC

Same agent code both ways; only the scheduler changes. Single-question graphs run locally in seconds; full-corpus blast-radius runs as an embarrassingly parallel HPC batch, returning the same Ledger.

## Collaboration primitive (this week) vs. collaboration UI (roadmap)

Every Ledger is signable and comparable: one scientist runs it, another re-runs it to an identical hash, a third records an override with attribution (`human_decision`, `human_signoff`). That reproducibility-as-collaboration substrate ships now; the multi-role comment/approve UI (PI → postdoc → reviewer → editor) is roadmap — building it this week would be building Google Docs, not the moat.
