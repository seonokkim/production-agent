#!/usr/bin/env python3
"""Seed fictional production documents into storage/landing (not real drama docs)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "storage" / "landing"

DOCS = {
    "aurora_ep2_scene18_brief.md": """# Project Aurora — Episode 2 / Scene 18

Late at night, a detective enters an abandoned factory.
Rain and neon light enter through broken windows.
Camera slowly follows behind the detective.
Mood: tense and cold.

(Fictional demo document — not a real production script.)
""",
    "aurora_shot_list.csv": """shot_no,location,shot_size,camera_motion,notes
1,abandoned factory,medium wide,slow tracking,detective entrance
2,factory interior,close-up,static,neon reflection on wet floor
3,broken window,wide,pan left,rain silhouette
""",
    "aurora_call_sheet.txt": """PROJECT AURORA — FICTIONAL CALL SHEET
Episode 2 / Scene 18 — Abandoned Factory
Unit call: 19:00
Est. wrap: 02:00
Characters: Detective Alex, Mina
Location: Studio Stage B (virtual)
Notes: Night interior; practical rain; neon practicals.
""",
    "aurora_production_note.md": """# Production note (demo)

- Prefer cooler grade on regenerate.
- Keep detective silhouette readable against neon.
- Do not use identifiable actor likeness.

This file is a sample production_document asset for Airflow ETL demos.
""",
}


def main() -> None:
    LANDING.mkdir(parents=True, exist_ok=True)
    for name, body in DOCS.items():
        path = LANDING / name
        path.write_text(body, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    print(f"Seeded {len(DOCS)} fictional documents into {LANDING}")


if __name__ == "__main__":
    main()
