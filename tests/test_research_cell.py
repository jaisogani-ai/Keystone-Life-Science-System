"""
Research Cell — swarm-vs-cell control + the N>8 agent gate.

Locks the winning thesis as a *measured* property, and the honesty contract:
the swarm is the no-gate policy over the same real corpus (deterministic), the
gate removes retracted / not-peer-reviewed / unsupported claims, and more than
the cell ceiling of agents is blocked unless a benchmark proves it beats the cell.
"""
from keystone.deterministic.research_cell import (
    AGENT_ROSTER, MAX_CELL_AGENTS, admit_agent_count, swarm_vs_cell)


def test_roster_is_a_small_controlled_cell():
    assert len(AGENT_ROSTER) <= MAX_CELL_AGENTS
    names = {a["name"] for a in AGENT_ROSTER}
    assert "Integrity Agent" in names and "Reviewer Agent" in names


def test_cell_admits_zero_unverified_claims_swarm_does_not():
    b = swarm_vs_cell("tcell", swarm_n=300)
    sw, ce = b["swarm"], b["cell"]
    # the gate removes every bad claim
    assert ce["retracted_or_concern_cited"] == 0
    assert ce["not_peer_reviewed_cited"] == 0
    assert ce["unsupported_cited"] == 0
    assert ce["provenance_complete_pct"] == 100
    # the no-gate swarm admits the real contested claims (preprint + unsupported)
    assert (sw["not_peer_reviewed_cited"] + sw["unsupported_cited"]) >= 1
    assert sw["provenance_complete_pct"] < 100


def test_more_agents_cost_more_without_buying_accuracy():
    b = swarm_vs_cell("tcell", swarm_n=300)
    assert b["swarm"]["est_usd"] > b["cell"]["est_usd"]      # 300 > 8 agents
    assert b["cell"]["provenance_complete_pct"] >= b["swarm"]["provenance_complete_pct"]


def test_cell_is_robust_to_a_new_retraction_swarm_is_not():
    b = swarm_vs_cell("tcell", swarm_n=300)
    assert b["cell"]["robust_to_new_retraction"] is True
    assert b["swarm"]["robust_to_new_retraction"] is False


def test_gbm_swarm_cites_the_real_retracted_source():
    """On the GBM corpus (which contains a real retracted Oncogene paper) the
    no-gate swarm cites it; the cell excludes it."""
    b = swarm_vs_cell("gbm", swarm_n=50)
    assert b["swarm"]["retracted_or_concern_cited"] >= 1
    assert b["cell"]["retracted_or_concern_cited"] == 0


def test_agent_count_gate_blocks_more_than_the_cell_ceiling():
    assert admit_agent_count(MAX_CELL_AGENTS)["allowed"] is True
    blocked = admit_agent_count(300)
    assert blocked["allowed"] is False
    assert blocked["capped_to"] == MAX_CELL_AGENTS


def test_cost_is_labelled_estimate_never_a_measured_bill():
    b = swarm_vs_cell("tcell")
    assert "estimate" in b["cost_model"].lower()
