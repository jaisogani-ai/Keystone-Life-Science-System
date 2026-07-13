// Keystone reusable UI components (framework-free ES modules — no build step, so
// a lab can run the app straight from disk). Pure functions returning HTML; the
// visual output matches the approved design exactly.

export const esc = s => (s == null ? '' : String(s))
  .replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));

const KB = { computed: 'c', estimate: 'e', qualitative: 'q' };

// a metric value with its honesty badge (computed / estimate / qualitative)
export const metric = m =>
  `${esc(m.value)}<sup class="${KB[m.kind]}" title="${esc(m.kind)}: ${esc(m.basis)}">${KB[m.kind]}</sup>`;

export const pill = (text, cls = '') => `<span class="pill ${cls}">${esc(text)}</span>`;

// the linear reasoning workflow strip
export const flowStrip = workflow => `<div class="flow stagger">` + workflow.map((w, i) => {
  const hot = /Competing|information gain|ranking|Contradiction|gap/i.test(w.stage);
  return `<span class="fl ${hot ? 'k' : ''}" style="--i:${i}">${esc(w.stage)} <b>${esc(w.value)}</b></span>`;
}).join('') + `</div>`;

// one competing-hypothesis card for the decision board
export const hypCard = (s, deb, idx = 0) => {
  const pct = Math.round(s.priority_score.value * 100);
  const grounds = Array.isArray(s.mechanism_path) ? s.mechanism_path.join(',') : '';
  return `<div class="hyp reveal sync ${s.rank === 1 ? 'top' : ''}" data-hyp="${esc(s.id)}" data-grounds="${esc(grounds)}" style="animation-delay:${idx * 45}ms">
    <div class="hrow"><span class="rank">#${s.rank}</span> <b>${esc(s.id)}</b>
      <span class="kind">${esc(s.kind)}</span>
      <span class="pri">priority ${s.priority_score.value}<span class="bar"><i style="width:${pct}%"></i></span></span></div>
    <div class="stmt">${esc(s.statement)}</div>
    <div class="mgrid">
      <div class="m"><span class="k">EIG</span> ${metric(s.information_gain)}</div>
      <div class="m"><span class="k">Evidence</span> ${metric(s.evidence_strength)}</div>
      <div class="m"><span class="k">Contradiction</span> ${metric(s.contradiction_score)}</div>
      <div class="m"><span class="k">Novelty</span> ${metric(s.novelty)}</div>
      <div class="m"><span class="k">Risk</span> ${pill(s.risk.value, s.risk.value)}</div>
      <div class="m"><span class="k">Difficulty</span> ${metric(s.validation_difficulty)}</div>
      <div class="m"><span class="k">Cost</span> $${s.cost_usd.value.toLocaleString()}<sup class="e" title="${esc(s.cost_usd.basis)}">e</sup></div>
      <div class="m"><span class="k">Time</span> ${s.duration_weeks.value}wk<sup class="e">e</sup></div>
      <div class="m"><span class="k">Reviewer</span> ${metric(s.reviewer_confidence)}</div>
    </div>
    <div class="why">Why #${s.rank}: ${esc((s.why || []).join(', '))}</div>
    ${deb ? debateBlock(deb) : ''}
  </div>`;
};

export const debateBlock = deb => {
  const R = r => `<div><h4>${esc(r.role)}</h4><ul>${r.case.map(c => `<li>${esc(c)}</li>`).join('')}</ul>
    <div style="color:var(--dim);font-size:11px">${esc(r.claim)}</div></div>`;
  return `<details class="exp"><summary>Scientific debate &amp; resolution</summary>
    <div class="debate">${R(deb.proponent)}${R(deb.skeptic)}${R(deb.reviewer)}</div>
    <div class="res"><b>Resolution (${esc(deb.resolution.verdict)}):</b> ${esc(deb.resolution.reason)}
      <div style="color:var(--dim);font-size:11px;margin-top:3px">${esc(deb.resolution.method)}</div></div>
  </details>`;
};

// one orchestration step — the SAME structured scientific artifact every seat
// exposes (Evidence · Datasets · Publications · Contradictions · Assumptions ·
// Remaining uncertainty · Confidence · Proposed experiment · Failure modes ·
// Expected information gain · Provenance). Reused for the static trace and the
// live stream. The Reviewer's confidence drop (before -> after) and the Principal
// Investigator's synthesis are surfaced as their own visible beats.
export const traceStep = (s, i = 0) => {
  const isRev = /Reviewer/i.test(s.actor);
  const isPI = /Principal Investigator/i.test(s.actor);
  const dg = isRev && s.confidence_delta != null && s.confidence_delta < 0;
  const chip = (label, arr) => (arr && arr.length)
    ? `<div class="tmeta"><span class="k">${label}:</span> ${arr.slice(0, 3).map(esc).join(' · ')}</div>` : '';
  const line = (label, val) => (val != null && val !== '')
    ? `<div class="tmeta"><span class="k">${label}:</span> ${esc(val)}</div>` : '';
  let delta = '';
  if (s.confidence_before != null && s.confidence_after != null) {
    const d = s.confidence_delta;
    const dir = d < 0 ? 'down' : (d > 0 ? 'up' : 'flat');
    delta = `<div class="cdelta ${dir}">confidence <b>${s.confidence_before}</b> → `
      + `<b>${s.confidence_after}</b> <span class="dd">${d > 0 ? '+' : ''}${d}</span></div>`;
  }
  return `<div class="tstep reveal ${dg ? 'downgrade' : ''} ${isPI ? 'pi' : ''}" style="--i:${i};animation-delay:${i * 40}ms">
    <span class="tnum">${s.step}</span>
    <div class="tbody">
      <div><b>${esc(s.actor)}</b> <span class="pill ${s.actor_type === 'agent' ? 'agent' : 'tool'}">${esc(s.actor_type)}</span>
        ${s.confidence != null ? `<span class="pill ${dg ? 'high' : ''}">conf ${s.confidence}</span>` : ''}
        ${s.information_gain != null ? `<span class="pill">EIG ${s.information_gain}</span>` : ''}</div>
      <div class="trole">${esc(s.role)}</div>
      <div class="tout">→ ${esc(s.output)}</div>
      ${delta}
      ${(s.evidence && s.evidence.length) ? `<div class="tev">evidence: ${s.evidence.slice(0, 4).map(esc).join(' · ')}</div>` : ''}
      ${chip('publications', s.supporting_publications)}${chip('datasets', s.source_datasets)}
      ${chip('contradictions', s.contradictions)}${chip('assumptions', s.assumptions)}
      ${line('remaining uncertainty', s.remaining_uncertainty)}
      ${line('proposed experiment', s.proposed_experiment)}
      ${isRev ? line('challenges', s.challenged_assumption) : ''}
      ${chip('failure modes', s.failure_modes)}${chip('provenance', s.provenance)}
      ${chip('artifacts', s.artifacts)}
    </div>
  </div>`;
};

