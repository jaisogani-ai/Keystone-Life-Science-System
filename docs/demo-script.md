# Keystone — 90-second demo script (audit one conclusion)

*The success test: a scientist opens ONE glioblastoma conclusion, sees what it is
built on, challenges it, and decides the next experiment.*

| Time | Beat |
|---|---|
| 0:00–0:12 | **Hook.** "In glioblastoma, is the cathepsin B / MMP-9 axis a safe target — given the foundational paper was retracted?" Press **Run loop**. |
| 0:12–0:30 | **Honest run-log streams** — `Retrieved · metadata matched → Claims extracted · integrity reviewed → Working inference drafted (AI · flagged for review) → Adversarial review → Recorded to ledger`. Never "verified" right after retrieval. |
| 0:30–0:48 | **Evidence graph, real names** (no `N_foundation`). Click the retracted node → the **provenance drawer**: `Source record verified = yes` **·** `Integrity = retracted` **·** and for this conclusion `evidence_status = excluded`. Say it out loud: *"the DOI resolves, but it can't support the conclusion."* |
| 0:48–1:05 | **"Why did Keystone reach this?"** — supporting vs contradicting claims by real title; the **Reviewer downgrades confidence in Claude's own words** (live with the API key). |
| 1:05–1:20 | **Exclude the retracted source** → the conclusion's support set changes; the same claim reads differently per conclusion (relation, not a global label). |
| 1:20–1:30 | **Experiment planner — decision tree**, "draft protocol requiring scientist approval." Close on the content-hashed ledger. |

Verified live: every claim carries source-record-verified / claim-type /
integrity-state + a conclusion-specific assessment; retracted never adds positive
support; the API key never appears in any response, error, or the static bundle.

---

# Keystone — 3-minute demo script

*The single shootable sequence. Every second is intentional. Total: 3:00.*

**Environment (before shooting):**

```bash
# 1. Fresh container
docker build -t keystone . && docker run -p 8000:8000 keystone
# → http://127.0.0.1:8000 must load with:
#     - brand:  "Keystone — an agentic scientific discovery workbench"
#     - subtitle: "Check what you build on; draft the rigor and methods
#                  artifacts you must submit."
#     - "Keystone recommends experiments and drafts artifacts; it never
#       replaces laboratory validation or scientific judgment." visible

# 2. When ready to record the live-Claude beats, restart with the key.
#    Setting ANTHROPIC_API_KEY is enough — Claude activates automatically
#    (make sure KEYSTONE_OFFLINE is NOT set). The badge flips
#    "· deterministic" -> "· Claude" and the Reviewer/PI/summary prose
#    become Claude's own words. Numbers stay deterministic (rule 7).
export ANTHROPIC_API_KEY=sk-...
docker run -e ANTHROPIC_API_KEY -p 8000:8000 keystone
# → verify at /healthz: {"live_claude": true}
```

Have Claude Desktop open in a second window with the Keystone MCP server
registered (see README §"Use Keystone from Claude Desktop").

---

## Shot table — THREE surfaces only

Panel note: 19 capabilities in 3 minutes reads as a tab tour. Show exactly
three surfaces — the **integrity catch (with the full post-publication
timeline)**, the **self-correcting Discovery Run loop (with prior art)**, and
the **Frontier Guard refusals** — then the MCP closer. Every other capability
stays in the app but OFF the demo. State every number exactly. Lead with the
real retraction; never lead with the 2/4 recall panel.

**Every DOI shown in the demo is real.** The Literature Pattern Miner runs on
the REAL corpus ("citers of the retraction" — 41 real OpenAlex papers, real
abstracts, 0 illustrative). Post-publication changes and prior art run on real
Crossref/OpenAlex records. If a judge clicks any DOI, it resolves.

**Surfaces to SHOW:** front-door integrity triage + blast radius + post-pub
timeline · Discovery Run + prior art (`/labs`) · Frontier Guard (`/labs`) ·
Claude Desktop MCP.
**Surfaces to HIDE:** biology chain, 3D protein, genome track, notebook,
live debate, validation panel, standalone pattern-miner tab.

