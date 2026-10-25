"""在仓库根目录运行：python -m backend [--host 127.0.0.1] [--port 8000] [--reload]"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description="城市智眼 CityEye 后端")
    ap.add_argument("--host", default=os.getenv("CITYEYE_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("CITYEYE_PORT", "8000")))
    ap.add_argument("--reload", action="store_true", help="开发模式：代码变更自动重载")
    args = ap.parse_args()
    sys.path.insert(0, str(BACKEND_DIR))
    os.chdir(BACKEND_DIR)
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload, app_dir=str(BACKEND_DIR))


if __name__ == "__main__":
    main()
