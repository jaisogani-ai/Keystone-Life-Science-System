"""
keystone.discovery_run
=====================
The cross-wire that makes Keystone's capabilities ONE self-correcting system
instead of separate tabs. It composes three shipped layers into a single loop:

  Literature Pattern Miner  ─contradiction→  Decision Engine  ─ranks→  next
  experiment  ─validated by→  Laboratory Agent  ─QC verdict→  downgrades the
  confidence of the very hypothesis the experiment was meant to test.

Everything here is COMPOSITION of existing deterministic functions — no new
scoring, no modified core. A literature contradiction becomes a real
`CandidateHypothesis` (kind='literature_contradiction') and is ranked by the
SAME auditable scorer as every graph-derived hypothesis. A failing plate
produces a confidence downgrade annotation on the recommendation. Rule 7
holds throughout: every number comes from the deterministic engine.
"""
from __future__ import annotations

import hashlib

from keystone.core import ExperimentPlan
from keystone.decision_engine import decide
from keystone.deterministic.hypothesis_space import (
    CandidateHypothesis, generate_candidates,
)
from keystone.deterministic.decision_metrics import rank_candidates
from keystone.deterministic.stats import sample_size_two_arm
from keystone.agents.pattern_miner import mine_patterns
from keystone.agents.bench_reviewer import review_plate
from keystone.reasoning_receipt import build_receipt, reasoning_narrative


def _resolve_experiment(target: str) -> ExperimentPlan:
    """A pre-registered head-to-head experiment that settles which direction of
    a contradicted claim is real. The kill-condition is named; n is computed
    (never fabricated) via the shared power analysis."""
    n, note = sample_size_two_arm(0.8, 1.0)
    return ExperimentPlan(
        perturbation=(f"pre-registered head-to-head {target} perturbation under "
                      f"both studies' reported conditions"),
        system="two independent labs, pre-registered",
        positive_controls=["known-direction positive control"],
        negative_controls=["non-targeting control"],
        readout="pre-registered primary phenotype readout",
        expected_outcome="one reported direction replicates; the other does not",
        kill_condition=(f"both directions replicate equally — the {target} "
                        f"contradiction is a genuine context effect, not an "
                        f"artifact"),
        effect_size_source=("assumed Cohen's d=0.8 (labeled planning assumption "
                            "— replace with a measured prior)"),
        assumed_effect_size=0.8, assumed_sd=1.0, alpha=0.05, power=0.80,
        required_n_per_arm=n, stats_notes=note)


def _contradiction_candidates(lit_result) -> list:
    """Turn each literature contradiction pair into a rankable hypothesis. The
    grounding is the REAL DOI pair; mechanism_path is empty on purpose (DOIs
    are not graph nodes) so the scorer treats it honestly — a literature-only
    hypothesis carries default uncertainty, never an inflated graph score."""
    cands = []
    for hit in lit_result.report.hits:
        if hit.kind != "contradiction_cluster":
            continue
        for i, pair in enumerate(hit.detail.get("pairs", [])[:3]):
            target = pair.get("target", "the target")
            pos = pair.get("positive_doi", "")
            neg = pair.get("negative_doi", "")
            cands.append(CandidateHypothesis(
                id=f"L{i + 1}",
                kind="literature_contradiction",
                statement=(f"RESOLVE CONTRADICTION: the literature disagrees on "
                           f"whether {target} promotes or inhibits the phenotype "
                           f"({pos} vs {neg}); a decisive head-to-head experiment "
                           f"settles the direction before either is built upon."),
                grounds_on=f"{pos} vs {neg}",
                supporting=[pos] if pos else [],
                contradicting=[neg] if neg else [],
                mechanism_path=[],
                experiment=_resolve_experiment(target),
                assumptions=[f"both studies measured {target} under comparable "
                             f"conditions"],
                failure_modes=["the disagreement is an uncontrolled context "
                               "variable, not a true contradiction"]))
    return cands


def _recommendation(top: dict, cand) -> dict:
    return {
        "hypothesis_id": top["id"], "kind": top["kind"],
        "source": top.get("source", "graph"),
        "statement": top["statement"],
        "why_first": top["why"],
        "priority_score": top["priority_score"]["value"],
        "information_gain": top["information_gain"]["value"],
        "risk": top["risk"]["value"],
        "experiment": {
            "perturbation": cand.experiment.perturbation,
            "system": cand.experiment.system,
            "n_per_arm": cand.experiment.required_n_per_arm,
        },
        "how_to_falsify": cand.experiment.kill_condition,
    }