| Time | Screen | What the narrator says | What lands |
|---|---|---|---|
| **0:00 – 0:15** | Cold-open over the retracted DOI `10.1038/sj.onc.1207616`: *"In 2025, a 2004 Oncogene paper was retracted. Papers still cite it every month. Watch what that costs a scientist."* | (silent overlay) | Verifiability — the real catch |
| **0:15 – 0:45** | Front door → "Check integrity" → triage renders **"4 of 5 compromised"**. Click a DOI → real Crossref page opens. Point at a reference's **post-publication timeline** (e.g. *expression of concern 2011 → retraction 2012* on the real arsenic-life record). | "Every flag is a real Crossref record. And Keystone shows the *full* change history — this one was flagged with an expression of concern a year before it was retracted. Not just retractions — every post-publication change." | Real data + coverage beyond retractions |
| **0:45 – 1:10** | Click the retracted node → **blast-radius** animation; inspector: *"↯ downstream claims inherit doubt."* | "A retracted paper contaminates the literature for years — doubt propagates along load-bearing citations. This is the blast radius." | Novel visual beat |
| **1:10 – 2:05** | `/labs` → **Discovery Run** → "Run the loop." A literature contradiction (real DOIs) **enters the decision board as a ranked hypothesis**; the bad plate fails QC; confidence **downgrades 0.55 → 0.15**. Then on the recommendation card, **"Has this been done?"** surfaces the real OpenAlex prior art — **top hit is RETRACTED**. | "The whole loop: a contradiction becomes a ranked experiment, the plate meant to test it fails QC, and Keystone downgrades its own confidence. Then — has this been done? The closest published work is retracted. Don't build on it." | The differentiator — one self-correcting system, real prior art |
| **2:05 – 2:40** | **Frontier Guard** → phage candidate with a toxin + lysogeny gene → **NO-GO**; refusal names IBC + *"won't prescribe a phage."* Switch to **aging** → *"won't compute a patient's biological age from scRNA-seq."* | "Keystone engages the phage and aging briefs — and responsibly refuses to prescribe a phage or compute a patient's biological age. It shows the evidence and the rigor. The guardrail is the point." | Responsible-AI across 3 frontiers — what Gladstone respects |
| **2:40 – 3:00** | Claude Desktop → *"Before I submit this R01, are any of my 47 references retracted or corrected?"* → `check_reference_integrity` fires via MCP. Fade to hero. | "Same check, inside Claude Desktop. No app open." | Outlast-the-week flex |

*Optional live-Claude beat (needs `ANTHROPIC_API_KEY`): during the loop, the
Reviewer's critique renders as real Claude prose and the badge flips
"· deterministic" → "· Claude." If no key, the badge honestly reads
deterministic — do not fake it.*

---

## Numbers to state honestly (no marketing wrapper)

- **Load-bearing classifier: 0.818 agreement** on 44 labelled citing sentences
  per domain × 2 domains. Note in narration: agreement on self-labelled sets
  is a floor, not a ceiling. Do NOT wrap it in "proof of trust."
- **Flaw-catch: 2 of 4 planted flaws caught, precision 1.0, recall 0.5**
  (heuristic reasoner offline). State it exactly. When Claude is live,
  re-measure and update this line before shooting.
- **Retraction detection: 100 percent on retractions Crossref already knows
  about.** Phrase it as *"Crossref lookups are exact; retractions Crossref
  knows about, Keystone flags."* — do not imply Keystone discovers retractions
  Crossref hasn't recorded.

## Failure modes to rehearse for

- **Live Claude rate limit** → the summary shows "· deterministic" not "· Claude." Recover by refreshing once; the template is honest either way.
- **Import network flake** → offline mode is default in Docker. If the network fixture path fails, the built-in samples still work.
- **Multi-agent trace SSE stall** → the trace still renders on final `done`; skip past the streaming choreography if it stalls > 5s.

## What NOT to say

- No claims of "top 3," ranking, or competitor beating.
- No claims that Keystone replaces laboratory validation. It recommends experiments; it drafts artifacts.
- No marketing verbs (revolutionize, transform).
- No grandiose platform metaphors (a lab OS, an all-remembering lab brain, version-control-for-science). Keystone is an agentic scientific discovery workbench.
- No wrapping the recall-0.5 flaw-catch number in "proof of trust." State it exactly.

## Post-demo one-liner (submission summary tie-in)

*"Keystone is an agentic scientific discovery workbench for biomedical research.
It checks what a scientist is building on — flags retractions, cell-line
misidentifications, and citation contamination on their own reference list —
ranks the next experiment against the evidence, and drafts the NIH rigor and
STAR Methods artifacts they must submit. Every claim traces to a real DOI or
is explicitly unresolved; nothing is fabricated. Keystone recommends
experiments and drafts artifacts; it never replaces laboratory validation or
scientific judgment."*
