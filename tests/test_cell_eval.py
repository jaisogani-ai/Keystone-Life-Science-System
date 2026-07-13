"""
Research Cell scientific-correctness eval — the measured scoreboard + its integrity.

The point of an eval is that it can FAIL. These tests prove (a) the real system passes
every case, and (b) the judges have TEETH — when an invariant is deliberately broken,
the corresponding case flips to FAIL and the scoreboard reports it honestly.
"""
import keystone.agents.cell_eval as ce
from keystone.agents.cell_eval import run_cell_eval


def test_all_scientific_correctness_cases_pass_on_the_real_system():
    e = run_cell_eval("tcell")
    assert e["n"] == 10
    failed = [c["id"] for c in e["cases"] if not c["passed"]]
    assert e["all_pass"], f"failing cases: {failed}"
    assert e["pass_rate"] == 1.0
    # every case carries real evidence, not a bare boolean
    assert all(c["evidence"] for c in e["cases"])


def test_the_judges_have_teeth_break_an_invariant_and_a_case_fails(monkeypatch):
    """Canary: if the preprint were admitted as PRIMARY support (the exact thing the
    reviewer gate must prevent), the eval MUST report failure — proving no case is
    hardcoded to pass."""
    real = ce.run_research_cell

    def broken(domain="tcell"):
        r = dict(real(domain))
        # inject the not-peer-reviewed preprint as primary ranking support
        r["admitted_to_ranking"] = list(r["admitted_to_ranking"]) + [
            {"id": "lit:FBXO32", "text": "x", "source_id": "PREPRINT"}]
        return r

    monkeypatch.setattr(ce, "run_research_cell", broken)
    e = run_cell_eval("tcell")
    assert not e["all_pass"]
    failed = {c["id"] for c in e["cases"] if not c["passed"]}
    # the preprint-as-primary breaks BOTH the preprint gate and the reviewer gate
    assert "preprint-not-primary" in failed
    assert "reviewer-gate" in failed


def test_a_secret_leak_would_be_caught(monkeypatch):
    """Canary #2: if a key ever leaked into the agent output, no-secret-leak must fail."""
    real = ce.run_research_cell

    def leaky(domain="tcell"):
        r = dict(real(domain))
        r["debug"] = "ANTHROPIC_API_KEY=sk-ant-LEAKED"     # simulate a leak
        return r

    monkeypatch.setattr(ce, "run_research_cell", leaky)
    e = run_cell_eval("tcell")
    failed = {c["id"] for c in e["cases"] if not c["passed"]}
    assert "no-secret-leak" in failed
