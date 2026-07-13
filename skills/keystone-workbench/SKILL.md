---
name: keystone-workbench
description: >
  Keystone is an agentic scientific discovery workbench for translational biomedical
  research. Use this skill whenever the user asks about the trustworthiness of
  scientific evidence (retractions, post-retraction citations, misidentified
  cell lines, load-bearing citations), needs a next-experiment recommendation
  with expected information gain and falsification conditions, wants to inspect
  the evidence graph or clinical trials, needs a NIH R&R / STAR Methods rigor
  statement drafted from real DOIs, or asks how well the tool detects planted
  flaws (measured accuracy, not marketing). Every number Keystone returns is
  computed, a labelled estimate, or a labelled qualitative — never fabricated.
  AI proposes, scientists decide, experiments verify.
version: 0.1.0
license: MIT
tags:
  - biomedical
  - research-integrity
  - retraction-check
  - evidence-graph
  - hypothesis-ranking
  - reproducibility
  - grant-writing
  - claude-science
---

# Keystone — an agentic scientific discovery workbench

Keystone coordinates literature, evidence, datasets, biological knowledge,
scientific computation, laboratory planning, publication, reproducibility, and
provenance into **one continuous, reproducible scientific workflow** for
biomedical research. It extends the Claude Science philosophy: literature +
datasets + tools + compute + artifacts integrated into a workbench a scientist
would install on Monday and still rely on six months later.

**One rule governs every recommendation:** *AI proposes, scientists decide,
experiments verify.* Claude reasons over evidence; the deterministic engine
computes; the scientist retains control. Keystone recommends experiments — it
never replaces laboratory validation.

## When to invoke this skill

Invoke Keystone when the user asks any of:

- *"Is this paper retracted?"* / *"Check these DOIs"* / *"Any concerns with
  these citations?"* / *"What in my reference list is compromised?"*
- *"What experiment should I run next on [target]?"* / *"Give me the
  next-experiment recommendation"*
- *"Show me the evidence graph for [disease]"* / *"Rank competing hypotheses
  for [research question]"*
