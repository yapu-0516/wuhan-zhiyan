#!/usr/bin/env bash
# 演示模式：构建前端后由后端单端口托管，适合路演 / 比赛现场
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"

"$PY" -c "import fastapi, numpy, PIL" 2>/dev/null || "$PY" -m pip install -r "$ROOT/backend/requirements.txt"
if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  (cd "$ROOT/frontend" && { [ -d node_modules ] || npm ci --no-audit --no-fund; } && npm run build)
fi
echo "▶ 城市之眼已启动：http://127.0.0.1:8000"
cd "$ROOT" && exec "$PY" -m backend --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
