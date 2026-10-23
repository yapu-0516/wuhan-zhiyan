"""WebSocket 广播中心。

消息格式 {"type", "data", "ts"}（docs/api.md §9）。publish() 线程安全：AI 任务线程、同步路由处理函数
均可调用，消息被调度到事件循环中统一发送；单个客户端发送失败或超时即被移除，不影响其他客户端。
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

from fastapi import WebSocket

from .. import timeutil

log = logging.getLogger("cityeye.ws")


def envelope(msg_type: str, data: Any) -> str:
    return json.dumps({"type": msg_type, "data": data, "ts": timeutil.fmt(timeutil.now())}, ensure_ascii=False)


class RealtimeHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: int | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop | None) -> None:
        self._loop = loop
        self._loop_thread = threading.get_ident() if loop else None

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, msg_type: str, data: Any) -> None:
        if not self._clients:
            return
        text = envelope(msg_type, data)
        clients = list(self._clients)
        results = await asyncio.gather(*(asyncio.wait_for(c.send_text(text), timeout=5) for c in clients), return_exceptions=True)
        for c, r in zip(clients, results):
            if isinstance(r, BaseException):
                self._clients.discard(c)

    def publish(self, msg_type: str, data: Any) -> None:
        """从任意线程推送消息；无事件循环（如离线脚本）或无客户端时直接忽略。"""
        loop = self._loop
        if loop is None or loop.is_closed() or not self._clients:
            return
        if threading.get_ident() == self._loop_thread:
            loop.create_task(self.broadcast(msg_type, data))
        else:
            try:
                asyncio.run_coroutine_threadsafe(self.broadcast(msg_type, data), loop)
            except RuntimeError:  # 事件循环已停止
                log.debug("事件循环已停止，丢弃消息 %s", msg_type)
