"""
keystone.agents.cell_eval
==========================
A reproducible, deterministically-judged evaluation of Keystone's Research Cell +
target ranking — the scientific-correctness invariants MEASURED on the real system,
not asserted in prose. Each case runs the actual agents/ranking and a deterministic
judge returns pass/fail + the evidence a scientist can re-check.

This is the agent-eval discipline (reproducible cases, deterministic judges, a
scoreboard, versioned) applied to the science instead of to coding agents.

Honesty (non-negotiable):
  * No case is rigged to pass — the accompanying canary test breaks each invariant and
    proves the judge flips to FAIL.
  * No number is fabricated: every verdict is computed from a real run of the real code.
  * A failing case is reported as failing; the scoreboard never rounds a failure up.
"""
from __future__ import annotations

import json

# module-level imports so a test can monkeypatch them to prove the judges have teeth
from keystone.deterministic.research_cell_run import run_research_cell, _fingerprint
from keystone.deterministic.target_ranking import rank_targets
from keystone.deterministic.research_cell import swarm_vs_cell

_PREPRINT = "https://www.biorxiv.org/content/10.64898/2025.12.23.696273v1"


def _case(cid: str, prop: str, passed: bool, evidence: str) -> dict:
    return {"id": cid, "property": prop, "passed": bool(passed), "evidence": evidence}


# ---- the cases: each runs the REAL system and judges deterministically ------
def _preprint_not_primary(r: dict) -> dict:
    admitted = {c["id"] for c in r["admitted_to_ranking"]}
    corro = {c["id"] for c in r["corroboration"]}
    ok = "lit:FBXO32" not in admitted
    return _case("preprint-not-primary",
                 "a not-peer-reviewed preprint is never PRIMARY ranking support",
                 ok, f"lit:FBXO32 admitted={not ok}; corroboration={sorted(corro)}")


def _synthetic_rejected(r: dict) -> dict:
    rejected = {c["id"] for c in r["rejected"]}
    admitted = {c["id"] for c in r["admitted_to_ranking"]}
    ok = ({"classifier:synthetic", "atlas:embedding"} <= rejected
          and not ({"classifier:synthetic", "atlas:embedding"} & admitted))
    return _case("synthetic-rejected",
                 "synthetic classifier + illustrative atlas cannot become ranking evidence",
                 ok, f"rejected⊇{{classifier,atlas}}={ok}")


def _reviewer_gate(r: dict) -> dict:
    reviewer = next(a for a in r["agents"] if a["name"] == "Reviewer Agent")
    approved = {d["id"] for d in reviewer["claims"] if d["text"].startswith("APPROVE")}
    admitted = {c["id"] for c in r["admitted_to_ranking"]}
    rejected = {c["id"] for c in r["rejected"]}
    ok = admitted <= approved and rejected.isdisjoint(admitted)
    return _case("reviewer-gate",
                 "nothing reaches primary support without Reviewer APPROVE; rejected∩admitted=∅",
                 ok, f"admitted⊆approved={admitted <= approved}; disjoint={rejected.isdisjoint(admitted)}")


def _tool_execution_real(r: dict) -> dict:
    from keystone import gladstone_data
    phantom = [a["name"] for a in r["agents"]
               if len(a["tool_calls"]) != len(a["tool_receipts"])]
    da = next(a for a in r["agents"] if a["name"] == "Data Analysis Agent")
    rc = next((x for x in da["tool_receipts"]
               if x["tool"].startswith("gladstone_data.all_regulator")), None)
    match = bool(rc) and rc["evidence"] == _fingerprint(gladstone_data.all_regulator_effects())
    ok = not phantom and match
    return _case("tool-execution-real",
                 "every tool call has a receipt whose fingerprint matches an independent re-run",
                 ok, f"phantom_calls={phantom or 'none'}; gladstone_receipt_matches_rerun={match}")


def _every_admitted_has_source(r: dict) -> dict:
    bad = [c["id"] for c in r["admitted_to_ranking"]
           if not c.get("source_id") or c["source_id"] == "—"]
    return _case("admitted-has-source",
                 "every claim admitted to the ranking carries a real source id",
                 not bad, f"admitted_without_source={bad or 'none'}")


def _no_secret_leak(r: dict) -> dict:
    blob = json.dumps(r, default=str)
    ok = "sk-ant-" not in blob and "ANTHROPIC_API_KEY" not in blob
    return _case("no-secret-leak",
                 "no API key or secret appears anywhere in the agent run output",
                 ok, "no 'sk-ant-' / 'ANTHROPIC_API_KEY' token in serialized run" if ok
                 else "SECRET TOKEN FOUND IN OUTPUT")


