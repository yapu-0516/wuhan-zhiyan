"""应用上下文：一个进程内共享的配置、数据库、地理数据、实时通道、路况状态等。

挂在 app.state.ctx 上，路由通过依赖 get_ctx 获取；后台线程（AI 任务）也通过它访问数据库与推送通道。
"""
from __future__ import annotations

import json
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from fastapi import HTTPException, Request
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .db import Base, make_engine, make_session_factory
from .geo import GeoRepository
from .services.realtime import RealtimeHub
from .services.sources import SourceState
from .services.traffic import TrafficState

SAMPLE_FIELDS = ("id", "type", "name", "description", "kind", "thumbnail_url", "files", "longitude", "latitude")


class SampleRepository:
    """示例数据清单（data/samples/manifest.json）。"""

    def __init__(self, samples_dir: Path) -> None:
        self.dir = samples_dir
        p = samples_dir / "manifest.json"
        self.items: list[dict[str, Any]] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        self.by_id = {s["id"]: s for s in self.items}

    def public(self, s: dict[str, Any]) -> dict[str, Any]:
        return {k: s.get(k) for k in SAMPLE_FIELDS}

    def list(self, event_type: str | None = None) -> list[dict[str, Any]]:
        return [self.public(s) for s in self.items if not event_type or s["type"] == event_type]

    def paths(self, s: dict[str, Any]) -> list[Path]:
        return [self.dir / f.removeprefix("/files/samples/") for f in s["files"]]


