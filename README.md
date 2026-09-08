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
      → (optional) Reference search / Multimodal RAG attach
      → Generate Keyframe → Generate Short Video
      → Human Review (Approve / Reject)
      → Exact Re-run with immutable history
```

ComfyUI is the generation execution engine. Creators use a production-oriented web UI — not a raw ComfyUI playground.

**Product surfaces (FE):** Dashboard · Projects · Scene workspace · Assets · Multimodal RAG (`/search-agent`)

## Product tour

### SceneFlow — brief → shot spec → generate → review

The scene workspace is the core production surface. Creators write a **Scene Brief**, ask the LLM to **Suggest shot spec**, edit camera / lighting / subject fields, then **Generate** keyframes or short video through ComfyUI (or mock). Every completed job exposes timing, workflow id, model, seed, and a **View full provenance** trail — approve, reject, or exact re-run without overwriting history.

![Scene workspace — Project Aurora / Abandoned Factory](asset/project.png)

| Area | What you see |
|---|---|
| Scene Brief | Narrative input + **Suggest shot spec** |
| Shot Specification | Structured, versioned fields (scene, subject, camera, lighting, …) |
| Preview | Generated still / video with status, workflow (`keyframe_v1` / `i2v_v1`), model, seed |
| Provenance | Frozen config for audit and exact re-run |

### Multimodal RAG — search approved media, cite, attach

`/search-agent` is a bounded knowledge agent over **approved** production stills and clips. Ask in natural language (e.g. handheld night factory, warm practicals); the agent runs staged steps (`searching` → `reading` → `grounding_video` → `answering`), returns scored citations with thumbnails, and lets you **Attach to scene**. Attach writes a `RetrievalEvent` for provenance — it does **not** generate or approve assets.

![Multimodal RAG — cite approved references and attach to scene](asset/mmrag.png)

| Area | What you see |
|---|---|
| Chat + stages | Natural-language queries with visible agent stages |
| Citations | Image / video thumbnails, scores, media ids |
| Attach to scene | Provenance-backed handoff into SceneFlow |
| Environment strip | Live `generation` / `llm` / `embedding` providers (e.g. ComfyUI, OpenAI, Marengo) |

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 18, TypeScript, Vite, TanStack Query, React Router, Tailwind, Radix |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| DB (default) | SQLite (`data/production_agent.db`) |
| DB (optional) | PostgreSQL + pgvector via Docker Compose |
| Generation | `mock` (default) + ComfyUI adapter |
| LLM | `mock` deterministic fallback, or OpenAI when keyed |
| Embeddings (P1) | `mock` (default) or Twelve Labs Marengo 3.5 → local cosine / pgvector |
| Agents (P2) | Multimodal RAG via OpenAI Agents SDK (optional extra); mock runner without key |

**Dev ports (this repo):** frontend `http://127.0.0.1:5174` → proxies to backend `http://127.0.0.1:8001`  
(Sibling `production-agent-dev` uses `5173` / `8000` — do not mix them.)

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

Open the seeded scene URL printed by `make seed` (typically `http://127.0.0.1:5174/scenes/1`).

Health / readiness:

```bash
curl -s http://127.0.0.1:8001/api/v1/health
curl -s http://127.0.0.1:8001/api/v1/ready
```

Verify the vertical slice:

```bash
make verify
# or
make test
```

### Optional: retrieval corpus + Multimodal RAG

```bash
# Index demo approved assets (mock embeddings by default)
make seed-retrieval

# Live Marengo embeddings (set TWELVE_LABS_API_KEY + EMBEDDING_PROVIDER=marengo)
# OpenAI Agents live path (set OPENAI_API_KEY; install agents extra)
cd be && . .venv/bin/activate && pip install -e ".[agents,dev]"

make eval-retrieval   # optional retrieval smoke metrics
```

Then open **Multimodal RAG** in the UI (`/search-agent`).

### Optional: PostgreSQL

```bash
docker compose up -d db
# in .env:
# DATABASE_URL=postgresql+psycopg://production:production@127.0.0.1:5432/production_agent
make migrate
```

## Demo path (Project Aurora)

1. Open **Project Aurora → Episode 2 / Scene 18 — Abandoned Factory**
2. Generate shot spec; edit camera or lighting; save
3. (Optional) Search approved references or ask Multimodal RAG and attach into the scene
4. Generate keyframe (status: queued → running → completed)
5. Generate short video from the keyframe
6. Inspect provenance: prompt, seed, model, workflow hash, timing
7. Reject with a comment → Exact re-run (new child job; parent unchanged)
8. Approve the improved result

## Architecture

```mermaid
flowchart LR
    U["Creator"] --> FE["React + TypeScript"]
    FE --> API["FastAPI"]
    API --> SPEC["Shot Spec Service"]
    SPEC --> LLM["LLM / mock"]
    API --> RET["Retrieval Service"]
    RET --> EMB["Mock / Marengo"]
    API --> AG["Agents / Multimodal RAG"]
    AG --> EMB
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
7. Multimodal RAG **searches and cites** approved media; it does not generate or approve assets.

## Configuration

See [`.env.example`](.env.example). Important keys:

```text
GENERATION_PROVIDER=mock|comfyui
COMFYUI_BASE_URL=http://127.0.0.1:8188
LLM_PROVIDER=mock|openai
OPENAI_API_KEY=
EMBEDDING_PROVIDER=mock|marengo
TWELVE_LABS_API_KEY=
AGENTS_SDK_ENABLED=true
OPENAI_AGENT_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./data/production_agent.db
CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
```

## Repository layout

```text
be/                 FastAPI application (app/, alembic/, tests/)
  app/agents/       Multimodal RAG catalog, runners, conversations
  app/providers/    mock, ComfyUI, LLM, Marengo embeddings
  app/services/     generation, shot spec, review, retrieval, …
fe/                 React app (Dashboard, Projects, Scene, Assets, RAG)
comfy/              Versioned workflow JSON + node maps
asset/              README product screenshots (SceneFlow, Multimodal RAG)
storage/            Generated + retrieval assets
data/demo/          Project Aurora fixture
data/retrieval/     Retrieval corpus fixture
scripts/            seed_demo, seed_retrieval_corpus, eval_retrieval, verify_demo
```

## Make targets

| Target | Purpose |
|---|---|
| `make be-install` / `fe-install` | Create venv / `npm install` |
| `make run-be` / `run-fe` | Dev servers on **8001** / **5174** |
| `make seed` | Project Aurora demo |
| `make seed-retrieval` | Index retrieval corpus |
| `make eval-retrieval` | Retrieval eval script |
| `make verify` / `test` | Smoke / pytest |
| `make db-up` / `migrate` | Postgres + Alembic |

## Non-goals (current scope)

Full autonomous multi-agent production loops, Redis/Celery/K8s, enterprise RBAC, cloud deployment, LoRA training, managed Twelve Labs `/search` (we embed + search locally).

## Trade-offs

| Choice | Why |
|---|---|
| Polling every ~2s | Enough for single-user MVP; SSE later |
| Mock providers default | Interview / demo reliability without GPU or paid keys |
| SQLite default | Zero-friction local draft; Postgres + pgvector ready |
| Ports 5174 / 8001 | Avoid colliding with sibling `production-agent-dev` |
| Immutable shot-spec versions on edit | History over in-place mutation |
| Marengo embeddings only | Vectors + local cosine; no managed search dependency |

---

**One sentence:** This project is `Generate → Review → Regenerate → Approve → Trace/Reproduce` (with optional reference search), not “I generated a video.”
