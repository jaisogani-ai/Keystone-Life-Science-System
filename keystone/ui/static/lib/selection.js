// Keystone shared selection bus — the mechanism that makes the workbench feel
// connected: one focus entity, many subscribed viewers. A viewer publishes what
// the scientist selected (a gene, protein, variant, paper, trial); every other
// viewer that cares re-renders around it. No framework, no global mutation of
// anyone else's DOM — each subscriber owns its own update.
//
// An entity is { type, id, label, data }. Subscribers filter by type as needed.

const _subs = new Set();
let _current = null;

export function focus(entity) {
  _current = entity;
  for (const cb of _subs) {
    try { cb(entity); } catch (e) { /* a broken subscriber never breaks the bus */ }
  }
}

export function onFocus(cb) {
  _subs.add(cb);
  if (_current) { try { cb(_current); } catch (e) { /* ignore */ } }
  return () => _subs.delete(cb);   // unsubscribe
}

export function current() { return _current; }

export function clearFocus() { focus(null); }
