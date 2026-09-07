# Production Agent

A production-oriented AI Creation workflow for turning scene briefs
into reviewable, reproducible image and video assets.

**Positioning:** Production Agent — AI Creation Workflow for Drama Previsualization  
**Core module:** SceneFlow  
**Keyword:** Provenance

> Production Agent uses deterministic, reviewable workflows rather than an autonomous agent loop for production-critical operations.

## What it does

```text
Scene Brief → LLM Shot Spec → Creator Edit
      → Generate Keyframe → Generate Short Video
      → Human Review (Approve / Reject)
      → Exact Re-run with immutable history
```

ComfyUI is the generation execution engine. Creators use a production-oriented web UI — not a raw ComfyUI playground.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React, TypeScript, Vite, TanStack Query, React Router |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 |
| DB (default draft) | SQLite file (`data/production_agent.db`) |
| DB (optional) | PostgreSQL via Docker Compose |
| Generation | `mock` provider (default) + ComfyUI adapter |
| LLM | `mock` deterministic fallback (or OpenAI when keyed) |

## Quick start (mock mode — no GPU required)

```bash
cp .env.example .env
make be-install
make fe-install
make seed
# terminal 1
make run-be
# terminal 2
make run-fe
```

Open the seeded scene URL printed by `make seed` (typically `/scenes/1`).

Verify the vertical slice:

```bash
make verify
# or
make test
```

## Demo path (Project Aurora)

1. Open **Project Aurora → Episode 2 / Scene 18 — Abandoned Factory**
2. Generate shot spec; edit camera or lighting; save
3. Generate keyframe (status: queued → running → completed)
4. Generate 4s video from the keyframe
5. Inspect provenance: prompt, seed, model, workflow hash, timing
6. Reject with a comment → Exact re-run (new child job; parent unchanged)
7. Approve the improved result

## Architecture

```mermaid
flowchart LR
    U["Creator"] --> FE["React + TypeScript"]
    FE --> API["FastAPI"]
    API --> SPEC["Shot Spec Service"]
    SPEC --> LLM["LLM / mock"]
    API --> GS["Generation Service"]
    GS --> CW["Workflow Registry"]
    GS --> COMFY["ComfyUI or Mock"]
    GS --> DB[("SQLite / PostgreSQL")]
    GS --> STORE["Asset Storage"]
    FE --> REVIEW["Approve / Reject / Regenerate"]
```

## Design invariants

1. The agent is a **bounded coordinator** — it never approves its own output.
2. Every job stores a **frozen configuration** (prompt, seed, model, workflow hash, …).
3. Exact re-run creates a **new** job with `parent_generation_id`; prior rows are never overwritten.
4. `GENERATION_PROVIDER=mock` supports the full product without a GPU.
5. Frontend never talks to ComfyUI directly.
6. Only two checked-in workflows: `keyframe_v1`, `i2v_v1`.

## Configuration

See `.env.example`. Important keys:

```text
GENERATION_PROVIDER=mock|comfyui
COMFYUI_BASE_URL=http://127.0.0.1:8188
LLM_PROVIDER=mock|openai
OPENAI_API_KEY=
DATABASE_URL=sqlite:///./data/production_agent.db
```

For PostgreSQL:

```bash
docker compose up -d db
# set DATABASE_URL=postgresql+psycopg://production:production@127.0.0.1:5432/production_agent
```

## Repository layout

```text
be/          FastAPI application
fe/          React Scene Workspace
comfy/       Versioned workflow JSON + node maps
storage/     Generated assets
data/demo/   Project Aurora fixture
scripts/     seed_demo.py, verify_demo.py
```

## Non-goals (P0)

RAG, multi-agent orchestration, Redis/Celery/K8s, enterprise RBAC, cloud deployment, LoRA training.

## Trade-offs

| Choice | Why |
|---|---|
| Polling every ~2s | Enough for single-user MVP; SSE later |
| Mock provider default | Interview reliability without GPU |
| SQLite default | Zero-friction local draft; Postgres ready |
| Immutable shot-spec versions on edit | History over in-place mutation |

---

**One sentence:** This project is `Generate → Review → Regenerate → Approve → Trace/Reproduce`, not “I generated a video.”
