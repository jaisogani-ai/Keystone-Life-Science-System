"""
Agent Skill tests. The Skill package (`skills/keystone-workbench/`) is what makes
Keystone usable inside Claude Desktop / Claude Code without opening any app — a
scientist asks Claude "check my references" and Keystone answers via MCP. These
tests guard the Skill's shape: valid frontmatter, every MCP tool documented, the
discipline rules present, and the workflow spine reference on disk.

Skills are text-only; no execution here — just structural validation so regressions
in the Skill package fail loudly rather than shipping a Skill Claude can't parse.
"""
from __future__ import annotations

import re
from pathlib import Path

_SKILL_DIR = Path(__file__).parent.parent / "skills" / "keystone-workbench"
_SKILL_MD = _SKILL_DIR / "SKILL.md"
_SPINE_MD = _SKILL_DIR / "references" / "discovery-spine.md"

# Every MCP tool that Keystone exposes must be listed in the Skill so Claude
# knows when to reach for it. Keep this list in sync with keystone.mcp_server.
_EXPECTED_TOOLS = {
    "check_reference_integrity", "next_experiment", "competing_hypotheses",
    "classify_load_bearing", "evidence_summary", "search_clinical_trials",
    "evidence_graph", "validation_metrics", "publication_report",
}


def _read_skill() -> str:
    assert _SKILL_MD.exists(), "SKILL.md missing"
    return _SKILL_MD.read_text()


def _frontmatter(text: str) -> dict:
    """Cheap YAML frontmatter parse — no PyYAML dependency. Handles top-level
    key: value pairs, list items, and folded scalars introduced by ``key: >``."""
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert m, "SKILL.md missing frontmatter"
    fm: dict = {}
    key = None
    folding = False
    for raw in m.group(1).splitlines():
        line = raw.rstrip()
        if re.match(r"^\w[\w-]*:", line):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            folding = (val == ">")
            fm[key] = "" if folding else val
        elif line.strip().startswith("- ") and key:      # list continuation
            fm.setdefault(f"{key}_list", []).append(line.strip()[2:])
        elif line.strip() and key and (folding or not fm[key]):  # folded body
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm


def test_skill_has_valid_frontmatter():
    fm = _frontmatter(_read_skill())
    assert fm.get("name") == "keystone-workbench"
    assert fm.get("description")                  # required for Claude to route
    assert len(fm["description"]) > 100           # not a stub
    assert fm.get("version")


def test_skill_documents_every_mcp_tool():
    text = _read_skill()
    missing = [t for t in _EXPECTED_TOOLS if t not in text]
    assert not missing, f"SKILL.md is missing tools: {missing}"


def test_skill_carries_the_discipline_rules():
    """The Skill must remind Claude of Keystone's no-fabrication discipline
    every time it's loaded — the credibility currency."""
    text = _read_skill()
    for phrase in ("Never fabricate", "AI proposes", "cite", "reproduc",
                   "load-bearing", "0.818", "never replaces"):
        assert phrase.lower() in text.lower(), f"SKILL.md missing '{phrase}'"


def test_workflow_spine_reference_exists_and_lists_all_stations():
    """The discovery spine reference doc is what Claude reads when it needs the
    full workflow context — must exist and cover every station."""
    assert _SPINE_MD.exists(), "discovery-spine.md missing"
    text = _SPINE_MD.read_text()
    for station in ("Question", "Evidence", "Integrity", "Decision",
                    "Experiment", "Publication", "Claude Desktop"):
        assert station in text, f"discovery-spine.md missing station: {station}"


def test_skill_when_to_invoke_is_concrete():
    """The 'When to invoke' section must give Claude phrase-level triggers, not
    vague guidance — otherwise Claude will not reach for the tools."""
    text = _read_skill()
    assert "When to invoke" in text
    # each of these is a real user-phrase the Skill teaches Claude to recognize
    # 'next-experiment' (hyphenated) and 'next experiment' both match Claude's
    # trigger routing; either form is acceptable.
    for trigger in ("retract", "next-experiment", "rigor", "clinical trials",
                    "load-bearing", "reference list"):
        assert trigger.lower() in text.lower()


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  ok  {name}")
    print("all skill tests passed")
