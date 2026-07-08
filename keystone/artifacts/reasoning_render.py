"""
keystone.artifacts.reasoning_render
==================================
Visual renderers for the reasoning-transparency artifacts (why-panel and
future-experiments tree). Deterministic; pure functions of their inputs.
"""

from __future__ import annotations

import html


def why_panel_html(panel: dict) -> str:
    def ev_rows(items):
        if not items:
            return '<li style="color:#8d99ae">none recorded</li>'
        return "".join(
            f'<li><b>{html.escape(e["id"])}</b> '
            f'<span style="color:#8d99ae">(doubt {e["doubt"]})</span> — '
            f'{html.escape(str(e["text"])[:90])}</li>' for e in items)

    ci = panel["confidence"]["interval"]
    obj = panel["reviewer_objection"]
    exp = panel["suggested_next_experiment"]
    return f"""<div style="font-family:system-ui,sans-serif;max-width:760px;
color:#e6e6e6;background:#0f1117;padding:22px;border-radius:10px;line-height:1.5">
  <h2 style="margin:0 0 4px">Why did Keystone reach this conclusion?</h2>
  <p style="color:#cfcfcf;margin:0 0 16px"><i>{html.escape(panel["hypothesis"])}</i></p>

  <h4 style="color:#4cc9f0;margin:12px 0 4px">Supporting evidence</h4>
  <ul style="margin:0">{ev_rows(panel["supporting_evidence"])}</ul>

  <h4 style="color:#ffd166;margin:14px 0 4px">Contradicting evidence</h4>
  <ul style="margin:0">{ev_rows(panel["contradicting_evidence"])}</ul>

  <h4 style="color:#e6e6e6;margin:14px 0 4px">Confidence</h4>
  <p style="margin:0">{panel["confidence"]["point"]} &nbsp;
     <span style="color:#8d99ae">interval [{ci[0]}, {ci[1]}]</span></p>

  <h4 style="color:#ff5d5d;margin:14px 0 4px">Reviewer objection (independent)</h4>
  <p style="margin:0"><b>{html.escape(obj["verdict"]).upper()}</b> —
     {html.escape(obj["weakness"])}<br>
     <span style="color:#8d99ae">adjusted confidence
     {obj["adjusted_confidence"]}</span></p>

  <h4 style="color:#e6e6e6;margin:14px 0 4px">Remaining uncertainty</h4>
  <p style="margin:0">{html.escape(panel["remaining_uncertainty"])}</p>

  <h4 style="color:#e6e6e6;margin:14px 0 4px">Failure modes</h4>
  <ul style="margin:0">{"".join(f"<li>{html.escape(f)}</li>"
                                 for f in panel["failure_modes"])}</ul>

  <h4 style="color:#06d6a0;margin:14px 0 4px">Suggested next experiment</h4>
  <p style="margin:0">{html.escape(exp["perturbation"])}<br>
     <span style="color:#8d99ae">kill condition: {html.escape(exp["kill_condition"])}
     &nbsp;·&nbsp; n/arm: {exp["required_n_per_arm"]}</span></p>
</div>"""


def future_experiments_svg(branches: list[dict]) -> str:
    """A simple grounded decision tree render."""
    by_id = {b["node_id"]: b for b in branches}
    # fixed layout for the canonical 4-node tree
    pos = {"E0": (400, 60), "E1_pos": (240, 200), "E1_neg": (600, 200),
           "E2_pos": (240, 340)}
    parts = ['<svg viewBox="0 0 800 420" xmlns="http://www.w3.org/2000/svg" '
             'font-family="system-ui,sans-serif">',
             '<rect width="800" height="420" fill="#0f1117"/>',
             '<text x="400" y="30" fill="#e6e6e6" font-size="17" '
             'text-anchor="middle">Future Experiments — decision tree</text>']

    def edge(a, b, label, col):
        if a not in pos or b not in pos:
            return ""
        x1, y1 = pos[a]; x2, y2 = pos[b]
        return (f'<line x1="{x1}" y1="{y1+26}" x2="{x2}" y2="{y2-26}" '
                f'stroke="{col}" stroke-width="2"/>'
                f'<text x="{(x1+x2)//2}" y="{(y1+y2)//2}" fill="{col}" '
                f'font-size="11" text-anchor="middle">{label}</text>')

    for b in branches:
        if b["on_positive"]:
            parts.append(edge(b["node_id"], b["on_positive"], "positive", "#06d6a0"))
        if b["on_negative"]:
            parts.append(edge(b["node_id"], b["on_negative"], "negative", "#ff5d5d"))

    for nid, (x, y) in pos.items():
        b = by_id.get(nid, {})
        col = "#4cc9f0" if nid == "E0" else ("#ff5d5d" if "neg" in nid else "#06d6a0")
        parts.append(f'<rect x="{x-90}" y="{y-26}" width="180" height="52" rx="8" '
                     f'fill="#1a1d27" stroke="{col}" stroke-width="1.5"/>')
        desc = html.escape((b.get("description", nid))[:44])
        parts.append(f'<text x="{x}" y="{y-4}" fill="#e6e6e6" font-size="10" '
                     f'text-anchor="middle">{nid}</text>')
        parts.append(f'<text x="{x}" y="{y+12}" fill="#bfbfbf" font-size="8.5" '
                     f'text-anchor="middle">{desc}</text>')
    parts.append('</svg>')
    return "\n".join(parts)
