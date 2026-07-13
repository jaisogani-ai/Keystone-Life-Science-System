# Contributing to Keystone

Keystone is an agentic scientific discovery workbench for biomedical research — a tool a
scientist installs on Monday and still relies on six months later. One rule
governs every contribution, and it is the reason a lab could trust this
system:

**Keystone recommends experiments and drafts artifacts; it never replaces
laboratory validation or scientific judgment.** AI proposes, scientists decide,
experiments verify.

## The semantic / deterministic boundary (do not blur it)

There are exactly two layers. Every function belongs to one of them.

| Layer | What lives here | May it call an LLM? |
|-------|-----------------|---------------------|
| **Semantic** (`keystone/agents/`) | judgments only a language model can make: planning a question, classifying a citing sentence as load-bearing, proposing a hypothesis statement, arguing against it | **Yes** — this is the only place Claude runs |
| **Deterministic** (`keystone/deterministic/`, `keystone/connectors/`, `keystone/artifacts/`, `core`, `workbench`, `reasoning_panel`, `replay`) | statistics, doubt propagation, protocol checks, database lookups, provenance/Ledger hashing, timeline, every rendered artifact | **No — ever** |

### The three lines you may not cross

1. **Never let an LLM emit a statistic.** Sample size, confidence intervals,
   doubt values, readiness ratios — all computed deterministically. If you are
   tempted to prompt for a number, stop: compute it in `deterministic/`, or
   refuse and flag the gap (see `sample_size_two_arm`, which returns `None` when
   there is no grounded effect size rather than inventing one).

2. **Never fabricate an identifier or a citing sentence.** A connector returns
   real data or a `resolved: False` / `unresolved` marker. It never guesses a
   DOI, accession, or context. New connectors must follow
   `keystone/connectors/registry.py` and go through `http_cache` (cache → live →
   fixture).

3. **Every displayed value is a projection of something already computed.** The
   panels in `reasoning_panel.py` invent nothing; they read the graph and the
   Ledger. If a dimension cannot be measured this week (e.g. quantitative
   novelty), it is labeled a qualitative estimate — never dressed up as a
   percentage.

## Definition of done

- `python -m pytest` is green (109 tests and counting).
- The reproducibility hash is stable across re-runs (`run_workbench.py` asserts it).
- New capability ships with a test. New semantic behavior ships with a
  calibration measurement (`calibrate.py`), not a claim.
- No new dependency in the deterministic layer beyond the standard library +
  `requests`.

## Refreshing the pinned real data

```bash
KEYSTONE_LIVE=1 python -m keystone.connectors.capture   # re-pin fixtures
```

Fixtures are committed real API responses; the ephemeral HTTP cache is not.
