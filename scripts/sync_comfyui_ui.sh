#!/usr/bin/env bash
# Populate isolated ComfyUI so the web UI shows this repo's workflows + media.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export REPO_ROOT
if [[ -z "${COMFYUI_INSTALL:-}" ]]; then
  echo "Set COMFYUI_INSTALL to your ComfyUI install path, e.g.:" >&2
  echo "  export COMFYUI_INSTALL=/path/to/ComfyUI" >&2
  exit 1
fi
COMFY_ROOT="$COMFYUI_INSTALL"
export COMFYUI_INSTALL="$COMFY_ROOT"
RUNTIME="${REPO_ROOT}/comfy_runtime"

if [[ ! -d "$COMFY_ROOT" ]]; then
  echo "ComfyUI install not found: $COMFY_ROOT" >&2
  exit 1
fi

mkdir -p \
  "${REPO_ROOT}/comfy/workflows_ui" \
  "${RUNTIME}/user/default/workflows" \
  "${RUNTIME}/input" \
  "${RUNTIME}/output" \
  "${RUNTIME}/output/product"

# 1) Build UI-format companions from this repo's API graphs + install into userdata.
python3 <<'PY'
import json
import os
from pathlib import Path

repo = Path(os.environ["REPO_ROOT"])
ui_dir = repo / "comfy" / "workflows_ui"
api_dir = repo / "comfy" / "workflows"
wf_dst = repo / "comfy_runtime" / "user" / "default" / "workflows"
ui_dir.mkdir(parents=True, exist_ok=True)
wf_dst.mkdir(parents=True, exist_ok=True)

WIDGET_KEYS = {
    "CheckpointLoaderSimple": ["ckpt_name"],
    "CLIPTextEncode": ["text"],
    "EmptyLatentImage": ["width", "height", "batch_size"],
    # UI inserts control_after_generate after seed (not in API schema).
    "KSampler": ["seed", "__control_after_generate__", "steps", "cfg", "sampler_name", "scheduler", "denoise"],
    "VAEDecode": [],
    "SaveImage": ["filename_prefix"],
    "UNETLoader": ["unet_name", "weight_dtype"],
    "CLIPLoader": ["clip_name", "type", "device"],
    "VAELoader": ["vae_name"],
    "ModelSamplingSD3": ["shift"],
    "LoadImage": ["image"],
    "Wan22ImageToVideoLatent": ["width", "height", "length", "batch_size"],
    "CreateVideo": ["fps"],
    "SaveVideo": ["filename_prefix", "format", "codec"],
}

OUTPUT_SLOTS = {
    "CheckpointLoaderSimple": [("MODEL", "MODEL"), ("CLIP", "CLIP"), ("VAE", "VAE")],
    "CLIPTextEncode": [("CONDITIONING", "CONDITIONING")],
    "EmptyLatentImage": [("LATENT", "LATENT")],
    "KSampler": [("LATENT", "LATENT")],
    "VAEDecode": [("IMAGE", "IMAGE")],
    "SaveImage": [],
    "UNETLoader": [("MODEL", "MODEL")],
    "CLIPLoader": [("CLIP", "CLIP")],
    "VAELoader": [("VAE", "VAE")],
    "ModelSamplingSD3": [("MODEL", "MODEL")],
    "LoadImage": [("IMAGE", "IMAGE"), ("MASK", "MASK")],
    "Wan22ImageToVideoLatent": [("LATENT", "LATENT")],
    "CreateVideo": [("VIDEO", "VIDEO")],
    "SaveVideo": [],
}

LINK_INPUT_TYPES = {
    "clip": "CLIP",
    "model": "MODEL",
    "positive": "CONDITIONING",
    "negative": "CONDITIONING",
    "latent_image": "LATENT",
    "samples": "LATENT",
    "vae": "VAE",
    "images": "IMAGE",
    "image": "IMAGE",
    "start_image": "IMAGE",
    "video": "VIDEO",
}