def _bench_adjustment(recommendation: dict, bench_csv: str,
                      bench_fmt: str) -> dict:
    """Validate the recommended experiment's data. A failing plate downgrades
    confidence in the hypothesis it was meant to test — the loop closes."""
    d = review_plate(bench_csv, label="validation plate", fmt=bench_fmt).to_dict()
    if d["refused"]:
        return {"reviewed": True, "verdict": "refused", "reason": d["reason"],
                "applies_to": recommendation["hypothesis_id"]}
    verdict = d["verdict"]
    downgraded = verdict in ("downgraded", "rejected")
    reason = (
        f"the plate intended to validate {recommendation['hypothesis_id']} failed "
        f"QC ({verdict}). {d['weakness']} Any result inherits that doubt until the "
        f"QC issues are resolved."
        if downgraded else
        f"the validation plate passed QC; confidence in "
        f"{recommendation['hypothesis_id']} is not downgraded.")
    return {
        "reviewed": True,
        "verdict": verdict,
        "applies_to": recommendation["hypothesis_id"],
        "base_confidence": d["base_confidence"],
        "adjusted_confidence": d["adjusted_confidence"]["point"],
        "downgraded": downgraded,
        "reason": reason,
        "qc_metrics": d["qc_metrics"],
        "suggestions": d["suggestions"],
    }


def _run_hash(records: list, graph_hash: str, top_id: str) -> str:
    dois = sorted((r.get("doi") or "") for r in (records or []))
    payload = "|".join(dois) + f"|{graph_hash}|{top_id}"
    return "run:" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def run_discovery(corpus_records: list, domain: str = "gbm",
                  question: str = "", seed_doi: str = "",
                  bench_csv: str | None = None,
                  bench_fmt: str = "plate_reader_csv",
                  reasoner=None) -> dict:
    """Run the whole self-correcting loop and return one unified result.

    corpus_records:  OpenAlex-shaped papers to mine for contradictions.
    domain:          curated evidence graph the graph-derived hypotheses use.
    bench_csv:       optional plate-reader CSV validating the top experiment.
    reasoner:        optional live Fable 5 (Claude) reasoner. It is used ONLY to
                     write an advisory reasoning narrative for the receipt — the
                     ranking, sizing, and every hash stay deterministic, so the
                     run_hash is identical with or without a key (rule 7).
    """
    decision, graph, ledger, hyp, review = decide(domain)

    lit = mine_patterns(corpus_records or [], question=question,
                        seed_doi=seed_doi, scan_type="contradiction_scan")
    lit_cands = _contradiction_candidates(lit)

    base_cands = generate_candidates(graph, hyp, {})
    all_cands = base_cands + lit_cands
    by_id = {c.id: c for c in all_cands}

    ranking = rank_candidates(all_cands, graph, review)
    ranked = ranking["ranked"]
    for s in ranked:
        s["source"] = ("literature" if s["kind"] == "literature_contradiction"
                       else "graph")

    top = ranked[0]
    recommendation = _recommendation(top, by_id[top["id"]])
    # the highest-ranked literature-derived hypothesis — proof the contradiction
    # entered the decision board even when a graph hypothesis wins #1
    top_lit = next((s for s in ranked if s["source"] == "literature"), None)

    bench = None
    if bench_csv is not None:
        bench = _bench_adjustment(recommendation, bench_csv, bench_fmt)

    n_contra = sum(len(h.detail.get("pairs", []))
                   for h in lit.report.hits
                   if h.kind == "contradiction_cluster")

    loop = [
        {"stage": "Literature", "value": f"{n_contra} contradiction pair(s) "
         f"mined from {lit.report.corpus_size} paper(s)"},
        {"stage": "Hypothesis", "value": f"{len(lit_cands)} literature "
         f"contradiction(s) became rankable hypotheses"},
        {"stage": "Decision", "value": f"ranked with {len(base_cands)} graph "
         f"hypotheses → #1 = {top['id']} ({top['source']})"},
        {"stage": "Experiment", "value": recommendation["experiment"]["perturbation"][:70]},
        {"stage": "Bench QC", "value": (bench["verdict"] if bench
                                        else "no plate submitted")},
        {"stage": "Confidence", "value": (
            f"downgraded → {bench['adjusted_confidence']}"
            if bench and bench.get("downgraded") else "not downgraded")},
    ]

    # illustrative-DOI honesty: expose the synthetic-record set so the UI badges
    # any illustrative DOI shown in a literature hypothesis' grounding, exactly
    # as the Pattern Miner tab does — no synthetic DOI is ever shown as real.
    illustrative_dois = list((lit.provenance or {}).get("illustrative_dois", []))

    result = {
        "domain": domain,
        "graph_hash": ledger.graph_hash,
        "run_hash": _run_hash(corpus_records, ledger.graph_hash, top["id"]),
        "contradictions_found": n_contra,
        "n_literature_hypotheses": len(lit_cands),
        "n_graph_hypotheses": len(base_cands),
        "illustrative_dois": illustrative_dois,
        "competing_hypotheses": ranked,
        "weights": ranking["weights"],
        "recommendation": recommendation,
        "top_literature_hypothesis": ({
            "id": top_lit["id"], "rank": top_lit["rank"],
            "statement": top_lit["statement"],
            "grounds_on": top_lit["grounds_on"],
            "priority_score": top_lit["priority_score"]["value"],
        } if top_lit else None),
        "bench_review": bench,
        "loop": loop,
    }

    # Reasoning receipt: make the deterministic / Fable 5 / human split auditable.
    # The narrative is advisory Fable 5 prose (None offline); the receipt reads
    # only numbers the engine already computed — no new number, no hash change.
    narrative = reasoning_narrative(result, reasoner)
    result["receipt"] = build_receipt(result, narrative)
    return result
