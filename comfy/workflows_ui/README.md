# ComfyUI workflow formats

## API format (authoritative execution)

Path: `comfy/workflows/*.json`

- ComfyUI **API / prompt** graph format (`node_id → { class_type, inputs }`)
- Used by the generation provider for node injection, `POST /prompt`, workflow hash,
  provenance snapshots, and exact rerun
- Matching injection maps: `comfy/node_map/*.json`

**Never replace these files with UI-format graphs.**

## Default look lock (product, not graph topology)

Generation positives/negatives are composed in `be/app/services/style_lock.py`
before ComfyUI injection:

- **Default look:** photorealistic live-action Korean drama / cinematic film still
- **Banned:** anime, manga, cartoon, cute, RPG, illustration, painting, stylized digital art
- Workflow JSON placeholders (`PROMPT_PLACEHOLDER` / `NEGATIVE_PLACEHOLDER`) stay as-is;
  node maps inject the composed strings at submit time
- **Exact re-run** still freezes parent `prompt` / `negative_prompt` / workflow snapshot
  on the child job (provenance unchanged)

This repo runs its own ComfyUI on **`:8189`** (`make run-comfy`, `comfy_runtime/`).
Sibling / shared default remains **`:8188`** — do not point this app at 8188.

## UI format (optional visual companion)

Path: `comfy/workflows_ui/` (optional; not required for Product Agent)

- Native ComfyUI editor export with node positions, sizes, links, `widgets_values`, groups
- Useful for opening/editing in the ComfyUI canvas at `COMFYUI_BASE_URL`
- **Not** loaded by the backend generation provider
- The in-app Workflow Graph viewer derives layout from the API-format graph via dagre;
  it does not depend on UI-format files

If you export companions from ComfyUI, store them as:

```text
comfy/workflows_ui/keyframe_v1.json
comfy/workflows_ui/i2v_v1.json
```

Keep names aligned with the API workflow names, and document any drift in this file.

## Making Workflows / Assets visible in ComfyUI (:8189)

Isolated runtime starts empty. Sync UI companions + media into `comfy_runtime/`:

```bash
bash scripts/sync_comfyui_ui.sh
# or: make run-comfy   # calls sync before start
```

- Workflows sidebar reads `comfy_runtime/user/default/workflows/` (symlinks to `comfy/workflows_ui/`)
- Assets come from mirrored `input/` / `output/` (+ `storage/outputs` under `output/product/`)
- BE execution still uses API graphs in `comfy/workflows/` only
