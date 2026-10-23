"""WebSocket 实时通道 /api/ws（docs/api.md §9）。"""
from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .. import timeutil

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    ctx = ws.app.state.ctx
    hub = ctx.hub
    await hub.connect(ws)
    try:
        await ws.send_text(json.dumps({
            "type": "hello",
            "data": {"server_time": timeutil.fmt(timeutil.now()), "demo_mode": ctx.settings.demo_mode, "clients": hub.client_count},
            "ts": timeutil.fmt(timeutil.now()),
        }, ensure_ascii=False))
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("type") == "ping":
                await ws.send_text(json.dumps({"type": "pong", "ts": timeutil.fmt(timeutil.now())}))
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(ws)
