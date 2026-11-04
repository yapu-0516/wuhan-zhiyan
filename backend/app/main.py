"""城市智眼 CityEye 后端入口。

    cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
    # 或在仓库根目录：python -m backend

- /api/**     REST 接口与 WebSocket（/api/ws），契约见 docs/api.md；交互式文档 /docs
- /files/**   上传文件、算法结果与证据图（backend/var/files），/files/samples/** 为示例数据（data/samples）
- /           若存在 frontend/dist 则托管前端，并对非 /api、/files 的 GET 请求回退到 index.html（SPA）
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import cityeye_algo as ca
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import seed
from .config import APP_NAME, APP_VERSION, Settings
from .context import AppContext
from .routers import data, demo, events, geo, llm, scenario, stats, system, tasks, ws
from .services.simulator import Simulator

log = logging.getLogger("cityeye")

_HTTP_CN = {"Not Found": "资源不存在", "Method Not Allowed": "不支持的请求方法"}
_VALIDATION_CN = {
    "missing": "缺少必填字段",
    "literal_error": "取值不合法",
    "enum": "取值不合法",
    "float_parsing": "必须是数字",
    "int_parsing": "必须是整数",
    "bool_parsing": "必须是布尔值",
    "string_too_short": "不能为空",
    "string_too_long": "长度超出限制",
    "greater_than_equal": "超出取值范围",
    "less_than_equal": "超出取值范围",
    "json_invalid": "JSON 格式错误",
    "model_attributes_type": "请求体格式错误",
}


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for err in exc.errors()[:5]:
        loc = ".".join(str(x) for x in err.get("loc", ()) if x not in ("body", "query", "path", "form"))
        reason = _VALIDATION_CN.get(err.get("type", ""), err.get("msg", "格式错误"))
        ctx = err.get("ctx") or {}
        if "expected" in ctx:
            reason += f"（可选 {ctx['expected']}）"
        parts.append(f"{loc or '请求'}：{reason}")
    return "请求参数校验失败：" + "；".join(parts)


def init_data(ctx: AppContext) -> None:
    """建表；首次启动或要求重置时生成种子数据，否则从数据库恢复内存态。"""
    ctx.create_schema()
    if ctx.settings.reset_on_start or not seed.is_seeded(ctx):
        seed.seed_database(ctx)
    else:
        seed.load_runtime_state(ctx)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    ctx = AppContext.create(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        ctx.hub.bind_loop(asyncio.get_running_loop())
        await asyncio.to_thread(init_data, ctx)
        sim = Simulator(ctx)
        app.state.simulator = sim
        sim.start()
        try:
            yield
        finally:
            await sim.stop()
            ctx.hub.bind_loop(None)
            ctx.executor.shutdown(wait=False, cancel_futures=True)
            ctx.engine.dispose()

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="武汉汉口沿江示范区城市智能监测数字孪生平台后端。接口契约见 docs/api.md。" "建筑 / 道路 / POI 数据 © OpenStreetMap contributors（ODbL）。",
        lifespan=lifespan,
    )
    app.state.ctx = ctx
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"],
                       allow_credentials="*" not in settings.cors_origins)

    @app.exception_handler(RequestValidationError)
    async def _on_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": _validation_message(exc)})

    @app.exception_handler(ca.InputError)
    async def _on_input(_: Request, exc: ca.InputError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(StarletteHTTPException)
    async def _on_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail: Any = _HTTP_CN.get(exc.detail, exc.detail) if isinstance(exc.detail, str) else exc.detail
        return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=getattr(exc, "headers", None))

    for r in (
        system.router,
        events.router,
        geo.router,
        stats.router,
        data.router,
        tasks.router,
        demo.router,
        ws.router,
        llm.router,
        scenario.router,
    ):
        app.include_router(r, prefix="/api")
    app.mount("/files/samples", StaticFiles(directory=settings.samples_dir, check_dir=False), name="samples")
    app.mount("/files", StaticFiles(directory=settings.files_dir, check_dir=False), name="files")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> Any:
        if full_path == "api" or full_path.startswith(("api/", "files/")):
            return JSONResponse(status_code=404, content={"detail": f"接口不存在：/{full_path}"})
        dist = settings.frontend_dist.resolve()
        index = dist / "index.html"
        if not index.exists():
            return JSONResponse(status_code=404, content={"detail": "前端尚未构建（frontend/dist 不存在），接口文档见 /docs", "name": APP_NAME})
        target = (dist / full_path).resolve()
        if full_path and target.is_file() and dist in target.parents:
            return FileResponse(target)
        return FileResponse(index)

    return app


def __getattr__(name: str) -> Any:
    """惰性创建模块级 app（供 `uvicorn app.main:app` 使用），避免测试导入时产生副作用。"""
    if name == "app":
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        globals()["app"] = application = create_app()
        return application
    raise AttributeError(name)
