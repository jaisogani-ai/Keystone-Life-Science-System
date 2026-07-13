"""
keystone.deterministic.research_cell_run
========================================
The **Keystone Research Cell** as an actually-executed, auditable run (Phase 2 ·
Priority 3). Exactly FIVE real agents, each of which performs a real task over real
inputs, calls real tools, and emits a structured output. Every output carries:
inputs · tool calls · structured claims · source ids · run id · failure state ·
reviewer status · timestamp · a reproducibility-ledger entry.

Hard rule (enforced here, proven by tests): **no agent output can affect the target
ranking until the Reviewer Agent approves it.** A claim reaches ``admitted_to_ranking``
only if the Integrity Agent did not exclude it AND the Reviewer Agent approved it.

Honesty: this is deterministic execution over the real evidence corpus + real
datasets the product already tracks — not a swarm of look-alike LLMs, not fabricated
agent chatter. The five agents are the controlled cell; the separate
``swarm_vs_cell`` control (research_cell.py) measures why the gate matters.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from dataclasses import dataclass, field, asdict

from keystone.deterministic.claim_status import node_claim

# The five real agents (Phase 2 · Priority 3). Ordered: analysts → gates.
CELL_AGENTS = [
    {"name": "Data Analysis Agent", "role": "runs the real Perturb-seq measurements + labeled classifier QC"},
    {"name": "Literature Evidence Agent", "role": "source-backed claims only (DOI / UniProt + exact locator)"},
    {"name": "Target Biology / Pathway Agent", "role": "maps regulator → pathway → disease onto real databases"},
    {"name": "Integrity & Retraction Agent", "role": "retraction / preprint / missing-control → excludes from support"},
    {"name": "Reviewer Agent", "role": "approves or rejects every claim; only approved claims can affect ranking"},
]
_GATE_AGENTS = {"Integrity & Retraction Agent", "Reviewer Agent"}


def _now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _run_id(domain: str, salt: str) -> str:
    """Deterministic, content-addressed run id (reproducible across runs)."""
    return "rc_" + hashlib.sha256(f"{domain}:{salt}".encode()).hexdigest()[:12]


# transparent cost model — mirrors the swarm-vs-cell estimate (research_cell.py).
_EST_TOKENS_PER_AGENT = 6000
_USD_PER_1K_TOKENS = 0.009


def _default_cost() -> dict:
    """Honest per-agent cost record. The cell runs DETERMINISTICALLY offline, so live
    model tokens are 0 (not fabricated); ``est_*`` is a clearly-labeled estimate with
    its formula, never presented as a measured bill or used for any scientific claim."""
    return {"mode": "deterministic", "live_model_tokens": 0,
            "est_tokens_if_live": _EST_TOKENS_PER_AGENT,
            "est_usd_if_live": round(_EST_TOKENS_PER_AGENT / 1000 * _USD_PER_1K_TOKENS, 4),
            "note": "deterministic — 0 live tokens offline; est_* is a labeled estimate, not a bill"}


def _claim(cid, text, source_id, integrity, claim_type):
    """One structured claim an agent emits. ``integrity`` ∈ normal|retracted|concern|
    not_peer_reviewed|unverified ; ``claim_type`` ∈ evidence|computed|hypothesis|missing."""
    return {"id": cid, "text": text, "source_id": source_id,
            "integrity": integrity, "claim_type": claim_type}


def _fingerprint(result) -> dict:
    """A VERIFIABLE execution receipt for a real tool result: item count (when sized)
    + a short content hash of its canonical JSON. Re-running the tool must reproduce
    this fingerprint — which is how a reviewer proves the agent actually executed the
    tool and consumed real output, not emitted a decorative string (audit Layer 7:
    hallucinated execution)."""
    try:
        blob = json.dumps(result, sort_keys=True, default=str)
    except Exception:
        blob = repr(result)
    return {"n": (len(result) if hasattr(result, "__len__") else None),
            "sha": hashlib.sha256(blob.encode()).hexdigest()[:12]}


def _tooled():
    """Returns ``(tool_calls, receipts, rec)``. ``rec(name, result)`` records a REAL
    tool call — it appends the human-readable name AND an execution receipt that
    fingerprints the actual result, then returns the result so the agent is forced to
    consume it. Only tools that really run get a receipt; nothing decorative."""
    tool_calls, receipts = [], []

    def rec(name, result):
        tool_calls.append(name)
        receipts.append({"tool": name, "ok": True, "evidence": _fingerprint(result)})
        return result
    return tool_calls, receipts, rec


@dataclass
class AgentRun:
    name: str
    role: str
    run_id: str
    timestamp: str
    inputs: dict
    tool_calls: list
    claims: list
    source_ids: list
    status: str = "ok"                 # ok | no_data | failed
    reviewer_status: str = "pending"   # pending | approved | rejected | n/a
    error: str | None = None
    ledger_entry: dict = field(default_factory=dict)
    task_id: str = ""                  # per-agent, derived from run_id + name
    cost: dict = field(default_factory=_default_cost)
    tool_receipts: list = field(default_factory=list)  # proof each tool really ran

    def __post_init__(self):
        if not self.task_id:
            self.task_id = "task_" + hashlib.sha256(
                f"{self.run_id}:{self.name}".encode()).hexdigest()[:10]

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# The five agents. Each returns an AgentRun with real tool calls + claims.
# ---------------------------------------------------------------------------
def _data_analysis_agent(domain: str, rid: str) -> AgentRun:
    tool_calls, receipts, rec = _tooled()
    claims, sources = [], []
    status = "ok"
    try:
        from keystone import gladstone_data
        effects = rec("gladstone_data.all_regulator_effects()",
                      gladstone_data.all_regulator_effects())
        p = gladstone_data.provenance()
        doi = f"DOI:{p['doi']}"
        sources.append(doi)
        integ = "normal" if p.get("peer_reviewed") else "not_peer_reviewed"
        for gene, e in effects.items():
            if not e:
                continue
            r = e.get("crossdonor_correlation_mean")
            claims.append(_claim(
                f"measured:{gene}",
                f"{gene} knockdown → {e.get('n_downstream')} downstream DE genes "
                f"(on-target KD {e.get('ontarget_effect_size'):+.1f}, cross-donor "
                f"r={r:.2f})" if r is not None else
                f"{gene} knockdown → {e.get('n_downstream')} downstream DE genes",
                doi, integ, "evidence"))
        # the synthetic classifier is run + reported, but marked as non-ranking.
        from keystone.ml.th2_signature import run_analysis
        a = rec("th2_signature.run_analysis()  [SYNTHETIC · cross-check]", run_analysis())
        claims.append(_claim(
            "classifier:synthetic",
            f"Type-2 classifier ({a['data_kind']} matrix) AUROC "
            f"{(a['model']['auroc'] or {}).get('mean')} — method cross-check only, "
            f"NOT a ranking input",
            "keystone/ml/th2_signature.py", "unverified", "computed"))
        # Visual Evidence Lab: the Data Analysis Agent also creates/retrieves the
        # Cell-State Atlas run. Illustrative (synthetic matrix) → the Reviewer must
        # keep it OUT of ranking support.
        try:
            from keystone.ml.cell_atlas import compute_atlas
            atlas = rec("cell_atlas.compute_atlas()  [SYNTHETIC · illustrative]",
                        compute_atlas(domain))
            claims.append(_claim(
                "atlas:embedding",
                f"Cell-State Atlas PCA embedding ({atlas['n_cells']} cells, "
                f"run {atlas['run_id']}) — illustrative, NOT ranking evidence",
                f"cell_atlas:{atlas['run_id']}", "unverified", "computed"))
        except Exception:
            pass
        if not [c for c in claims if c["integrity"] != "unverified"]:
            status = "no_data"
    except Exception as exc:
        status, err = "failed", str(exc)
        return AgentRun("Data Analysis Agent", CELL_AGENTS[0]["role"], rid, _now(),
                        {"domain": domain, "dataset": "Gladstone CD4+ Perturb-seq"},
                        tool_calls, claims, sources, status="failed", error=err,
                        tool_receipts=receipts)
    return AgentRun("Data Analysis Agent", CELL_AGENTS[0]["role"], rid, _now(),
                    {"domain": domain, "condition": "polarization"}, tool_calls,
                    claims, sources, status=status, tool_receipts=receipts)


def _literature_agent(domain: str, rid: str) -> AgentRun:
    tool_calls, receipts, rec = _tooled()
    claims, sources = [], []
    try:
        from keystone.deterministic.target_ranking import rank_targets
        ranking = rec("target_ranking.rank_targets()", rank_targets())["ranking"]
        for r in ranking:
            fe = r["components"]["functional_effect"]
            claims.append(_claim(
                f"lit:{r['gene']}",
                f"{r['gene']} — {fe['formula']}",
                fe["source"],
                "not_peer_reviewed" if fe["source"] == "PREPRINT" else "normal",
                "evidence" if fe["label"] == "Literature-supported" else "hypothesis"))
            sources.append(fe["source"])
    except Exception as exc:
        return AgentRun("Literature Evidence Agent", CELL_AGENTS[1]["role"], rid,
                        _now(), {"domain": domain}, tool_calls, claims, sources,
                        status="failed", error=str(exc), tool_receipts=receipts)
    return AgentRun("Literature Evidence Agent", CELL_AGENTS[1]["role"], rid, _now(),
                    {"domain": domain, "genes": "ranked regulators"}, tool_calls,
                    claims, sources, tool_receipts=receipts)


def _biology_agent(domain: str, rid: str) -> AgentRun:
    tool_calls, receipts, rec = _tooled()
    claims, sources = [], []
    try:
        from keystone.connectors.opentargets import type2_association
        for gene in ("GATA3", "STAT6", "RARA", "FBXO32"):
            try:
                ot = rec(f"opentargets.type2_association({gene})", type2_association(gene))
            except Exception:
                ot = None
            if ot and ot.get("disease"):
                sid = f"Open Targets:{ot.get('disease_id') or '—'}"
                claims.append(_claim(
                    f"bio:{gene}",
                    f"{gene} → {ot['disease']} association {ot['score']:.2f}",
                    sid, "normal", "evidence"))
                sources.append(sid)
            else:
                claims.append(_claim(
                    f"bio:{gene}", f"{gene} → no type-2 disease association found",
                    "Open Targets", "normal", "missing"))
    except Exception as exc:
        return AgentRun("Target Biology / Pathway Agent", CELL_AGENTS[2]["role"], rid,
                        _now(), {"domain": domain}, tool_calls, claims, sources,
                        status="failed", error=str(exc), tool_receipts=receipts)
    return AgentRun("Target Biology / Pathway Agent", CELL_AGENTS[2]["role"], rid,
                    _now(), {"domain": domain}, tool_calls, claims, sources,
                    tool_receipts=receipts)


# hard integrity failures — a claim on one of these can never support a conclusion.
_HARD_EXCLUDE = ("retracted", "concern", "unverified")


def _integrity_agent(domain: str, rid: str, upstream: list) -> AgentRun:
    """Triages every upstream claim on its source integrity. Retracted / concern /
    unverified → HARD EXCLUDE (can never support a conclusion). Preprint
    (not-peer-reviewed) → PROVISIONAL (admissible as corroboration, flagged, never
    primary support). Everything else → cleared. This is a gate before ranking."""
    tool_calls, receipts, rec = _tooled()
    verdicts, sources = [], []
    for c in upstream:
        if c["integrity"] in _HARD_EXCLUDE:
            verdict, ctype = "EXCLUDE — " + c["integrity"].replace("_", " "), "missing"
        elif c["integrity"] == "not_peer_reviewed":
            verdict, ctype = "PROVISIONAL — preprint (corroboration only)", "evidence"
        else:
            verdict, ctype = "cleared for support", "evidence"
        verdicts.append(_claim(c["id"], verdict, c["source_id"], c["integrity"], ctype))
        sources.append(c["source_id"])
    rec("integrity.triage(upstream_claims)", [v["text"] for v in verdicts])
    return AgentRun("Integrity & Retraction Agent", CELL_AGENTS[3]["role"], rid, _now(),
                    {"domain": domain, "claims_reviewed": len(upstream)}, tool_calls,
                    verdicts, sorted(set(sources)), reviewer_status="n/a",
                    tool_receipts=receipts)


def _reviewer_agent(domain: str, rid: str, upstream: list, integrity: AgentRun) -> AgentRun:
    """The final gate, with three dispositions:
      * APPROVE — peer-reviewed evidence with an exact source → primary ranking support.
      * CORROBORATION — preprint measured evidence with a source → admitted but flagged
        provisional; it never becomes primary support on its own.
      * REJECT — no source, unsupported (hypothesis/missing), hard-excluded (retracted),
        or the synthetic cross-check.
    Only APPROVE claims may affect the ranking as primary support."""
    tool_calls, receipts, rec = _tooled()
    excluded_ids = {v["id"] for v in integrity.claims if v["text"].startswith("EXCLUDE")}
    provisional_ids = {v["id"] for v in integrity.claims if v["text"].startswith("PROVISIONAL")}
    decisions, sources = [], []
    for c in upstream:
        has_source = bool(c["source_id"]) and c["source_id"] != "—"
        supportable = c["claim_type"] in ("evidence", "computed")
        synthetic = c["id"] == "classifier:synthetic"
        if synthetic:
            disp, reason = "REJECT", "non-ranking cross-check (synthetic)"
        elif c["id"] in excluded_ids:
            disp, reason = "REJECT", "hard-excluded by integrity (retracted/unverified)"
        elif not has_source:
            disp, reason = "REJECT", "no exact source link"
        elif not supportable:
            disp, reason = "REJECT", "unsupported (hypothesis/missing)"
        elif c["id"] in provisional_ids:
            disp, reason = "CORROBORATION", "preprint — provisional, not primary support"
        else:
            disp, reason = "APPROVE", "peer-reviewed evidence with exact source"
        decisions.append(_claim(c["id"], f"{disp} — {reason}", c["source_id"],
                                c["integrity"], "evidence" if disp != "REJECT" else "missing"))
        sources.append(c["source_id"])
    rec("reviewer.adjudicate(upstream_claims)", [d["text"] for d in decisions])
    return AgentRun("Reviewer Agent", CELL_AGENTS[4]["role"], rid, _now(),
                    {"domain": domain, "claims_reviewed": len(upstream)},
                    tool_calls, decisions, sorted(set(sources)), reviewer_status="n/a",
                    tool_receipts=receipts)


def run_research_cell(domain: str = "tcell") -> dict:
    """Execute the five-agent cell over the real corpus and return a fully audited
    run: every agent's structured output + the reviewer-gated set of claims admitted
    to the ranking + a reproducibility ledger."""
    rid = _run_id(domain, "cell-v1")
    ledger = []

    def _log(agent: AgentRun) -> AgentRun:
        agent.ledger_entry = {"run_id": rid, "task_id": agent.task_id,
                              "agent": agent.name, "status": agent.status,
                              "claims": len(agent.claims), "at": agent.timestamp}
        ledger.append(agent.ledger_entry)
        return agent

    analysts = [_log(_data_analysis_agent(domain, rid)),
                _log(_literature_agent(domain, rid)),
                _log(_biology_agent(domain, rid))]
    upstream = [c for a in analysts for c in a.claims]

    integrity = _log(_integrity_agent(domain, rid, upstream))
    reviewer = _log(_reviewer_agent(domain, rid, upstream, integrity))

    # THE GATE: a claim is PRIMARY ranking support only if the Reviewer APPROVED it.
    approved_ids = {d["id"] for d in reviewer.claims if d["text"].startswith("APPROVE")}
    corroboration_ids = {d["id"] for d in reviewer.claims if d["text"].startswith("CORROBORATION")}
    id_to_claim = {c["id"]: c for c in upstream}

    def _pack(ids):
        return sorted(({"id": cid, "text": id_to_claim[cid]["text"],
                        "source_id": id_to_claim[cid]["source_id"]}
                       for cid in ids if cid in id_to_claim), key=lambda x: x["id"])

    admitted = _pack(approved_ids)
    corroboration = _pack(corroboration_ids)
    rejected = sorted(({"id": d["id"], "reason": d["text"]}
                       for d in reviewer.claims if d["text"].startswith("REJECT")),
                      key=lambda x: x["id"])

    # set each analyst's reviewer_status from the reviewer's decisions
    for a in analysts:
        a_ids = {c["id"] for c in a.claims}
        a.reviewer_status = ("approved" if (a_ids & approved_ids)
                             else "corroboration" if (a_ids & corroboration_ids)
                             else "rejected")

    agents = analysts + [integrity, reviewer]
    return {
        "domain": domain,
        "run_id": rid,
        "generated_at": _now(),
        "agents": [a.to_dict() for a in agents],
        "admitted_to_ranking": admitted,
        "corroboration": corroboration,
        "rejected": rejected,
        "ledger": ledger,
        "gate_note": ("No agent output is primary ranking support until the Reviewer "
                      "Agent approves it. Peer-reviewed evidence → approved; preprint "
                      "measured data → corroboration (provisional); no-source / "
                      "unsupported / synthetic → rejected."),
    }
