#!/usr/bin/env bash
# Start an isolated ComfyUI instance for this repo (default port :8189).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -z "${COMFYUI_INSTALL:-}" ]]; then
  echo "Set COMFYUI_INSTALL to your ComfyUI install path, e.g.:" >&2
  echo "  export COMFYUI_INSTALL=/path/to/ComfyUI" >&2
  exit 1
fi
COMFY_ROOT="$COMFYUI_INSTALL"
RUNTIME="${REPO_ROOT}/comfy_runtime"
PORT="${COMFYUI_PORT:-8189}"
LOG_DIR="${REPO_ROOT}/logs"
PID_FILE="${LOG_DIR}/comfyui_${PORT}.pid"
STAMP="$(TZ=Asia/Seoul date +%Y%m%d_%H%M)"
LOG_FILE="${LOG_DIR}/${STAMP}_comfyui_${PORT}.log"

if [[ ! -d "$COMFY_ROOT" ]]; then
  echo "ComfyUI install not found: $COMFY_ROOT" >&2
  exit 1
fi

mkdir -p "$RUNTIME"/{input,output,temp,user} "$LOG_DIR"
ln -sfn "${COMFY_ROOT}/models" "${RUNTIME}/models"
ln -sfn "${COMFY_ROOT}/custom_nodes" "${RUNTIME}/custom_nodes"

# Install UI workflows + mirror media into this runtime (ComfyUI sidebar/assets).
bash "${REPO_ROOT}/scripts/sync_comfyui_ui.sh"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" || true)"
  if [[ -n "${old_pid}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "Already running pid=$old_pid port=$PORT (pidfile=$PID_FILE)"
    exit 0
  fi
fi

if curl -s -o /dev/null -w '' --connect-timeout 1 "http://127.0.0.1:${PORT}/" 2>/dev/null; then
  code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 1 "http://127.0.0.1:${PORT}/" || true)"
  if [[ "$code" == "200" ]]; then
    echo "Port $PORT already serves HTTP 200; not starting another process."
    exit 0
  fi
fi

cd "$COMFY_ROOT"
# shellcheck disable=SC1091
. .venv/bin/activate

nohup python main.py \
  --listen 127.0.0.1 \
  --port "$PORT" \
  --base-directory "$RUNTIME" \
  --enable-assets \
  --enable-asset-hashing \
  >"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
echo "started pid=$(cat "$PID_FILE") port=$PORT base=$RUNTIME log=$LOG_FILE"
echo "Point COMFYUI_BASE_URL=http://127.0.0.1:${PORT} in .env"
