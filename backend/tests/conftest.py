"""后端测试夹具：临时 SQLite + 临时文件目录，关闭模拟器与进度节奏，整个测试会话共享一个已播种的应用。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def tmp_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("cityeye")
    dist = root / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>CityEye</title><div id=app></div>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    return root


@pytest.fixture(scope="session")
def client(tmp_root: Path):
    settings = Settings(
        db_url=f"sqlite:///{tmp_root / 'test.db'}",
        simulator=False,
        task_pacing=0.0,
        files_dir=tmp_root / "files",
        frontend_dist=tmp_root / "dist",
    )
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture(scope="session")
def ctx(client: TestClient):
    return client.app.state.ctx


def wait_task(client: TestClient, task_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        t = client.get(f"/api/tasks/{task_id}").json()
        if t["status"] in ("done", "failed"):
            return t
        time.sleep(0.1)
    raise AssertionError(f"任务 {task_id} 超时未完成")
