"""Timestamped log path helpers for prod-agent-dev.

Convention (KST wall clock unless overridden):
  logs/YYYYMMDD_HHMM_<slug>.<ext>

Examples:
  logs/20260909_0155_be.log
  logs/20260909_0140_diverse_videos_evidence.json
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
KST = timezone(timedelta(hours=9))


def stamp(when: datetime | None = None) -> str:
    """Return YYYYMMDD_HHMM in Asia/Seoul."""
    dt = when or datetime.now(KST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    else:
        dt = dt.astimezone(KST)
    return dt.strftime("%Y%m%d_%H%M")


def log_path(slug: str, *, ext: str = "log", when: datetime | None = None) -> Path:
    """Build logs/YYYYMMDD_HHMM_<slug>.<ext> (creates logs/ if needed)."""
    LOGS.mkdir(parents=True, exist_ok=True)
    clean = slug.strip().lstrip("/").replace(" ", "_")
    if clean.endswith(f".{ext}"):
        clean = clean[: -(len(ext) + 1)]
    # Avoid double-prefix if caller already stamped.
    if len(clean) >= 13 and clean[8] == "_" and clean[:8].isdigit() and clean[9:13].isdigit():
        name = f"{clean}.{ext}" if not clean.endswith(f".{ext}") else clean
    else:
        name = f"{stamp(when)}_{clean}.{ext}"
    return LOGS / name


def stamp_existing_name(path: Path) -> str:
    """Prefix an existing basename with its mtime (KST) if not already stamped."""
    name = path.name
    if len(name) >= 14 and name[8] == "_" and name[:8].isdigit() and name[9:13].isdigit():
        return name
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=KST)
    return f"{stamp(mtime)}_{name}"
