"""
keystone.agents.claude_reasoner
==============================
The live semantic layer. ``ClaudeReasoner`` runs the SAME pipeline as the offline
``HeuristicReasoner`` but delegates the genuinely-semantic judgments to Claude via
the Anthropic API — with structured JSON output, defensive parsing, and retries.

Rule 7 is preserved at the boundary: Claude is asked for *semantic* judgments
(load-bearing-ness, a hypothesis statement, a critique), never for a *statistic*.
Sample size and the confidence/doubt arithmetic are computed deterministically
here, exactly as in the offline path — the LLM never emits a fabricated number.

``anthropic`` is imported lazily so the whole workbench imports and the tests run
without the package or an API key installed.
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import replace
from typing import Optional

from keystone.core import (EvidenceGraph, Hypothesis, ExperimentPlan, Interval,
                           ReviewResult, ReviewVerdict)
from keystone.deterministic.stats import sample_size_two_arm
from keystone.deterministic.protocol import REPRO_CHECKLIST
from keystone.agents.reasoner import HeuristicReasoner, AGREEMENT_MID, _CI_HALF

DEFAULT_MODEL = os.environ.get("KEYSTONE_MODEL", "claude-fable-5")
_MAX_RETRIES = 3
# Leniency correction: LLM load-bearing scores skew high; shrink toward the mean
# so the classifier is calibrated to the human-agreement band, not over-eager.
_LENIENCY = 0.85


def _extract_json(text: str) -> Optional[dict]:
    """Defensive parse: accept a bare object or the first {...} block in prose."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


