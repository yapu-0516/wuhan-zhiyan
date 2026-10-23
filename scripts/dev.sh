#!/usr/bin/env bash
# 开发模式：同时启动 FastAPI 后端（:8000，热重载）与 Vite 前端（:5173，代理 /api 与 /files）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "▶ 后端  http://127.0.0.1:8000  (Swagger: /docs)"
(cd "$ROOT" && "$PY" -m backend --reload) &

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  (cd "$ROOT/frontend" && npm ci --no-audit --no-fund)
fi
echo "▶ 前端  http://127.0.0.1:5173"
(cd "$ROOT/frontend" && npm run dev) &

wait