// the node inspector — DOI-linkified source + doubt interval + integrity flags.
// ONE definition, reused by the living graph and every page (replaces the
// per-page wireGraph node boxes that had drifted).
// Provenance drawer: the claim's real name, the FOUR independent axes
// (source-record-verified is NOT "true"/"supports"), and the exact claim->source
// linkage. "not available" is shown honestly; nothing is fabricated.
export const nodeInspect = (n) => {
  if (!n) return '';
  const c = n.claim || {}, lk = c.linkage || {};
  const di = n.doubt_interval ? ` [${n.doubt_interval.join(', ')}]` : '';
  const doiLink = (s) => /^(10\.|doi:|https?:)/i.test(s || '')
    ? `<a href="https://doi.org/${esc((s || '').replace(/^doi:/i, ''))}" target="_blank">${esc(s)}</a>`
    : esc(s || 'not available');
  const na = v => (v && v !== 'not available') ? esc(v) : '<span class="ks-dim">not available</span>';
  const row = (k, v) => `<div class="tmeta"><span class="k">${k}:</span> ${v}</div>`;
  const sv = c.source_record_verified;
  const svPill = (sv === undefined) ? ''
    : `<span class="pill ${sv ? 'low' : 'medium'}" title="the identifier resolves — NOT that it supports the claim">source record ${sv ? 'verified' : 'unverified'}</span>`;
  const ctPill = c.claim_type ? `<span class="pill">claim: ${esc(c.claim_type)}</span>` : '';
  const isCol = { retracted: 'high', concern: 'medium', unverified: 'medium', normal: 'low' }[c.integrity_state] || '';
  const isPill = c.integrity_state ? `<span class="pill ${isCol}">integrity: ${esc(c.integrity_state)}</span>` : '';
  return `<b>${esc(n.text || n.id)}</b> <span class="pill">${esc(n.type)}</span>
    <div style="margin:6px 0 8px;display:flex;gap:5px;flex-wrap:wrap">${svPill}${ctPill}${isPill}</div>
    ${row('source id', doiLink(lk.source_id || n.source))}
    ${row('locator', na(lk.source_locator))}
    ${row('quote', na(lk.source_quote))}
    ${row('extraction', na(lk.extraction_method))}
    ${row('doc version', na(lk.source_document_version))}
    ${row('doubt', `${n.doubt}${di}${n.date ? ` · ${esc(n.date)}` : ''}`)}`;
};

// the "Why did Keystone reach this?" reasoning chain — ONE definition, projecting
// reasoning_panel.why_panel (replaces the three drifted per-page renderings).
export const whyPanel = (wp) => {
  if (!wp) return '';
  const ev = items => (items && items.length)
    ? `<ul>${items.map(e => `<li><b>${esc((e.text || e.id).slice(0, 96))}</b> <span class="ks-dim">(doubt ${e.doubt})</span></li>`).join('')}</ul>`
    : `<div class="ks-dim">none recorded</div>`;
  const r = wp.reviewer_objection || {};
  const ne = wp.suggested_next_experiment || {};
  const ci = (wp.confidence && wp.confidence.interval) ? wp.confidence.interval.join(', ') : '';
  return `<div class="why-h">${esc(wp.hypothesis)}</div>
    <div class="why-grid">
      <div><div class="lbl green">Supporting evidence</div>${ev(wp.supporting_evidence)}</div>
      <div><div class="lbl amber">Contradicting evidence</div>${ev(wp.contradicting_evidence)}</div>
    </div>
    <div class="why-row"><span class="k">Confidence</span>${wp.confidence.point} [${ci}]</div>
    <div class="why-row red"><span class="k">Reviewer (${esc(r.verdict)})</span>${esc(r.weakness)} → adj ${r.adjusted_confidence}</div>
    <div class="why-row"><span class="k">Remaining uncertainty</span>${esc(wp.remaining_uncertainty)}</div>
    <div class="why-row"><span class="k">Failure modes</span></div>
    <ul>${(wp.failure_modes || []).map(f => `<li>${esc(f)}</li>`).join('')}</ul>
    <div class="why-row green"><span class="k">How to disprove it</span>${esc(ne.kill_condition)} · n/arm ${ne.required_n_per_arm}</div>`;
};

export const agentTrace = trace =>
  `<div class="trace">` + trace.map((s, i) => traceStep(s, i)).join('') + `</div>`;
