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

### Dashboard — workflow health at a glance

Landing surface for production health: job counts, approval rate, average attempts / gen time, and recent activity — with live provider status in the sidebar (ComfyUI, OpenAI, Marengo).

![Dashboard — jobs, approvals, and recent activity](asset/dashboard.png)

### Projects — scenes under Project Aurora

Browse projects and open scenes (episode / scene / draft status). Project Aurora is the seeded drama previz sandbox used throughout the demo path.

![Projects — Project Aurora scene list](asset/project_list.png)

### SceneFlow — brief → shot spec → generate → review

The scene workspace is the core production surface. Creators write a **Scene Brief**, ask the LLM to **Suggest shot spec**, edit camera / lighting / subject fields, then **Generate** keyframes or short video through ComfyUI. Every completed job exposes timing, workflow id, model, seed, and a **View full provenance** trail — approve, reject, or exact re-run without overwriting history.

![Scene workspace — Project Aurora / Abandoned Factory](asset/project.png)

| Area | What you see |
|---|---|
| Scene Brief | Narrative input + **Suggest shot spec** |
| Shot Specification | Structured, versioned fields (scene, subject, camera, lighting, …) |
| Preview | Generated still / video with status, workflow (`keyframe_v1` / `i2v_v1`), model, seed |
| Provenance | Frozen config for audit and exact re-run |

### Assets — approved and generated media library

Browse keyframes and videos from completed jobs. Detail views keep technical paths; the grid is the production media library for review and RAG indexing.

![Assets — keyframe and video library](asset/assets.png)

### Multimodal RAG — search approved media, cite, attach

`/search-agent` is a bounded knowledge agent over **approved** production stills and clips. Ask in natural language (e.g. handheld night factory, warm practicals); the agent runs staged steps (`searching` → `reading` → `grounding_video` → `answering`), returns scored citations with thumbnails, and lets you **Attach to scene**. Attach writes a `RetrievalEvent` for provenance — it does **not** generate or approve assets.

![Multimodal RAG — cite approved references and attach to scene](asset/mmrag.png)

| Area | What you see |
|---|---|
| Chat + stages | Natural-language queries with visible agent stages |
| Citations | Image / video thumbnails, scores, media ids |
| Attach to scene | Provenance-backed handoff into SceneFlow |
| Environment strip | Live `generation` / `llm` / `embedding` providers (e.g. ComfyUI, OpenAI, Marengo) |

### Generation workflows — keyframe still & short video

SceneFlow generates media through two fixed ComfyUI workflows. **Keyframe** makes the image; **I2V** (image-to-video) turns an approved keyframe into a short clip.

![ComfyUI generation workflows — keyframe_v1 / i2v_v1](asset/workflow.png)

| Job | Role | Workflow | Models |
|---|---|---|---|
| **Keyframe** | Keyframe image from shot spec | `comfy/workflows/keyframe_v1.json` | `sd_xl_base_1.0.safetensors` |
| **I2V** | Short video from approved keyframe | `comfy/workflows/i2v_v1.json` | `wan2.2_ti2v_5B_fp16.safetensors` · `umt5_xxl_fp8_e4m3fn_scaled.safetensors` · `wan2.2_vae.safetensors` |

#### What each model does

| File | Used for | Role |
|---|---|---|
| `sd_xl_base_1.0.safetensors` | Keyframe | **SDXL** image model — turns the shot-spec prompt into one photorealistic frame. A *checkpoint* is the full saved weights for that image model. |
| `wan2.2_ti2v_5B_fp16.safetensors` | I2V | **Wan 2.2** video generator (TI2V = text+image → video). The main network that animates the keyframe into a short clip (~5B parameters; `fp16` = half-precision weights for GPU memory). |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | I2V | **Text encoder** (UMT5-XXL) — converts the motion / scene prompt into numbers the video model can use. Not an image model; it only understands text. |
| `wan2.2_vae.safetensors` | I2V | **VAE** (Variational Autoencoder) — compresses images/frames into a smaller internal form for generation, then decodes them back to visible pixels. Think “zip/unzip for pictures” so the big video model can run efficiently. |

**Terms in brief:**

- *I2V* — image-to-video
- *checkpoint* — packaged model weights
- *safetensors* — safe weight file format
- *UNet* / diffusion backbone — the core “paint the next frame” network inside Wan
- *fp8* / *fp16* — lower-precision number formats that save VRAM

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 18, TypeScript, Vite, TanStack Query, React Router, Tailwind, Radix |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| DB (default) | SQLite (`data/production_agent.db`) |
| DB (optional) | PostgreSQL + pgvector via Docker Compose |
| Generation | ComfyUI (`keyframe_v1`, `i2v_v1`) |
| LLM | OpenAI (shot-spec suggest) |
| Embeddings (P1) | Twelve Labs Marengo 3.5 → local cosine / pgvector |
| Agents (P2) | Multimodal RAG via OpenAI Agents SDK |

**Dev ports:** frontend `http://127.0.0.1:5174` → proxies to backend `http://127.0.0.1:8001`

## Quick start

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
# Index demo approved assets
make seed-retrieval

# Live Marengo embeddings (set TWELVE_LABS_API_KEY + EMBEDDING_PROVIDER=marengo)
# OpenAI Agents path (set OPENAI_API_KEY; install agents extra)
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
    SPEC --> LLM["LLM"]
    API --> RET["Retrieval Service"]
    RET --> EMB["Marengo embeddings"]
    API --> AG["Agents / Multimodal RAG"]
    AG --> EMB
    API --> GS["Generation Service"]
    GS --> CW["Workflow Registry"]
    GS --> COMFY["ComfyUI"]
    GS --> DB[("SQLite / PostgreSQL")]
    GS --> STORE["Asset Storage"]
    FE --> REVIEW["Approve / Reject / Regenerate"]
```

## Design invariants

1. The agent is a **bounded coordinator** — it never approves its own output.
2. Every job stores a **frozen configuration** (prompt, seed, model, workflow hash, …).
3. Exact re-run creates a **new** job with `parent_generation_id`; prior rows are never overwritten.
4. Frontend never talks to ComfyUI directly — generation goes through FastAPI.
5. Only two checked-in workflows: `keyframe_v1`, `i2v_v1`.
6. Multimodal RAG **searches and cites** approved media; it does not generate or approve assets.

## Configuration

See [`.env.example`](.env.example). Important keys:

```text
GENERATION_PROVIDER=comfyui
COMFYUI_BASE_URL=http://127.0.0.1:8189
LLM_PROVIDER=openai
OPENAI_API_KEY=
EMBEDDING_PROVIDER=marengo
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
  app/providers/    ComfyUI, LLM, Marengo embeddings
  app/services/     generation, shot spec, review, retrieval, …
fe/                 React app (Dashboard, Projects, Scene, Assets, RAG)
comfy/              Versioned workflow JSON + node maps
asset/              README product screenshots (Dashboard, Projects, SceneFlow, Assets, RAG, workflows)
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

---

**One sentence:** This project is `Generate → Review → Regenerate → Approve → Trace/Reproduce` (with optional reference search), not “I generated a video.”
