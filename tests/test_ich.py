"""
Tests for the third domain — intracerebral / brain hemorrhage ("NeuroHem").
Runs offline against the pinned real fixtures. The claims under test:

  1. the foundation is a REAL, Crossref-verified RETRACTED paper (MMP-9);
  2. the target is the real MMP-9 protein, not another domain's target;
  3. the graph is reproducible and cites only real (non-synthetic) DOIs;
  4. decide('ich') reasons about MMP-9 and NEVER leaks GBM/insulin text
     (the "silent GBM fallback" fabrication trap the resolver could hit);
  5. the Scientific Safety Boundary REFUSES the dangerous parts of a
     brain-hemorrhage brief — CT detection, brain-waves, treatment.
"""
import os
os.environ["KEYSTONE_OFFLINE"] = "1"

import json  # noqa: E402

from keystone.data_ich import build_ich_graph  # noqa: E402
from keystone.decision_engine import decide  # noqa: E402
from keystone import ich_spec as SPEC  # noqa: E402
from keystone.cv_lab import REFUSED, modality_catalogue  # noqa: E402


def test_foundation_is_real_and_retracted():
    g = build_ich_graph()
    f = g.nodes["N_foundation"]
    assert f.retracted is True                       # real Crossref retraction
    assert f.doubt.point == 1.0                      # a retracted keystone is fully doubted
    assert SPEC.FOUNDATION["doi"] in f.source


def test_target_is_mmp9_not_another_domain():
    g = build_ich_graph()
    t = g.nodes["N_target"]
    assert "MMP9" in t.text or "Matrix metalloproteinase-9" in t.text
    assert "P14780" in t.source                      # the real UniProt id


def test_graph_reproducible_and_only_real_dois():
    a = build_ich_graph()
    b = build_ich_graph()
    assert a.snapshot_hash() == b.snapshot_hash()    # same fixtures -> same hash
    for n in a.nodes.values():
        assert not n.source.startswith("10.9999")    # no synthetic DOI
        assert "gbm-" not in n.source and "insulin-" not in n.source


def test_decide_ich_reasons_about_mmp9_and_never_leaks_gbm():
    out = decide(domain="ich")
    d = out[0] if isinstance(out, tuple) else out
    blob = json.dumps(d).lower()
    assert "mmp9" in blob or "mmp-9" in blob or "hemorrhage" in blob
    # the resolver must NOT silently serve the GBM graph under an 'ich' label
    assert "cathepsin" not in blob and "glioblastoma" not in blob
    h1 = next((h for h in d.get("competing_hypotheses", []) if h.get("id") == "H1"), {})
    assert "MMP9" in h1.get("statement", "")


def test_safety_boundary_refuses_detection_brainwaves_and_treatment():
    for key in ("ct_hemorrhage_detection", "eeg_brainwave", "treatment_recommendation"):
        assert key in REFUSED
    cat = {c["modality"]: c for c in modality_catalogue()}
    assert cat["ct_hemorrhage_detection"]["status"] == "refused"
    assert "diagnosis" in cat["ct_hemorrhage_detection"]["detail"]
    assert "no patient data" in cat["eeg_brainwave"]["detail"]
    assert "never treatment" in cat["treatment_recommendation"]["detail"]