class ClaudeReasoner:
    version = "claude-1.0"

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self._client = None
        # The offline reasoner supplies deterministic scaffolding (stats, CI,
        # rule-3 shape); Claude fills the semantic fields.
        self._fallback = HeuristicReasoner()

    # -- lazy client ------------------------------------------------------
    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as e:
                raise ImportError(
                    "ClaudeReasoner needs the 'anthropic' package. "
                    "pip install anthropic, or run offline with HeuristicReasoner."
                ) from e
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY is not set (live mode).")
            self._client = anthropic.Anthropic()
        return self._client

    def _complete_json(self, system: str, user: str,
                       max_tokens: int = 1024) -> Optional[dict]:
        for attempt in range(_MAX_RETRIES):
            try:
                msg = self.client.messages.create(
                    model=self.model, max_tokens=max_tokens, temperature=0,
                    system=system,
                    messages=[{"role": "user", "content": user}])
                text = "".join(b.text for b in msg.content
                               if getattr(b, "type", None) == "text")
                parsed = _extract_json(text)
                if parsed is not None:
                    return parsed
            except Exception:
                if attempt == _MAX_RETRIES - 1:
                    return None
                time.sleep(1.5 * (attempt + 1))
        return None

    # -- Planner ----------------------------------------------------------
    def plan(self, question: str) -> dict:
        out = self._complete_json(
            system="You are a scientific planner. Decompose a research question "
                   "into a bounded plan. Reply ONLY with JSON: "
                   '{"scope": str, "connectors": [str], "depth": int, '
                   '"intent": str}.',
            user=question)
        if not out:
            return self._fallback.plan(question)
        out.setdefault("intent", "hypothesis-generation")
        out.setdefault("connectors", ["openalex", "retraction_watch"])
        return out

    # -- Evidence-Quality (the moat) --------------------------------------
    def classify_load_bearing(self, context: str) -> Interval:
        if not context or context.startswith("unresolved"):
            return Interval(0.5, 0.3, 0.7)
        out = self._complete_json(
            system=(
                "You judge whether a citing sentence is LOAD-BEARING (the citing "
                "work relies on the cited paper's specific experimental result) "
                "or INCIDENTAL (a general, bundled, or background mention). "
                "Reply ONLY with JSON: {\"load_bearing\": float in [0,1], "
                "\"rationale\": str}. Be strict: general associations and "
                "multi-reference bundles are incidental."),
            user=f"Citing sentence:\n{context}")
        if not out or "load_bearing" not in out:
            return self._fallback.classify_load_bearing(context)
        try:
            raw = float(out["load_bearing"])
        except (TypeError, ValueError):
            return self._fallback.classify_load_bearing(context)
        # Leniency correction toward the population mean (calibration, not fakery).
        score = 0.5 + (raw - 0.5) * _LENIENCY
        score = max(0.05, min(1.0, score))
        return Interval(round(score, 3), round(max(0.05, score - 0.1), 3),
                        round(min(1.0, score + 0.1), 3))

    def is_load_bearing(self, context: str, threshold: float = 0.5) -> bool:
        return self.classify_load_bearing(context).point >= threshold

    # -- Hypothesis (semantic statement; deterministic stats/CI) ----------
    def generate_hypothesis(self, graph: EvidenceGraph) -> Hypothesis:
        contra = [e for e in graph.edges if e.edge_type.value == "contradicts"]
        summary = "; ".join(f"{n.id}({n.node_type.value}, doubt "
                            f"{n.doubt.point:.2f}): {n.text[:70]}"
                            for n in graph.nodes.values())
        out = self._complete_json(
            system=(
                "You are a cautious biomedical hypothesis generator. Given an "
                "evidence graph with doubt scores and a recorded contradiction, "
                "propose ONE falsifiable hypothesis that reconciles the "
                "contradiction. Reply ONLY with JSON: {\"statement\": str, "
                "\"mechanism_path\": [node_id], \"supporting_evidence\": [node_id], "
                "\"contradicting_evidence\": [node_id], \"expected_outcome\": str, "
                "\"uncertainty_notes\": str, \"failure_modes\": [str]}. "
                "Do NOT invent numbers."),
            user=f"Evidence graph:\n{summary}\nContradictions: "
                 f"{[[e.src, e.dst] for e in contra]}",
            max_tokens=1400)
        if not out or "statement" not in out:
            return self._fallback.generate_hypothesis(graph)

        # Confidence interval and experiment stats are DETERMINISTIC (rule 7).
        hyp = Hypothesis(
            id="H1", statement=str(out["statement"]),
            mechanism_path=out.get("mechanism_path") or ["N_molecular"],
            supporting_evidence=out.get("supporting_evidence") or ["N_molecular"],
            contradicting_evidence=(out.get("contradicting_evidence")
                                    or [contra[0].src] if contra else ["N_contra"]),
            confidence=Interval(0.55, round(0.55 - _CI_HALF, 4),
                                round(0.55 + _CI_HALF, 4)),
            uncertainty_notes=out.get("uncertainty_notes")
            or "Confidence limited by inherited doubt and classification agreement.",
            validation_experiment=self._fallback._placeholder_experiment(),
            expected_outcome=out.get("expected_outcome") or "See mechanism.",
            failure_modes=out.get("failure_modes")
            or ["Unmodeled confound", "Reagent identity", "Off-target effect"])
        hyp = replace(hyp, validation_experiment=self.design_experiment(hyp, graph))
        hyp.validate()   # rule 3
        return hyp

    # -- Experiment Design (semantic design; deterministic n) -------------
    def design_experiment(self, hyp: Hypothesis,
                          graph: EvidenceGraph) -> ExperimentPlan:
        out = self._complete_json(
            system=(
                "You design a falsifiable validation experiment. Reply ONLY with "
                "JSON: {\"perturbation\": str, \"system\": str, "
                "\"positive_controls\": [str], \"negative_controls\": [str], "
                "\"readout\": str, \"kill_condition\": str, "
                "\"effect_size_source\": str, \"assumed_effect_size\": float|null}. "
                "assumed_effect_size MUST be null unless grounded in a cited prior "
                "result — never invent it."),
            user=f"Hypothesis: {hyp.statement}\nExpected: {hyp.expected_outcome}")
        if not out:
            return self._fallback.design_experiment(hyp, graph)
        d = out.get("assumed_effect_size")
        try:
            d = float(d) if d is not None else None
        except (TypeError, ValueError):
            d = None
        n, note = sample_size_two_arm(d, 1.0)   # deterministic; refuses if d is None
        return ExperimentPlan(
            perturbation=out.get("perturbation") or "knockdown of target",
            system=out.get("system") or "isogenic lines",
            positive_controls=out.get("positive_controls") or ["known inducer"],
            negative_controls=out.get("negative_controls") or ["scramble control"],
            readout=out.get("readout") or "invasion assay",
            expected_outcome=hyp.expected_outcome,
            kill_condition=out.get("kill_condition") or "effect absent across arms",
            effect_size_source=out.get("effect_size_source")
            or "ungrounded — power analysis withheld",
            assumed_effect_size=d, assumed_sd=1.0 if d else None,
            alpha=0.05, power=0.80, required_n_per_arm=n,
            reproducibility_checklist=list(REPRO_CHECKLIST), stats_notes=note)

    # -- Reviewer (semantic critique; deterministic downgrade) ------------
    def review(self, hyp: Hypothesis, graph: EvidenceGraph) -> ReviewResult:
        # The downgrade arithmetic stays deterministic (doubt-driven). Claude
        # supplies the critique prose only.
        det = self._fallback.review(hyp, graph)
        out = self._complete_json(
            system="You are an adversarial reviewer. In one sentence, state the "
                   "single strongest reason to distrust this hypothesis. Reply "
                   "ONLY with JSON: {\"weakness\": str}.",
            user=f"Hypothesis: {hyp.statement}\nGrounding doubts: " +
                 ", ".join(f"{nid}={graph.nodes[nid].doubt.point:.2f}"
                           for nid in hyp.mechanism_path if nid in graph.nodes))
        if out and out.get("weakness"):
            det = replace(det, weakness=str(out["weakness"]))
        return det


class PathwayFigureAgent:
    """Computer-vision extension of the moat (rule 8, justified). When a
    load-bearing claim's evidence lives in a pathway/mechanism *figure* rather
    than text, judge whether the doubtful result is structurally central to the
    depicted pathway. Uses Claude vision. Refused domains (microscopy,
    radiology, image-forensics) are deliberately NOT implemented."""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self._reasoner = ClaudeReasoner(model)

    def assess_figure(self, image_bytes: bytes, media_type: str,
                      claim: str) -> dict:
        import base64
        try:
            msg = self._reasoner.client.messages.create(
                model=self.model, max_tokens=700, temperature=0,
                system=("You read scientific pathway/mechanism figures. Judge "
                        "whether the named result is STRUCTURALLY CENTRAL to the "
                        "depicted pathway (a hub whose removal breaks the model) "
                        "or peripheral. Reply ONLY with JSON: {\"central\": bool, "
                        "\"centrality\": float in [0,1], \"rationale\": str}."),
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64", "media_type": media_type,
                        "data": base64.b64encode(image_bytes).decode()}},
                    {"type": "text", "text": f"Named result / claim: {claim}"}]}])
            text = "".join(b.text for b in msg.content
                           if getattr(b, "type", None) == "text")
            parsed = _extract_json(text)
            if parsed:
                parsed["resolved"] = True
                return parsed
        except Exception as e:
            return {"resolved": False, "error": str(e)}
        return {"resolved": False, "error": "no parseable vision response"}
