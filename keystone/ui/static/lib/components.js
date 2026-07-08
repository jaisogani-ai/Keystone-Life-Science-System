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
  return `<div class="hyp reveal ${s.rank === 1 ? 'top' : ''}" style="animation-delay:${idx * 45}ms">
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

// one orchestration step — the same structured schema every seat exposes
// (Evidence, Confidence, Sources, Contradictions, Assumptions, Failure modes,
// Artifacts). Reused for the static trace and the live stream. Reviewer steps
// that carry a downgrade are highlighted (the winning beat).
export const traceStep = (s, i = 0) => {
  const isRev = /Reviewer/i.test(s.actor);
  const dg = isRev && /downgraded|rejected/i.test(s.output);
  const chip = (label, arr) => (arr && arr.length)
    ? `<div class="tmeta"><span class="k">${label}:</span> ${arr.slice(0, 3).map(esc).join(' · ')}</div>` : '';
  return `<div class="tstep reveal ${dg ? 'downgrade' : ''}" style="--i:${i};animation-delay:${i * 40}ms">
    <span class="tnum">${s.step}</span>
    <div class="tbody">
      <div><b>${esc(s.actor)}</b> <span class="pill ${s.actor_type === 'agent' ? 'agent' : 'tool'}">${esc(s.actor_type)}</span>
        ${s.confidence != null ? `<span class="pill ${dg ? 'high' : ''}">conf ${s.confidence}</span>` : ''}</div>
      <div class="trole">${esc(s.role)}</div>
      <div class="tout">→ ${esc(s.output)}</div>
      ${(s.evidence && s.evidence.length) ? `<div class="tev">provenance: ${s.evidence.slice(0, 4).map(esc).join(' · ')}</div>` : ''}
      ${chip('sources', s.sources)}${chip('contradictions', s.contradictions)}
      ${chip('assumptions', s.assumptions)}${chip('failure modes', s.failure_modes)}
      ${chip('artifacts', s.artifacts)}
    </div>
  </div>`;
};

export const agentTrace = trace =>
  `<div class="trace">` + trace.map((s, i) => traceStep(s, i)).join('') + `</div>`;
