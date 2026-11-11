"""导出前端离线快照：frontend/public/snapshot/

在进程内启动后端（全新临时数据库 + 种子数据，模拟器关闭），把前端可能请求的 GET 接口结果写成静态 JSON，
并复制这些 JSON 引用到的 /files/** 资源（算法证据图、任务结果、示例数据缩略图），保持 /files/ 之后的相对路径。
前端在后端不可达或 VITE_USE_MOCK=true 时读取这些快照（见 frontend/src/api/http.ts）。

用法（仓库根目录）：python scripts/export_snapshot.py [--out frontend/public/snapshot]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

FILE_URL = re.compile(r"/files/[^\s\"'?#]+")


def dump(path: Path, data: Any) -> int:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return len(text.encode())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "frontend" / "public" / "snapshot"))
    out = Path(ap.parse_args().out).resolve()
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="cityeye-snapshot-") as tmp:
        settings = Settings(db_url=f"sqlite:///{tmp}/snapshot.db", simulator=False, task_pacing=0.0,
                            files_dir=Path(tmp) / "files", frontend_dist=Path(tmp) / "no-dist")
        with TestClient(create_app(settings)) as c:
            ctx = c.app.state.ctx

            def get(path: str) -> Any:
                r = c.get(f"/api{path}")
                r.raise_for_status()
                return r.json()

            events = get("/events?limit=2000")
            payloads: dict[str, Any] = {
                "events.json": events,
                "event_logs.json": {e["id"]: get(f"/events/{e['id']}/logs") for e in events},
                "buildings.geojson": get("/buildings"),
                "roads.geojson": get("/roads"),
                "pois.json": get("/pois"),
                "stats_overview.json": get("/stats/overview"),
                "data.json": get("/data"),
                "data_stats.json": get("/data/stats"),
                "tasks.json": get("/tasks"),
                "samples.json": get("/samples"),
                "sources.json": get("/sources"),
                "system_info.json": get("/system/info"),
                "monitoring_tasks.json": get("/monitoring-tasks"),
                "task_templates.json": get("/task-templates"),
                "scenario_templates.json": get("/scenario/templates"),
                "monitoring_runs.json": get("/monitoring-runs"),
                "assessments.json": get("/assessments"),
                "work_orders.json": get("/work-orders"),
                "reviews.json": get("/reviews"),
                "accounts.json": get("/support/accounts"),
                "grids.json": get("/support/grids"),
                "emergency_resources.json": get("/support/emergency-resources"),
                "notifications.json": get("/support/notifications"),
                "audit.json": get("/support/audit"),
                "sla_summary.json": get("/support/sla-summary"),
                "traceability_graph.json": get("/traceability/graph"),
            }
            ids = {f["id"] for f in payloads["buildings.geojson"]["features"] if f["properties"]["monitored"]}
            ids |= {e["building_id"] for e in events if e.get("building_id")}
            payloads["building_details.json"] = {bid: get(f"/buildings/{bid}") for bid in sorted(ids)}

            sizes = {name: dump(out / name, data) for name, data in payloads.items()}

            urls = set()
            for data in payloads.values():
                urls |= set(FILE_URL.findall(json.dumps(data, ensure_ascii=False)))
            copied, missing = 0, []
            for url in sorted(urls):
                src = ctx.path_for(url)
                if src is None:
                    missing.append(url)
                    continue
                dst = out / "files" / url.removeprefix("/files/")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                sizes[f"files/{url.removeprefix('/files/')}"] = dst.stat().st_size
                copied += 1

    total = sum(sizes.values())
    for name in payloads:
        print(f"  {name:24s} {sizes[name] / 1024:8.1f} KB")
    print(f"复制资源文件 {copied} 个；快照合计 {total / 1e6:.2f} MB → {out}")
    if missing:
        print(f"警告：{len(missing)} 个引用文件不存在：{missing[:5]}")


if __name__ == "__main__":
    main()
