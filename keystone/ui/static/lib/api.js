// Keystone data layer — the single place the UI talks to the engine.
// Every payload is the engine's own output; the UI computes nothing.

const j = async (url) => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json();
};

export const getDecision = domain => j('/api/decision?domain=' + encodeURIComponent(domain));
export const getPipeline = domain => j('/api/pipeline?domain=' + encodeURIComponent(domain));
export const reportUrl = domain => '/api/report?domain=' + encodeURIComponent(domain);

// Live reasoning stream — the agents' steps arrive as they complete.
export const streamDecision = (domain, onStep, onDone, onError) => {
  const es = new EventSource('/api/decision/stream?domain=' + encodeURIComponent(domain));
  es.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.type === 'step') onStep(m.step);
    else if (m.type === 'done') { onDone(m.data); es.close(); }
  };
  es.onerror = () => { es.close(); if (onError) onError(); };
  return es;
};