def api_to_ui(api: dict, workflow_id: str) -> dict:
    node_ids = sorted(api.keys(), key=lambda x: int(x) if str(x).isdigit() else 0)
    links: list = []
    link_id = 1
    nodes: list = []
    for order, nid in enumerate(node_ids):
        data = api[nid]
        ctype = data["class_type"]
        inputs = data.get("inputs") or {}
        ui_inputs = []
        widgets = []
        for key in WIDGET_KEYS.get(ctype, []):
            if key == "__control_after_generate__":
                widgets.append("fixed")
                continue
            val = inputs.get(key)
            if isinstance(val, list) and len(val) == 2:
                continue
            if key in inputs:
                widgets.append(inputs[key])
        # UI-loadable default: real file under comfy_runtime/input (API keeps placeholder).
        if ctype == "LoadImage":
            widgets = ["reference_keyframe.png"]
        for key, val in inputs.items():
            if isinstance(val, list) and len(val) == 2:
                src, slot = int(val[0]), int(val[1])
                target_slot = len(ui_inputs)
                links.append(
                    [
                        link_id,
                        src,
                        slot,
                        int(nid),
                        target_slot,
                        LINK_INPUT_TYPES.get(key, "*"),
                    ]
                )
                ui_inputs.append(
                    {
                        "name": key,
                        "type": LINK_INPUT_TYPES.get(key, "*"),
                        "link": link_id,
                    }
                )
                link_id += 1
        outputs = []
        for i, (name, typ) in enumerate(OUTPUT_SLOTS.get(ctype, [])):
            outputs.append({"name": name, "type": typ, "links": [], "slot_index": i})
        nodes.append(
            {
                "id": int(nid),
                "type": ctype,
                "pos": [80 + (order % 4) * 380, 80 + (order // 4) * 220],
                "size": [340, 80 + 20 * max(1, len(widgets))],
                "flags": {},
                "order": order,
                "mode": 0,
                "inputs": ui_inputs,
                "outputs": outputs,
                "properties": {"Node name for S&R": ctype},
                "widgets_values": widgets,
            }
        )

    id_to_node = {n["id"]: n for n in nodes}
    for link in links:
        lid, origin, origin_slot, _t, _ts, _typ = link
        src = id_to_node.get(origin)
        if src and origin_slot < len(src["outputs"]):
            out = src["outputs"][origin_slot]
            out.setdefault("links", [])
            if out["links"] is None:
                out["links"] = []
            out["links"].append(lid)

    return {
        "id": workflow_id,
        "revision": 0,
        "last_node_id": max((n["id"] for n in nodes), default=0),
        "last_link_id": max((l[0] for l in links), default=0),
        "nodes": nodes,
        "links": links,
        "groups": [],
        "config": {},
        "extra": {"ds": {"scale": 0.75, "offset": [40, 40]}},
        "version": 0.4,
    }


for name in ("keyframe_v1", "i2v_v1"):
    api_path = api_dir / f"{name}.json"
    out = ui_dir / f"{name}.json"
    if api_path.exists():
        ui = api_to_ui(json.loads(api_path.read_text()), f"prod-agent-{name}")
        out.write_text(json.dumps(ui, indent=2) + "\n")
        print(f"wrote {out}")
    elif out.exists():
        print(f"kept existing UI workflow {out}")
    else:
        print(f"WARNING: missing API workflow {api_path}; no UI graph for {name}")

for src in ui_dir.glob("*.json"):
    dst = wf_dst / src.name
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    dst.symlink_to(src.resolve())
    print(f"linked {dst.name}")
PY

# 2) Mirror media into isolated input/output (hardlink/copy; no sibling config change).
python3 <<'PY'
import os
import shutil
import sqlite3
from pathlib import Path

repo = Path(os.environ["REPO_ROOT"])
comfy = Path(os.environ["COMFYUI_INSTALL"])
runtime = repo / "comfy_runtime"
input_dir = runtime / "input"
output_dir = runtime / "output"
product_out = output_dir / "product"
product_out.mkdir(parents=True, exist_ok=True)
input_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)


def link_tree(src: Path, dst: Path) -> int:
    """Hardlink (preferred) or copy files into dst.

    ComfyUI LoadImage rejects symlinks that resolve outside --base-directory.
    """
    if not src.is_dir():
        return 0
    n = 0
    for path in src.rglob("*"):
        if not path.is_file():
            continue
        # Skip nesting product into itself
        try:
            if path.resolve().is_relative_to(dst.resolve()):
                continue
        except Exception:
            pass
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            # Refresh broken symlinks / outdated links
            if target.is_symlink():
                target.unlink()
            elif target.is_file() and target.stat().st_ino == path.stat().st_ino:
                continue
            elif target.is_file() and target.stat().st_size == path.stat().st_size:
                continue
            else:
                target.unlink()
        try:
            os.link(path, target)
        except OSError:
            shutil.copy2(path, target)
        n += 1
    return n


n_in = link_tree(comfy / "input", input_dir)
n_out = link_tree(comfy / "output", output_dir)
n_prod = link_tree(repo / "storage" / "outputs", product_out)
print(f"linked input={n_in} shared_output={n_out} product_output={n_prod}")

# Ensure UI default reference exists as a real in-tree file.
ref = input_dir / "reference_keyframe.png"
candidates = [
    input_dir / "ui_ref_keyframe.png",
    input_dir / "smoke_ref_keyframe.png",
    input_dir / "manual_keyframe_gateA.png",
    input_dir / "example.png",
]
if not ref.exists() or ref.is_symlink():
    if ref.is_symlink() or ref.exists():
        ref.unlink()
    src = next((c for c in candidates if c.exists() and not c.is_symlink()), None)
    if src is None:
        src = next((c for c in candidates if c.exists()), None)
    if src is not None:
        src = src.resolve() if src.is_symlink() else src
        try:
            os.link(src, ref)
        except OSError:
            shutil.copy2(src, ref)
        print(f"seeded {ref.name} from {src}")
    else:
        print("WARNING: no candidate image to seed reference_keyframe.png")
else:
    print(f"reference_keyframe.png ok size={ref.stat().st_size}")

# 3) Rewrite asset DB paths into this runtime so Assets UI stops marking them missing.
db = runtime / "user" / "comfyui.db"
if db.exists():
    con = sqlite3.connect(str(db))
    replacements = [
        (str(comfy / "input"), str(input_dir)),
        (str(comfy / "output"), str(output_dir)),
        (str(comfy / "models"), str(runtime / "models")),
    ]
    cur = con.cursor()
    existing = {
        row[0]
        for row in cur.execute("select file_path from asset_references").fetchall()
        if row[0]
    }
    fixed = 0
    skipped = 0
    rows = cur.execute("select id, file_path, is_missing from asset_references").fetchall()
    for rid, fpath, missing in rows:
        if not fpath:
            continue
        new = fpath
        for old, new_root in replacements:
            if new.startswith(old):
                new = new_root + new[len(old) :]
                break
        exists = Path(new).exists()
        if new == fpath:
            if exists and missing:
                cur.execute(
                    "update asset_references set is_missing=0 where id=?",
                    (rid,),
                )
                fixed += 1
            continue
        if new in existing:
            # Duplicate after remap — drop the old shared-path row if file is covered.
            cur.execute("delete from asset_references where id=?", (rid,))
            skipped += 1
            continue
        cur.execute(
            "update asset_references set file_path=?, is_missing=? where id=?",
            (new, 0 if exists else 1, rid),
        )
        existing.discard(fpath)
        existing.add(new)
        fixed += 1
    con.commit()
    miss = cur.execute("select count(*) from asset_references where is_missing=1").fetchone()[0]
    ok = cur.execute("select count(*) from asset_references where is_missing=0").fetchone()[0]
    con.close()
    print(f"asset_db updated rows={fixed} deduped={skipped} ok={ok} missing={miss}")
else:
    print("no comfyui.db yet; will populate on next ComfyUI start")
PY

echo "sync done. Refresh ComfyUI Workflows/Assets (or restart :8189)."
