"""Isolate test DB/storage before any app imports in test modules.

test_core_flow.py still sets env at import time; this file documents the contract
and ensures _tmp is writable.
"""

from __future__ import annotations

from pathlib import Path

_TMP = Path(__file__).resolve().parent / "_tmp"
_TMP.mkdir(exist_ok=True)
(_TMP / "storage").mkdir(exist_ok=True)
