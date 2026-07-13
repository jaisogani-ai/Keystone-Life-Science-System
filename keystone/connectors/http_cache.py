"""
keystone.connectors.http_cache
=============================
Tiny cache-first HTTP layer for the connectors. Order of resolution:

    on-disk cache  ->  live HTTP (if online & requests available)  ->  fixture

Everything is cached to disk so a second run is offline and reproducible, and a
pinned fixture is the final fallback if the network is down or rate-limited. No
connector ever fabricates data: a miss returns ``None`` and the caller marks the
node ``unresolved``.

Set ``KEYSTONE_OFFLINE=1`` to skip the network entirely (cache + fixtures only).
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional

_HERE = Path(__file__).resolve().parent
CACHE_DIR = _HERE / "cache"
FIXTURE_DIR = _HERE / "fixtures"
CACHE_DIR.mkdir(exist_ok=True)
FIXTURE_DIR.mkdir(exist_ok=True)

USER_AGENT = ("Keystone-research-workbench/0.1 "
              "(mailto:jaisogani183@gmail.com)")
_MIN_INTERVAL_S = 0.34   # be polite: ~3 req/s max to shared public APIs
_last_call = {"t": 0.0}
# short timeout + circuit breaker: in a sandbox with no outbound network, the
# FIRST failed live call trips the breaker so every later call skips straight to
# the pinned fixture instead of blocking the page for 30s each.
_HTTP_TIMEOUT = int(os.environ.get("KEYSTONE_HTTP_TIMEOUT", "8"))
_NET_PROBE_TIMEOUT = float(os.environ.get("KEYSTONE_NET_PROBE_TIMEOUT", "1.5"))
_net = {"down": False, "probed": False}


def _network_reachable() -> bool:
    """One-time check for *usable* outbound network. Per-request ``timeout`` and
    layer-probes are not enough on their own: DNS (``getaddrinfo``) ignores
    socket timeouts, and a restricted network can accept the TCP connect yet
    silently drop the data — so a page that fans out to several connectors (or
    a live Claude call) would still hang for a long time. Only a real HTTP
    round-trip catches all three (DNS / connect / read). We do one, inside a
    daemon thread capped with ``join`` so the probe itself can never block past
    the budget no matter which layer stalls. Any HTTP status proves usable
    network; a timeout/error trips the breaker and every connector call and live
    Claude falls straight to its offline path. Probed once, cached per process.
    ``KEYSTONE_OFFLINE=1`` skips the probe entirely."""
    if _net["probed"]:
        return not _net["down"]
    _net["probed"] = True
    # Only the launch-level offline flag trips the permanent network breaker. A
    # transient fixture-backed build (force_offline) must NOT cache the network
    # as down, or the process would stay offline for its whole lifetime.
    if _stable_offline():
        _net["down"] = True
        return False
    import threading
    result = {"ok": False}

    def _probe() -> None:
        try:
            import requests
            # Any response (even 401/404) proves the network is usable.
            requests.head("https://api.anthropic.com/",
                          timeout=(_NET_PROBE_TIMEOUT, _NET_PROBE_TIMEOUT))
            result["ok"] = True
        except Exception:
            result["ok"] = False   # DNS/connect/read failure, or no requests

    t = threading.Thread(target=_probe, daemon=True)
    t.start()
    t.join(_NET_PROBE_TIMEOUT * 2 + 0.5)   # hard wall-clock cap on the probe
    if not result["ok"]:
        _net["down"] = True
    return not _net["down"]


def _slug(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:24]


# A deterministic build (e.g. the pinned GBM/ICH/insulin graph) needs fixtures
# only, but it must NOT mutate the process-global environment to get them: in an
# async server that env mutation races between concurrent requests and leaks,
# permanently bricking live Claude and live search. This ContextVar carries that
# "fixtures only for this block" intent in an async- and thread-safe way.
_force_offline_cv: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "keystone_force_offline", default=False)


def _stable_offline() -> bool:
    """The launch-level intent: the whole process is pinned offline (tests, the
    offline demo config). Stable for the process lifetime — safe to cache on."""
    return os.environ.get("KEYSTONE_OFFLINE") == "1"


def _is_offline() -> bool:
    """Effective offline for a single connector call: the process is pinned
    offline, or the current context is a deterministic fixture-backed build."""
    return _stable_offline() or _force_offline_cv.get()


@contextlib.contextmanager
def force_offline(active: bool = True):
    """Resolve connectors from pinned fixtures only for the duration of the
    block, without touching global state. Lets a *live* server build its
    reproducible domain graph from fixtures while live Claude and live prior-art
    search keep working for every other request."""
    if not active:
        yield
        return
    token = _force_offline_cv.set(True)
    try:
        yield
    finally:
        _force_offline_cv.reset(token)


def _read_json(path: Path) -> Optional[dict]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _throttle() -> None:
    dt = time.time() - _last_call["t"]
    if dt < _MIN_INTERVAL_S:
        time.sleep(_MIN_INTERVAL_S - dt)
    _last_call["t"] = time.time()


def cached_get_json(url: str, params: Optional[dict] = None,
                    fixture_name: Optional[str] = None) -> Optional[dict]:
    """Resolve a GET request through cache -> live -> fixture. Returns parsed
    JSON or ``None`` (never a fabricated payload)."""
    key = url + "?" + json.dumps(params or {}, sort_keys=True)
    cache_path = CACHE_DIR / f"{_slug(key)}.json"

    cached = _read_json(cache_path)
    if cached is not None:
        return cached

    if not _is_offline() and _network_reachable():
        try:
            import requests  # optional dependency; fixtures cover its absence
            _throttle()
            resp = requests.get(url, params=params,
                                headers={"User-Agent": USER_AGENT},
                                timeout=_HTTP_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                cache_path.write_text(json.dumps(data))
                return data
        except Exception:
            _net["down"] = True   # network unreachable — stop retrying; use fixtures
            # (fall through to fixture — never fabricate on failure)

    if fixture_name:
        return _read_json(FIXTURE_DIR / fixture_name)
    return None


def cached_post_json(url: str, body: dict,
                     fixture_name: Optional[str] = None) -> Optional[dict]:
    """Resolve a POST (e.g. a GraphQL query) through cache -> live -> fixture,
    keyed by url + body so each distinct query caches separately. Returns parsed
    JSON or ``None`` — never a fabricated payload."""
    key = url + "#" + json.dumps(body, sort_keys=True)
    cache_path = CACHE_DIR / f"{_slug(key)}.json"

    cached = _read_json(cache_path)
    if cached is not None:
        return cached

    if not _is_offline() and _network_reachable():
        try:
            import requests
            _throttle()
            resp = requests.post(url, json=body,
                                 headers={"User-Agent": USER_AGENT,
                                          "Content-Type": "application/json"},
                                 timeout=_HTTP_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                cache_path.write_text(json.dumps(data))
                return data
        except Exception:
            _net["down"] = True   # network unreachable — fall through to fixture

    if fixture_name:
        return _read_json(FIXTURE_DIR / fixture_name)
    return None


def save_fixture(name: str, data: dict) -> Path:
    """Used by the capture tool to pin a real API response as an offline fixture."""
    path = FIXTURE_DIR / name
    path.write_text(json.dumps(data, indent=2))
    return path


def cached_get_text(url: str, params: Optional[dict] = None,
                    fixture_name: Optional[str] = None) -> Optional[str]:
    """Like cached_get_json but for text payloads (e.g. an SVG 2D structure).
    cache -> live -> fixture; returns None on miss (never fabricated)."""
    key = "TEXT:" + url + "?" + json.dumps(params or {}, sort_keys=True)
    cache_path = CACHE_DIR / f"{_slug(key)}.txt"
    if cache_path.exists():
        try:
            return cache_path.read_text()
        except OSError:
            pass
    if not _is_offline():
        try:
            import requests
            _throttle()
            resp = requests.get(url, params=params,
                                headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code == 200:
                cache_path.write_text(resp.text)
                return resp.text
        except Exception:
            pass
    if fixture_name:
        p = FIXTURE_DIR / fixture_name
        if p.exists():
            return p.read_text()
    return None


def save_text_fixture(name: str, text: str) -> Path:
    path = FIXTURE_DIR / name
    path.write_text(text)
    return path