def _counterfactual_recompute() -> dict:
    base = {x["gene"]: x["composite"] for x in rank_targets()["ranking"]}
    after = {x["gene"]: x["composite"] for x in rank_targets(excluded_sources=[_PREPRINT])["ranking"]}
    fbxo_drop = base["FBXO32"] - after["FBXO32"]
    others_stable = all(abs(base[g] - after[g]) < 1e-9 for g in ("STAT6", "RARA", "GATA3"))
    ok = fbxo_drop > 0.1 and others_stable
    return _case("counterfactual-recompute",
                 "excluding the preprint genuinely drops FBXO32 and leaves other targets unchanged",
                 ok, f"FBXO32 Δ={fbxo_drop:+.3f}; others_unchanged={others_stable}")


def _doi_form_robust() -> dict:
    forms = [_PREPRINT, "10.64898/2025.12.23.696273", "DOI:10.64898/2025.12.23.696273",
             "https://doi.org/10.64898/2025.12.23.696273", "PREPRINT"]
    vals = {round(next(x["composite"] for x in rank_targets(excluded_sources=[f])["ranking"]
                       if x["gene"] == "FBXO32"), 6) for f in forms}
    ok = len(vals) == 1
    return _case("doi-form-robust",
                 "excluding by any canonical DOI form recomputes identically (no silent no-op)",
                 ok, f"distinct_results_across_{len(forms)}_forms={len(vals)}")


def _ranking_explainable() -> dict:
    out = rank_targets()
    eight = {"functional_effect", "activation_specificity", "type2_pathway",
             "disease_relevance", "tractability", "safety_risk", "integrity_risk",
             "missing_evidence"}
    labels = set(out["evidence_labels"]) | set(out["tractability_labels"])
    scored = {"functional_effect", "activation_specificity", "type2_pathway",
              "disease_relevance", "tractability", "safety_risk", "integrity_risk"}
    bad = []
    for cand in out["ranking"]:
        if set(cand["components"]) != eight:
            bad.append(f"{cand['gene']}:components")
        for k in scored:                       # missing_evidence is a list of gaps, not scored
            c = cand["components"][k]
            if not c.get("source") or c.get("label") not in labels or not c.get("formula"):
                bad.append(f"{cand['gene']}.{k}")
    weights_shown = isinstance(out.get("weights"), dict) and len(out["weights"]) >= 7
    ok = not bad and weights_shown
    return _case("ranking-explainable",
                 "every candidate exposes all 8 labeled+sourced components with weights shown (no opaque score)",
                 ok, f"defects={bad[:3] or 'none'}; weights_shown={weights_shown}")


def _retracted_excluded_by_gate() -> dict:
    b = swarm_vs_cell("gbm")
    cell_bad = b["cell"]["retracted_or_concern_cited"]
    swarm_bad = b["swarm"]["retracted_or_concern_cited"]
    ok = cell_bad == 0 and swarm_bad >= 1
    return _case("retracted-excluded",
                 "the integrity gate cites 0 retracted sources where the no-gate swarm cites ≥1",
                 ok, f"cell_retracted_cited={cell_bad}; swarm_retracted_cited={swarm_bad}")


def run_cell_eval(domain: str = "tcell") -> dict:
    """Run every scientific-correctness case against the REAL system and score it."""
    r = run_research_cell(domain)
    cases = [
        _preprint_not_primary(r),
        _synthetic_rejected(r),
        _reviewer_gate(r),
        _tool_execution_real(r),
        _every_admitted_has_source(r),
        _no_secret_leak(r),
        _counterfactual_recompute(),
        _doi_form_robust(),
        _ranking_explainable(),
        _retracted_excluded_by_gate(),
    ]
    passed = sum(c["passed"] for c in cases)
    n = len(cases)
    return {
        "domain": domain,
        "run_id": r["run_id"],
        "n": n,
        "passed": passed,
        "failed": n - passed,
        "pass_rate": round(passed / n, 3),
        "all_pass": passed == n,
        "cases": cases,
        "note": ("Deterministic scientific-correctness eval over the REAL Research Cell + "
                 "ranking. Every verdict is computed from a live run; a failing case is "
                 "reported as failing. Judges are proven to have teeth by the canary test."),
    }
