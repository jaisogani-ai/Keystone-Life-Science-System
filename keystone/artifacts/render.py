"""
keystone.artifacts.render
========================
Native artifact renderers (rule 5): the evidence graph, the research timeline,
and the 3D protein structure. Deterministic pure functions of their inputs — an
artifact is always tied to the reasoning that produced it, never decoration.
"""
from __future__ import annotations

import html
import math

from keystone.core import EvidenceGraph


def _doubt_color(doubt: float) -> str:
    """Green (trusted) -> amber -> red (doubted)."""
    doubt = max(0.0, min(1.0, doubt))
    if doubt < 0.5:
        r = int(0x2e + (0xff - 0x2e) * (doubt / 0.5))
        g = 0xb0 + int((0xd1 - 0xb0) * (doubt / 0.5))
        b = 0x66
    else:
        r = 0xff
        g = int(0xd1 * (1 - (doubt - 0.5) / 0.5))
        b = int(0x66 * (1 - (doubt - 0.5) / 0.5))
    return f"#{r:02x}{g:02x}{b:02x}"


def evidence_graph_svg(graph: EvidenceGraph, width: int = 820,
                       height: int = 520) -> str:
    """Doubt-coloured nodes, load-bearing-weighted edges, dashed contradictions,
    a red retraction ring. Deterministic circular layout ordered by node id."""
    ids = sorted(graph.nodes.keys())
    n = len(ids)
    cx, cy, radius = width / 2, height / 2, min(width, height) / 2 - 90
    pos = {}
    for i, nid in enumerate(ids):
        ang = -math.pi / 2 + 2 * math.pi * i / max(n, 1)
        pos[nid] = (cx + radius * math.cos(ang), cy + radius * math.sin(ang))

    parts = [f'<svg viewBox="0 0 {width} {height}" '
             'xmlns="http://www.w3.org/2000/svg" '
             'font-family="system-ui,sans-serif">',
             f'<rect width="{width}" height="{height}" fill="#0f1117"/>',
             f'<text x="{width/2}" y="26" fill="#e6e6e6" font-size="16" '
             'text-anchor="middle">Evidence graph — doubt-coloured, '
             'load-bearing-weighted</text>']

    for e in graph.edges:
        if e.src not in pos or e.dst not in pos:
            continue
        x1, y1 = pos[e.src]
        x2, y2 = pos[e.dst]
        w = 1 + 5 * e.load_bearing.point
        if e.edge_type.value == "contradicts":
            col, dash = "#ff5d5d", ' stroke-dasharray="6 4"'
        elif e.edge_type.value == "supports":
            col, dash = "#06d6a0", ""
        else:
            col, dash = "#5b6b8c", ""
        parts.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" '
                     f'y2="{y2:.0f}" stroke="{col}" stroke-width="{w:.1f}"{dash} '
                     f'opacity="0.8"/>')
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(f'<text x="{mx:.0f}" y="{my:.0f}" fill="#8d99ae" '
                     f'font-size="9" text-anchor="middle">'
                     f'{e.edge_type.value} {e.load_bearing.point:.2f}</text>')

    for nid in ids:
        x, y = pos[nid]
        node = graph.nodes[nid]
        col = _doubt_color(node.doubt.point)
        if node.retracted:
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="30" fill="none" '
                         f'stroke="#ff5d5d" stroke-width="3" stroke-dasharray="4 3"/>')
        if node.inexcusable:
            parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="34" fill="none" '
                         f'stroke="#ffd166" stroke-width="2"/>')
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="22" fill="{col}" '
                     f'stroke="#0f1117" stroke-width="2"/>')
        parts.append(f'<text x="{x:.0f}" y="{y+4:.0f}" fill="#0f1117" '
                     f'font-size="9" font-weight="bold" text-anchor="middle">'
                     f'{html.escape(nid.replace("N_", ""))}</text>')
        parts.append(f'<text x="{x:.0f}" y="{y+38:.0f}" fill="#cfcfcf" '
                     f'font-size="8.5" text-anchor="middle">'
                     f'doubt {node.doubt.point:.2f}</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def timeline_svg(timeline: list, width: int = 860, height: int = 240) -> str:
    """Horizontal research timeline; the retraction event is highlighted red."""
    if not timeline:
        return '<svg xmlns="http://www.w3.org/2000/svg"/>'
    dates = [e["date"] for e in timeline]
    lo, hi = min(dates), max(dates)
    def _x(d):
        if lo == hi:
            return width / 2
        return 60 + (width - 120) * (dates.index(d) / max(len(dates) - 1, 1))
    parts = [f'<svg viewBox="0 0 {width} {height}" '
             'xmlns="http://www.w3.org/2000/svg" '
             'font-family="system-ui,sans-serif">',
             f'<rect width="{width}" height="{height}" fill="#0f1117"/>',
             f'<text x="{width/2}" y="26" fill="#e6e6e6" font-size="16" '
             'text-anchor="middle">Research timeline</text>',
             f'<line x1="60" y1="{height/2}" x2="{width-60}" y2="{height/2}" '
             'stroke="#5b6b8c" stroke-width="2"/>']
    for i, ev in enumerate(timeline):
        x = _x(ev["date"])
        is_ret = ev["kind"] == "retraction"
        col = "#ff5d5d" if is_ret else "#4cc9f0"
        up = (i % 2 == 0)
        ty = height / 2 - 40 if up else height / 2 + 52
        parts.append(f'<circle cx="{x:.0f}" cy="{height/2}" r="6" fill="{col}"/>')
        parts.append(f'<text x="{x:.0f}" y="{ty}" fill="{col}" font-size="9.5" '
                     f'text-anchor="middle">{html.escape(ev["date"])}</text>')
        parts.append(f'<text x="{x:.0f}" y="{ty + (14 if up else 0)}" '
                     f'fill="#cfcfcf" font-size="8.5" text-anchor="middle">'
                     f'{html.escape(ev["label"][:26])}</text>')
    parts.append('</svg>')
    return "\n".join(parts)


def protein_viewer_html(pdb_id: str, gene: str = "target") -> str:
    """3Dmol.js viewer, rendered because a hypothesis points at this target.
    Loads the structure from RCSB by PDB id."""
    pid = html.escape(pdb_id)
    return f"""<div style="width:100%;height:420px;position:relative"
     id="ks-viewer" data-pdb="{pid}">
  <div style="position:absolute;top:8px;left:10px;z-index:2;color:#e6e6e6;
       font-family:system-ui,sans-serif;font-size:13px">
    3D structure — {html.escape(gene)} (PDB {pid})</div>
  <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
  <script>
    (function() {{
      var el = document.getElementById('ks-viewer');
      var v = $3Dmol.createViewer(el, {{backgroundColor: '#0f1117'}});
      $3Dmol.download('pdb:{pid}', v, {{}}, function() {{
        v.setStyle({{}}, {{cartoon: {{color: 'spectrum'}}}});
        v.zoomTo(); v.render();
      }});
    }})();
  </script>
</div>"""
