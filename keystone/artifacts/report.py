"""
keystone.artifacts.report
========================
Publication-ready artifact generation. Composes the existing dataclasses (Ledger,
Hypothesis, ReviewResult) + provenance into a formatted, print-ready research
report — a real composition, no new computation. Every citation is a real
identifier from the graph; the reproducibility hash and the independent Reviewer
critique are included so the document is auditable, not promotional.
"""
from __future__ import annotations

import html
from datetime import date

from keystone.core import EvidenceGraph
from keystone.deterministic.provenance import build_provenance
from keystone.artifacts.render import evidence_graph_svg, timeline_svg


def _esc(s) -> str:
    return html.escape(str(s))


def research_report_html(question: str, graph: EvidenceGraph, ledger, hyp,
                         review) -> str:
    prov = build_provenance(graph, ledger, hyp)
    ep = hyp.validation_experiment
    support = [(nid, graph.nodes[nid]) for nid in hyp.supporting_evidence
               if nid in graph.nodes]
    contra = [(nid, graph.nodes[nid]) for nid in hyp.contradicting_evidence
              if nid in graph.nodes]

    def cite(n):
        s = n.source
        link = (f'<a href="https://doi.org/{_esc(s)}">{_esc(s)}</a>'
                if s.startswith("10.") else _esc(s))
        return f"{_esc(n.text[:100])} ({link})"

    refs = "".join(
        f"<li>{cite(n)} — doubt {n.doubt.point:.2f}</li>"
        for n in sorted(graph.nodes.values(), key=lambda x: x.id)
        if n.source and n.source != "unresolved")

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Keystone Research Report — {_esc(ledger.graph_hash)}</title>
<style>
  body{{font-family:Georgia,'Times New Roman',serif;max-width:820px;margin:40px auto;
    padding:0 24px;color:#1a1a1a;line-height:1.6}}
  h1{{font-size:24px;margin-bottom:4px}} h2{{font-size:16px;border-bottom:1px solid #ccc;
    padding-bottom:4px;margin-top:28px}}
  .meta{{color:#666;font-size:13px}} .tag{{background:#eef;border:1px solid #cce;
    border-radius:4px;padding:1px 6px;font-size:11px;font-family:monospace}}
  .critique{{background:#fff8f0;border-left:3px solid #d68000;padding:10px 14px}}
  code{{background:#f4f4f4;padding:1px 5px;border-radius:3px}}
  ol,ul{{font-size:14px}} .appendix{{font-size:12.5px;color:#333}}
  @media print{{a{{color:#000;text-decoration:none}}}}
</style></head><body>
<h1>{_esc(question)}</h1>
<div class="meta">Keystone Evidence Ledger · reasoner <span class="tag">{_esc(ledger.reasoner_version)}</span>
 · reproducibility hash <span class="tag">{_esc(ledger.graph_hash)}</span> · {date.today().isoformat()}</div>

<h2>Hypothesis</h2>
<p>{_esc(hyp.statement)}</p>
<p class="meta">Confidence {hyp.confidence.point} [{hyp.confidence.low}, {hyp.confidence.high}]
 · expected outcome: {_esc(hyp.expected_outcome)}</p>

<h2>Supporting evidence</h2>
<ul>{''.join(f'<li>{cite(n)}</li>' for _, n in support) or '<li>none recorded</li>'}</ul>
<h2>Contradicting evidence</h2>
<ul>{''.join(f'<li>{cite(n)}</li>' for _, n in contra) or '<li>none recorded</li>'}</ul>

<h2>Proposed validation experiment (methods)</h2>
<p><b>Perturbation:</b> {_esc(ep.perturbation)}<br>
<b>System:</b> {_esc(ep.system)}<br>
<b>Controls:</b> +{_esc(ep.positive_controls)} / -{_esc(ep.negative_controls)}<br>
<b>Readout:</b> {_esc(ep.readout)}<br>
<b>Kill-condition (falsifies the hypothesis):</b> {_esc(ep.kill_condition)}<br>
<b>Sample size:</b> n/arm = {ep.required_n_per_arm} — {_esc(ep.stats_notes)}<br>
<b>Effect size source:</b> {_esc(ep.effect_size_source)}</p>

<h2>Figures</h2>
<figure style="margin:0 0 18px">
  {evidence_graph_svg(graph, width=760, height=460)}
  <figcaption style="font-size:12px;color:#555;margin-top:4px"><b>Figure 1.</b>
   Evidence graph — nodes coloured by inherited doubt, edges weighted by
   load-bearing classification; the retracted foundation is ringed.
   Source: {_esc(', '.join(prov['coverage']['source_kinds']))} connectors;
   reproduces from hash <code>{_esc(ledger.graph_hash)}</code>.</figcaption>
</figure>
<figure style="margin:0 0 8px">
  {timeline_svg(ledger.timeline, width=760, height=220)}
  <figcaption style="font-size:12px;color:#555;margin-top:4px"><b>Figure 2.</b>
   Research timeline — discovery to retraction to downstream citation, from the
   real publication and retraction dates in the evidence graph.</figcaption>
</figure>

<h2>Independent reviewer critique</h2>
<div class="critique"><b>{_esc(review.verdict.value).upper()}</b> — {_esc(review.weakness)}<br>
adjusted confidence {review.adjusted_confidence.point}</div>

<h2>Remaining uncertainty &amp; failure modes</h2>
<p>{_esc(hyp.uncertainty_notes)}</p>
<ul>{''.join(f'<li>{_esc(f)}</li>' for f in hyp.failure_modes)}</ul>

<h2>Provenance appendix</h2>
<p class="appendix">{prov['coverage']['nodes_resolved']} of {prov['coverage']['nodes_total']}
 evidence nodes resolved to a real source
 ({', '.join(_esc(k) for k in prov['coverage']['source_kinds'])});
 {prov['coverage']['nodes_unresolved']} unresolved (shown as such, never fabricated).
 Every value in this report originates from the cited sources below or is a
 deterministic computation over them.</p>
<ol class="appendix">{refs}</ol>
<p class="meta">Re-running Keystone on this evidence reproduces hash
 <code>{_esc(ledger.graph_hash)}</code> identically.</p>
</body></html>"""