@dataclass
class AppContext:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker
    geo: GeoRepository
    samples: SampleRepository
    hub: RealtimeHub
    traffic: TrafficState
    sources: SourceState
    executor: ThreadPoolExecutor
    id_lock: threading.Lock = field(default_factory=threading.Lock)
    started_at: float = field(default_factory=time.time)
    _buildings_cache: bytes | None = None
    _fine_buildings_cache: bytes | None = None
    _fine_district_cache: dict[str, bytes] = field(default_factory=dict)

    @classmethod
    def create(cls, settings: Settings) -> "AppContext":
        engine = make_engine(settings.db_url)
        geo = GeoRepository(settings.geo_dir)
        for sub in ("uploads", "results", "evidence"):
            (settings.files_dir / sub).mkdir(parents=True, exist_ok=True)
        return cls(
            settings=settings,
            engine=engine,
            session_factory=make_session_factory(engine),
            geo=geo,
            samples=SampleRepository(settings.samples_dir),
            hub=RealtimeHub(),
            traffic=TrafficState(geo),
            sources=SourceState(),
            executor=ThreadPoolExecutor(max_workers=2, thread_name_prefix="cityeye-task"),
        )

    # ------------------------------------------------------------------ 数据库
    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)
        self._migrate_data_asset_profile()
        self._migrate_audit_payload()

    def _migrate_data_asset_profile(self) -> None:
        """为旧数据库增量补充数据资源画像字段，不删除或重建已有数据。"""
        columns = {item["name"] for item in inspect(self.engine).get_columns("data_assets")}
        additions = {
            "spatial_extent": "JSON NOT NULL DEFAULT '{}'",
            "time_start": "DATETIME",
            "time_end": "DATETIME",
            "crs": "VARCHAR(32) NOT NULL DEFAULT 'EPSG:4326'",
            "quality_score": "FLOAT NOT NULL DEFAULT 0",
            "quality_notes": "JSON NOT NULL DEFAULT '[]'",
            "version": "VARCHAR(32) NOT NULL DEFAULT ''",
            "analysis_status": "VARCHAR(16) NOT NULL DEFAULT 'unknown'",
        }
        missing = {name: ddl for name, ddl in additions.items() if name not in columns}
        with self.engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(text(f"ALTER TABLE data_assets ADD COLUMN {name} {ddl}"))
            extent = json.dumps(
                {"label": "武汉中心城区", "bbox": list(self.geo.region.get("bbox", []))},
                ensure_ascii=False,
            )
            notes = json.dumps(["旧数据已完成结构迁移，质量与时相口径待复核"], ensure_ascii=False)
            rows = conn.execute(
                text(
                    "SELECT id, type, status, time FROM data_assets "
                    "WHERE analysis_status = 'unknown'"
                )
            ).mappings().all()
            for row in rows:
                status = row["status"]
                analysis_status = "ready" if status == "已入库" else "pending" if status == "采集中" else "unavailable"
                quality_score = 88 if status == "已入库" else 72 if status == "采集中" else 0
                conn.execute(
                    text(
                        "UPDATE data_assets SET spatial_extent = :extent, "
                        "time_start = datetime(:time, :start_offset), "
                        "time_end = :time_end, version = substr(:time, 1, 10), "
                        "quality_score = :quality_score, quality_notes = :notes, "
                        "analysis_status = :analysis_status WHERE id = :id"
                    ),
                    {
                        "id": row["id"],
                        "time": row["time"],
                        "start_offset": "-365 day" if row["type"] in ("矢量数据", "三维模型") else "-1 day",
                        "time_end": None if row["type"] == "视频流" else row["time"],
                        "quality_score": quality_score,
                        "extent": extent,
                        "notes": notes,
                        "analysis_status": analysis_status,
                    },
                )

    def _migrate_audit_payload(self) -> None:
        """为旧审计表补充修改前后值，保留既有审计记录。"""
        columns = {item["name"] for item in inspect(self.engine).get_columns("audit_logs")}
        additions = {
            "before_data": "JSON NOT NULL DEFAULT '{}'",
            "after_data": "JSON NOT NULL DEFAULT '{}'",
        }
        with self.engine.begin() as conn:
            for name, ddl in additions.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {name} {ddl}"))

    @contextmanager
    def session(self) -> Iterator[Session]:
        s = self.session_factory()
        try:
            yield s
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    # ------------------------------------------------------------------ 文件
    @property
    def results_dir(self) -> Path:
        return self.settings.files_dir / "results"

    @property
    def evidence_dir(self) -> Path:
        return self.settings.files_dir / "evidence"

    @property
    def uploads_dir(self) -> Path:
        return self.settings.files_dir / "uploads"

    def url_for(self, path: Path) -> str:
        """磁盘路径 → /files/... 访问地址。"""
        path = path.resolve()
        for base, prefix in ((self.settings.samples_dir.resolve(), "/files/samples/"), (self.settings.files_dir.resolve(), "/files/")):
            try:
                return prefix + path.relative_to(base).as_posix()
            except ValueError:
                continue
        raise ValueError(f"文件不在可访问目录内：{path}")

    def path_for(self, url: str) -> Path | None:
        """/files/... 访问地址 → 磁盘路径（不存在返回 None）。"""
        if url.startswith("/files/samples/"):
            p = self.settings.samples_dir / url.removeprefix("/files/samples/")
        elif url.startswith("/files/"):
            p = self.settings.files_dir / url.removeprefix("/files/")
        else:
            return None
        return p if p.exists() else None

    def copy_evidence(self, src: Path, name: str) -> str:
        dst = self.evidence_dir / f"{name}{src.suffix.lower()}"
        shutil.copyfile(src, dst)
        return self.url_for(dst)

    def clear_generated_files(self) -> None:
        for sub in ("uploads", "results", "evidence"):
            d = self.settings.files_dir / sub
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ 缓存
    def invalidate_buildings(self) -> None:
        self._buildings_cache = None

    def reload_geo(self) -> None:
        """空间底图文件修改后重建内存索引和实时路况对象。"""
        from .geo import GeoRepository
        from .services.traffic import TrafficState

        self.geo = GeoRepository(self.settings.geo_dir)
        self.traffic = TrafficState(self.geo)
        self.invalidate_buildings()

    def buildings_json(self) -> bytes:
        if self._buildings_cache is None:
            self._buildings_cache = json.dumps(self.geo.buildings_geojson(), ensure_ascii=False, separators=(",", ":")).encode()
        return self._buildings_cache

    @property
    def fine_district_dir(self) -> Path:
        return self.settings.fine_buildings_path.parent / "districts"

    def fine_building_manifest(self) -> dict[str, Any]:
        path = self.fine_district_dir / "manifest.json"
        if not path.exists():
            return {"districts": []}
        return json.loads(path.read_text(encoding="utf-8"))

    def fine_buildings_json(self, district: str | None = None) -> bytes:
        if district:
            if district not in self._fine_district_cache:
                item = next((d for d in self.fine_building_manifest().get("districts", []) if d.get("name") == district), None)
                if item is None:
                    raise FileNotFoundError(district)
                path = self.fine_district_dir / f"{item['prefix']}.geojson"
                if not path.exists():
                    raise FileNotFoundError(path)
                self._fine_district_cache[district] = path.read_bytes()
            return self._fine_district_cache[district]
        if self._fine_buildings_cache is None:
            path = self.settings.fine_buildings_path
            if not path.exists():
                raise FileNotFoundError(path)
            self._fine_buildings_cache = path.read_bytes()
        return self._fine_buildings_cache


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def not_found(msg: str) -> HTTPException:
    return HTTPException(status_code=404, detail=msg)


def bad_request(msg: str) -> HTTPException:
    return HTTPException(status_code=400, detail=msg)
