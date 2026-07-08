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
