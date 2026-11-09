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
from sqlalchemy import Engine
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
