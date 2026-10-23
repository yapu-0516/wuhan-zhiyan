"""运行配置：全部来自环境变量（前缀 CITYEYE_），带开发期默认值。"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
ALGORITHM_DIR = REPO_ROOT / "algorithm"

# 算法包以源码目录形式提供（无需安装），在此统一加入导入路径
if str(ALGORITHM_DIR) not in sys.path:
    sys.path.insert(0, str(ALGORITHM_DIR))

APP_NAME = "城市之眼 CityEye"
APP_VERSION = "1.0.0"


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    v = os.getenv(name)
    try:
        return float(v) if v not in (None, "") else default
    except ValueError:
        return default


def _path(name: str, default: Path) -> Path:
    v = os.getenv(name)
    return Path(v).expanduser().resolve() if v else default


@dataclass(frozen=True)
class Settings:
    db_url: str
    demo_mode: bool = True
    simulator: bool = True
    sim_interval: float = 45.0       # 巡检流水线（新事件）间隔，秒
    traffic_interval: float = 10.0   # 路况刷新间隔，秒
    sensor_interval: float = 5.0     # 数据源吞吐刷新间隔，秒
    heartbeat_interval: float = 20.0
    lifecycle_interval: float = 45.0  # 事件自动流转检查间隔，秒
    task_pacing: float = 0.6         # AI 任务每个阶段的最短展示时长（仅影响进度推送节奏，不影响结果）
    reset_on_start: bool = False
    frontend_dist: Path = REPO_ROOT / "frontend" / "dist"
    files_dir: Path = BACKEND_DIR / "var" / "files"
    samples_dir: Path = REPO_ROOT / "data" / "samples"
    geo_dir: Path = REPO_ROOT / "data" / "geo"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    max_upload_mb: float = 20.0

    @property
    def database_kind(self) -> str:
        return self.db_url.split(":", 1)[0].split("+", 1)[0]

    @classmethod
    def from_env(cls) -> "Settings":
        default_db = f"sqlite:///{(BACKEND_DIR / 'var' / 'cityeye.db').as_posix()}"
        origins = os.getenv("CITYEYE_CORS_ORIGINS", "*")
        return cls(
            db_url=os.getenv("CITYEYE_DB_URL") or default_db,
            demo_mode=_bool("CITYEYE_DEMO_MODE", True),
            simulator=_bool("CITYEYE_SIMULATOR", True),
            sim_interval=max(3.0, _float("CITYEYE_SIM_INTERVAL", 45.0)),
            traffic_interval=max(1.0, _float("CITYEYE_TRAFFIC_INTERVAL", 10.0)),
            sensor_interval=max(1.0, _float("CITYEYE_SENSOR_INTERVAL", 5.0)),
            task_pacing=max(0.0, _float("CITYEYE_TASK_PACING", 0.6)),
            reset_on_start=_bool("CITYEYE_RESET_ON_START", False),
            frontend_dist=_path("CITYEYE_FRONTEND_DIST", REPO_ROOT / "frontend" / "dist"),
            files_dir=_path("CITYEYE_FILES_DIR", BACKEND_DIR / "var" / "files"),
            samples_dir=_path("CITYEYE_SAMPLES_DIR", REPO_ROOT / "data" / "samples"),
            geo_dir=_path("CITYEYE_GEO_DIR", REPO_ROOT / "data" / "geo"),
            cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
            max_upload_mb=max(1.0, _float("CITYEYE_MAX_UPLOAD_MB", 20.0)),
        )
