// Keystone living evidence graph (framework-free ES module).
//
// Turns the static, engine-rendered SVG into a living surface: selecting a node
// illuminates every connected entity, dims the rest, and traces DOUBT along
// load-bearing reliance edges to the claims that inherit it. It COMPUTES NOTHING
// scientific — it reads the doubt/load-bearing/relationships already produced by
// keystone.deterministic.propagation and projected via graph_to_dict. The browser
// only reveals what the engine decided.
//
// Reliance direction (matches core.incoming_dependencies): an edge src -> dst of
// type cites/depends_on means SRC relies on DST. So doubt in a node X flows to the
// nodes that depend on X: the srcs of edges whose dst === X.

import { esc, nodeInspect } from '/static/lib/components.js';

const RELIANCE = new Set(['cites', 'depends_on']);

// Build adjacency + a dependents map (who inherits doubt from whom) once.
function index(edges) {
  const neighbors = {};   // id -> Set(connected ids)  (undirected, for illuminate)
  const dependents = {};  // id -> [{id, load}]        (nodes relying ON this id)
  for (const e of edges) {
    (neighbors[e.src] = neighbors[e.src] || new Set()).add(e.dst);
    (neighbors[e.dst] = neighbors[e.dst] || new Set()).add(e.src);
    if (RELIANCE.has(e.edge_type)) {
      const load = e.load_bearing && e.load_bearing.point != null
        ? e.load_bearing.point : (e.load_bearing || 0);
      (dependents[e.dst] = dependents[e.dst] || []).push({ id: e.src, load });
    }
  }
  return { neighbors, dependents };
}

// Mount the living graph. `container` holds the engine SVG as innerHTML.
// data = { nodes: {id: nodeDetail}, edges: [{src,dst,edge_type,load_bearing}] }.
// opts.inspectEl (optional) is filled with the node inspector + propagation note.
// Returns an API: { select(id), highlightNodes(ids), clear() }.
export function mountGraph(container, data, opts = {}) {
  const nodes = data.nodes || {};
  const edges = data.edges || [];
  const { neighbors, dependents } = index(edges);
  const svg = container.querySelector('svg');
  container.classList.add('ks-graph');
  const inspect = opts.inspectEl || null;

  const nodeEls = () => container.querySelectorAll('.ks-node');
  const edgeEls = () => container.querySelectorAll('.ks-edge');

  function clear() {
    container.classList.remove('sel');
    nodeEls().forEach(el => el.classList.remove('on', 'sel-root'));
    edgeEls().forEach(el => el.classList.remove('on', 'prop'));
  }

  function illuminate(ids) {
    const set = new Set(ids);
    container.classList.add('sel');
    nodeEls().forEach(el => el.classList.toggle('on', set.has(el.dataset.node)));
    edgeEls().forEach(el => el.classList.toggle(
      'on', set.has(el.dataset.src) && set.has(el.dataset.dst)));
  }

  // highlight a hypothesis's grounding nodes (used to synchronize the decision
  // board with the graph — clicking a competing hypothesis lights its evidence).
  function highlightNodes(ids) {
    if (!ids || !ids.length) { clear(); return; }
    const keep = ids.filter(id => nodes[id] || neighbors[id]);
    illuminate(keep.length ? keep : ids);
    nodeEls().forEach(el => el.classList.toggle(
      'sel-root', ids.includes(el.dataset.node)));
  }

  function propagationNote(id) {
    // who inherits doubt from this source, and mark those reliance edges.
    const deps = dependents[id] || [];
    if (!deps.length) return '';
    edgeEls().forEach(el => {
      if (el.dataset.dst === id && RELIANCE.has(el.dataset.etype))
        el.classList.add('prop', 'on');
    });
    const src = nodes[id] || {};
    const doubt = src.doubt != null ? src.doubt : '?';
    const lead = deps.sort((a, b) => b.load - a.load)
      .map(d => `${d.id} (reliance ${d.load})`).slice(0, 4).join(', ');
    return `<div class="ks-prop">↯ ${deps.length} downstream claim(s) inherit `
      + `doubt (${doubt}) from <b>${esc(id)}</b> along load-bearing reliance: `
      + `${esc(lead)}</div>`;
  }

  function select(id) {
    const node = nodes[id];
    if (!node) return;
    const nbrs = neighbors[id] ? [...neighbors[id]] : [];
    illuminate([id, ...nbrs]);
    nodeEls().forEach(el => el.classList.toggle('sel-root', el.dataset.node === id));
    if (inspect) {
      inspect.innerHTML = nodeInspect(node) + propagationNote(id);
    }
    if (opts.onSelect) opts.onSelect(id, node, { neighbors: nbrs });
  }

  // wire clicks: a node selects; the background clears.
  nodeEls().forEach(el => el.addEventListener(
    'click', ev => { ev.stopPropagation(); select(el.dataset.node); }));
  if (svg) svg.addEventListener('click', () => {
    clear();
    if (inspect) inspect.innerHTML = opts.emptyHint
      || 'Select a node to illuminate its connected evidence and trace inherited doubt.';
  });

  return { select, highlightNodes, clear };
}
