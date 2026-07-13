// The 8-stage workflow spine, rendered under the header on every page.
// Reads the current stage from <body data-stage="…"> and marks the stages
// before it "done", the current one "now", and the rest neutral.
//
// Every capability in Keystone belongs to one of these eight stages; the
// spine is the visual reminder that this is one scientific workflow, not
// a dashboard of independent products.

export const STAGES = [
  { id: "evidence",        label: "Evidence" },
  { id: "provenance",      label: "Provenance" },
  { id: "integrity",       label: "Integrity" },
  { id: "reasoning",       label: "Reasoning" },
  { id: "hypothesis",      label: "Hypothesis" },
  { id: "experiment",      label: "Experiment" },
  { id: "publication",     label: "Publication" },
  { id: "reproducibility", label: "Reproducibility" },
];

export function mountSpine(host, current) {
  if (!host) return;
  const now = (current || document.body.dataset.stage || "").toLowerCase();
  const idx = STAGES.findIndex(s => s.id === now);
  host.innerHTML = STAGES.map((s, i) => {
    const cls = idx < 0 ? "" : (i < idx ? "done" : (i === idx ? "now" : ""));
    const sep = i < STAGES.length - 1 ? '<span class="sep">›</span>' : "";
    return `<span class="pb ${cls}" data-stage="${s.id}">${s.label}</span>${sep}`;
  }).join("");
}

// Auto-mount on any page that carries <div class="wf-spine" id="spine"></div>.
// The page can override by calling mountSpine(el, stageId) explicitly.
if (typeof document !== "undefined") {
  document.addEventListener("DOMContentLoaded", () => {
    const el = document.getElementById("spine");
    if (el) mountSpine(el);
  });
}
