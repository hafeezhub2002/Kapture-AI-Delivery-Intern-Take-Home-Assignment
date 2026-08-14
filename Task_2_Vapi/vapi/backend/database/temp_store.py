"""
temp_store.py
=============
Lightweight in-memory temporary store for short-lived, call-scoped data.

Use this for anything that should NOT be persisted to the main DB:
  - Pending DOB / verification attempt buffers
  - Mid-call flags  (e.g. "dob_asked", "warning_issued")
  - Any ephemeral key-value pairs tied to a call_id

Entries auto-expire after TTL_SECONDS (default: 10 minutes).
The store is a module-level singleton — import TEMP and use it anywhere.

Usage
-----
    from .temp_store import TEMP

    # Write
    TEMP.set("call-abc", "dob_asked", True)
    TEMP.set("call-abc", "attempts",  0, ttl=300)   # 5-min TTL override

    # Read  (returns None if missing or expired)
    asked = TEMP.get("call-abc", "dob_asked")

    # Increment a counter
    TEMP.increment("call-abc", "attempts")

    # Delete one key
    TEMP.delete("call-abc", "dob_asked")

    # Wipe everything for a call when it ends
    TEMP.clear_call("call-abc")
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Tuple


_MISSING = object()      # sentinel — distinct from None
DEFAULT_TTL: int = 600   # 10 minutes


class TempStore:
    """Thread-safe in-memory temporary store with per-entry TTL."""

    def __init__(self, default_ttl: int = DEFAULT_TTL) -> None:
        self._default_ttl = default_ttl
        # Structure: { call_id: { key: (value, expires_at) } }
        self._store: Dict[str, Dict[str, Tuple[Any, float]]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _expires_at(self, ttl: Optional[int]) -> float:
        return time.monotonic() + (ttl if ttl is not None else self._default_ttl)

    def _is_alive(self, expires_at: float) -> bool:
        return time.monotonic() < expires_at

    def _get_raw(self, call_id: str, key: str) -> Optional[Tuple[Any, float]]:
        """Return raw (value, expires_at) tuple, or None if absent/expired."""
        bucket = self._store.get(call_id)
        if bucket is None:
            return None
        entry = bucket.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if not self._is_alive(expires_at):
            bucket.pop(key, None)   # lazy eviction
            return None
        return entry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set(self, call_id: str, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store *value* under *call_id* / *key* with optional TTL override (seconds)."""
        with self._lock:
            self._store.setdefault(call_id, {})[key] = (value, self._expires_at(ttl))

    def get(self, call_id: str, key: str, default: Any = None) -> Any:
        """Return the stored value, or *default* if missing or expired."""
        with self._lock:
            entry = self._get_raw(call_id, key)
            return entry[0] if entry is not None else default

    def get_or_set(self, call_id: str, key: str, default: Any, ttl: Optional[int] = None) -> Any:
        """Return existing live value; if absent/expired, store *default* and return it."""
        with self._lock:
            entry = self._get_raw(call_id, key)
            if entry is not None:
                return entry[0]
            self._store.setdefault(call_id, {})[key] = (default, self._expires_at(ttl))
            return default

    def increment(self, call_id: str, key: str, by: int = 1, ttl: Optional[int] = None) -> int:
        """Atomically increment an integer counter (starts at 0 if absent). Returns new value."""
        with self._lock:
            entry = self._get_raw(call_id, key)
            current = entry[0] if entry is not None else 0
            new_val = current + by
            self._store.setdefault(call_id, {})[key] = (new_val, self._expires_at(ttl))
            return new_val

    def delete(self, call_id: str, key: str) -> None:
        """Remove a single key for a call."""
        with self._lock:
            bucket = self._store.get(call_id)
            if bucket:
                bucket.pop(key, None)

    def clear_call(self, call_id: str) -> None:
        """Remove ALL temporary data for a completed / ended call."""
        with self._lock:
            self._store.pop(call_id, None)

    def snapshot(self, call_id: str) -> Dict[str, Any]:
        """Return dict of all live key->value pairs for *call_id* (useful for debugging)."""
        with self._lock:
            bucket = self._store.get(call_id, {})
            now = time.monotonic()
            return {k: v for k, (v, exp) in bucket.items() if now < exp}

    def purge_expired(self) -> int:
        """Eagerly evict all expired entries across all calls. Returns count removed."""
        removed = 0
        now = time.monotonic()
        with self._lock:
            empty_calls: List[str] = []
            for call_id, bucket in self._store.items():
                dead = [k for k, (_, exp) in bucket.items() if now >= exp]
                for k in dead:
                    del bucket[k]
                    removed += 1
                if not bucket:
                    empty_calls.append(call_id)
            for call_id in empty_calls:
                del self._store[call_id]
        return removed

    def all_call_ids(self) -> List[str]:
        """Return list of call_ids that currently have at least one live temp entry."""
        with self._lock:
            return list(self._store.keys())

    def __repr__(self) -> str:
        with self._lock:
            return f"TempStore(calls={len(self._store)}, default_ttl={self._default_ttl}s)"


# ---------------------------------------------------------------------------
# Module-level singleton — import TEMP and use it directly anywhere
# ---------------------------------------------------------------------------
TEMP = TempStore()