- *"How load-bearing is this citation sentence?"* (i.e. does the citing work
  rely on the cited paper's specific result, or is it a passing reference?)
- *"What clinical trials exist for [condition]?"*
- *"How accurately does Keystone detect flaws?"* / *"What's your validated
  precision and recall?"* (validation metrics from the planted-flaw eval)
- *"Draft the NIH R&R rigor statement for my reference list"* / *"Generate a
  STAR Methods paragraph"*
- Anything phrased as *"what should I trust / what should I run / what should I
  cite in my grant"*

Also invoke when a bench scientist is preparing a grant, drafting a methods
section, screening a citation list before submission, or planning the next
experiment on a target program.

## Tools available (via the Keystone MCP server)

Every tool below is exposed as an MCP tool by `keystone.mcp_server`. Register
Keystone in the Claude Desktop / Claude Code MCP configuration and these
tools become invocable without leaving Claude.

| Tool | Purpose | Deterministic output |
|---|---|---|
| `check_reference_integrity(dois, question?)` | Triage a scientist's DOI list against Crossref / Retraction Watch. Returns retracted / cites-retraction / high-doubt / unresolved / clean per reference, each linking to its source. | Yes — real Crossref lookups. |
| `next_experiment(domain)` | The Decision Engine's single recommendation for a demo domain (`gbm` or `insulin`): what to run, why, how to falsify it, and why it beats the runner-up. | Yes — computed / estimate / qualitative labels on every field. |
| `competing_hypotheses(domain)` | Ranked competing hypotheses with priority, expected information gain, cost, risk, and kind. | Yes — auditable ranking. |
| `classify_load_bearing(citing_sentence)` | Judges whether a citing sentence is load-bearing (relies on the cited paper's specific result) or incidental. Reaches 0.818 agreement with a hand-labelled reference set (single-annotator baseline). | Yes — interval + verdict. |
| `evidence_summary(domain)` | High-level summary of the evidence graph — node/edge counts, contradictions, knowledge gaps, cited sources, reproducibility hash. | Yes. |
| `search_clinical_trials(condition, limit?)` | Real ClinicalTrials.gov v2 search. Returns NCT id, status, phase, eligibility. | Yes — real API. |
| `evidence_graph(domain)` | Full evidence graph as JSON — nodes with `NodeType` and doubt intervals, edges with load-bearing weight and temporal relation. | Yes — lossless projection. |
| `validation_metrics(domain)` | Keystone's measured catch rate on planted known flaws + benign controls. Precision, recall, F1, and the load-bearing calibration number. | Yes — the "verify the tool before you trust it" beat. |
| `publication_report(domain)` | Publication-ready HTML with the independent Reviewer critique, real DOIs, provenance appendix, and reproducibility hash. | Yes. |
| `mine_literature_patterns(records, question?, seed_doi?, scan_type?)` | Scan a corpus of OpenAlex-shaped records; return contradiction clusters, method drift over time, flagged reagent contamination trends, and consensus-vs-outlier claims. Every hit cites real DOIs. Out-of-scope scans (causal inference, patient outcome, drug efficacy, clinical decision) refused with structured explanation. | Yes — deterministic detectors own numbers; Claude narrates. |
| `review_bench_data(csv_text, label?, fmt?)` | The Laboratory Agent: run deterministic QC on a 96-well plate-reader CSV (standard-curve R², replicate CV, edge effect, missing wells) and return a Reviewer verdict (supported / downgraded / rejected) that downgrades confidence when the data fails QC, with grounded workflow fixes. Unsupported instrument formats (western blot, microscopy, CryoEM, FCS, FASTQ) refused with a structured explanation. | Yes — thresholds cite-able (FDA Bioanalytical 2018); Claude narrates only. |
| `discovery_run(records, domain?, question?, seed_doi?, bench_csv?)` | The self-correcting loop: mine literature contradictions, turn each into a rankable competing hypothesis scored on the SAME decision board as the graph hypotheses, and — if a validation plate is supplied — downgrade the recommendation's confidence when the plate fails QC. Ties the Literature Miner, Decision Engine, and Laboratory Agent into one system. | Yes — every score deterministic; a literature-only hypothesis carries honest default uncertainty. |
| `post_publication_changes(doi)` | "Which papers changed after publication?" — every Crossref post-publication change for a DOI: retractions, corrections, errata, and expressions of concern (not just retractions), with dates. Real data or an explicit unresolved marker. | Yes — real Crossref, never fabricated. |
| `field_integrity(records, question?, seed_doi?)` | "How contaminated is this field's literature?" — a transparent, auditable Field Integrity Score (0-100) computed from real signals: retraction burden, post-publication-change burden, and integrity-pattern load. Every weight exposed; pairs with a printable hash-stamped Research Integrity Audit. Nothing fabricated. | Yes — deterministic composite of real signals. |
| `check_prior_art(query)` | "Did someone already discover this?" — search OpenAlex for the closest existing work to a hypothesis or question, so a scientist doesn't re-run a published experiment. Flags retracted matches. NEVER issues a novelty verdict — surfacing overlap is the tool's job; judging novelty is the scientist's. | Yes — real OpenAlex; surfaces overlap, no novelty claim. |
| `assess_frontier(frontier, genes?, study?, records?, question?)` | Frontier Guard — the responsible-AI layer for three frontiers. `phage_design` vets a candidate phage genome for biosafety (toxin / lysogeny / AMR screen + host-range → go/caution/no-go) and refuses to prescribe a phage. `organoid_response` scores an organoid study for reproducibility risk (low/medium/high). `aging_clock` scores a biological-age-acceleration study's rigor and benchmarks a claimed result against published clocks (Horvath / PhenoAge / GrimAge). Each adds a literature evidence scan + rigor checklist. NEVER generates a sequence, prescribes a phage, predicts a patient outcome, computes a patient's biological age, reads images, or touches PHI; unknown frontiers refused. | Yes — deterministic screen against cited marker/standard sets. |

## Invocation patterns (share these with the user when relevant)

**Reference-integrity check.** *User pastes DOIs or a BibTeX snippet.*
```
User: "Check these references for retractions:
        10.1038/sj.onc.1207616, 10.1038/414799a, 10.3389/fonc.2025.1577492"
Claude → check_reference_integrity(dois=[...], question="my reference set")
Claude → responds with the per-reference triage, DOIs linked, and calls out
         any post-retraction citations (the blast radius).
```

**Next-experiment recommendation.** *User asks what to run.*
```
User: "Given the glioblastoma cathepsin B invasion axis, what should I run
       next?"
Claude → next_experiment(domain="gbm")
Claude → summarizes the ranked #1 hypothesis, its kill-condition, the priority
         breakdown, and why it beats the runner-up.
```

**Rigor statement drafting.** *User is preparing an R01.*
```
User: "Draft the NIH R&R rigor statement for these DOIs."
Claude → check_reference_integrity(dois=[...])
       → interprets the triage
       → notes cell-line / antibody / SABV slots the scientist must fill in
         (Keystone does not fabricate these).
```

**Literature pattern mining across a corpus.** *User asks about the state of a field.*
```
User: "What contradictions exist in the cathepsin B glioblastoma literature?"
Claude → mine_literature_patterns(records=<50-100 OpenAlex-shaped papers>,
                                   question="cathepsin B in glioblastoma",
                                   scan_type="contradiction_scan")
Claude → summarizes each contradiction pair, cites the real DOIs from the
         report.hits[].dois list; never invents a pattern.
```

**Frontier vetting (Frontier Guard).** *User asks about a phage candidate or an organoid study.*
```
User: "Is this phage candidate safe for therapy? Genes: capsid, integrase, stx2, tail fiber."
Claude → assess_frontier("phage_design", genes=["capsid","integrase","stx2","tail fiber"])
Claude → reports NO-GO (toxin + lysogeny markers), the flagged categories with
         citations, and states plainly that this is a first-pass screen, not IBC
         clearance, and that Keystone never generates sequences.
```

**Bench-data QC review (the Laboratory Agent).** *User has plate-reader output.*
```
User: "Review this ELISA plate — is the standard curve good enough to quantify?"
Claude → review_bench_data(csv_text=<plate CSV>, label="ELISA run 3")
Claude → reports the verdict (supported/downgraded/rejected), the failed QC
         checks with their cite-able thresholds, and the workflow fixes;
         defers the decision to the scientist. Refuses western-blot /
         microscopy / CryoEM formats with a structured explanation.
```

**Trust check before recommending Keystone itself.**
```
User: "Do you actually catch retraction contamination reliably?"
Claude → validation_metrics(domain="gbm")
Claude → reports the measured catch rate honestly, including missed flaws.
```

## Discipline (rules the skill must not violate)

1. **Never fabricate numbers.** Every doubt value, sample size, or ranking is
   deterministic. Do not invent a percentage, sample size, or interval; if the
   engine did not return it, do not present it.
2. **Claude reasons; the engine computes.** Explain, contextualize, and connect
   the tool's output. Do not substitute prose for a number.
3. **Cite sources.** Every claim must trace back to a DOI, NCT id, UniProt
   accession, Cellosaurus id, or an explicit `unresolved` marker.
4. **AI proposes, scientists decide.** When the user asks *"should I do X?"*,
   answer with the recommendation *and* the falsification path, and defer the
   decision to the scientist.
5. **Never claim laboratory validation.** Keystone recommends experiments;
   experiments happen in the lab.

## Reference

- Full architecture: `ARCHITECTURE.md` in the Keystone repository.
- MCP server: `keystone.mcp_server` (registered as `command: python`,
  `args: ["-m", "keystone.mcp_server"]`).
- Workflow spine: **Scientist → Question → Evidence → Integrity → Decision →
  Experiment → Publication → Claude Desktop → Scientist.**
- Determinism boundary: `keystone/agents/reasoner.py` (heuristic) /
  `keystone/agents/claude_reasoner.py` (live semantic layer). Numbers stay in
  the engine; prose comes from Claude.

## Flagship demonstration

Keystone ships with a real glioblastoma dataset — the cathepsin B / MMP-9
proteolytic axis — anchored by a real 2004 *Oncogene* paper
(`10.1038/sj.onc.1207616`) that was retracted in 2025. Two sample reference
lists in the `examples/` directory demonstrate the tool end-to-end. The
platform is validated on two independent domains; the classifier reaches 0.818
agreement with a hand-labelled reference set (single-annotator baseline).
