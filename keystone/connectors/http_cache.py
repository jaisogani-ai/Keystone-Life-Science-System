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


def _slug(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def _is_offline() -> bool:
    return os.environ.get("KEYSTONE_OFFLINE") == "1"


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

    if not _is_offline():
        try:
            import requests  # optional dependency; fixtures cover its absence
            _throttle()
            resp = requests.get(url, params=params,
                                headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                cache_path.write_text(json.dumps(data))
                return data
        except Exception:
            pass  # fall through to fixture — never fabricate on failure

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
