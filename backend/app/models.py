"""ORM 模型（与 database/schema.sql 保持一致）。

时间字段均为东八区本地时间（naive datetime）。道路实时路况保存在内存（services/traffic.py），不落库。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Event(Base):
    """城市事件（火灾 / 交通拥堵 / 建筑异常 / 内涝积水）。"""

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # E0001
    event_type: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(128))
    longitude: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)  # 发现时间
    severity: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[str] = mapped_column(String(16))
    district: Mapped[str] = mapped_column(String(32), default="")
    address: Mapped[str] = mapped_column(String(128), default="")
    grid: Mapped[str] = mapped_column(String(16), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    building_id: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    road_id: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    evidence_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    assignee: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)  # 入库时间
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    logs: Mapped[list["EventLog"]] = relationship(
        back_populates="event", cascade="all, delete-orphan", order_by="EventLog.timestamp"
    )


class EventLog(Base):
    """事件处置日志：created / status_changed / assigned / comment / ai_detected。"""

    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(16))
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    operator: Mapped[str] = mapped_column(String(64), default="系统")
    note: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)

    event: Mapped[Event] = relationship(back_populates="logs")


class DataAsset(Base):
    """数据资产目录（遥感 / 无人机 / 视频 / 三维 / 传感器 / 矢量）。"""

    __tablename__ = "data_assets"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # D0001
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(16), index=True)
    time: Mapped[datetime] = mapped_column(DateTime, index=True)  # 获取时间
    status: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(64), default="")
    format: Mapped[str] = mapped_column(String(32), default="")
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    records: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Task(Base):
    """AI 分析任务。inputs / algorithm / result 以 JSON 保存，结构见 docs/api.md §6。"""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # T0001
    type: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)  # pending | running | done | failed
    origin: Mapped[str] = mapped_column(String(16), default="user")  # user | upload | demo | seed
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String(32), default="排队中")
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    inputs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    algorithm: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    sample_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    create_event: Mapped[bool] = mapped_column(Boolean, default=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class SettlementSeries(Base):
    """接入沉降监测的建筑：位移时序 + 由 SettleWatch 算法计算的评估结果。"""

    __tablename__ = "settlement_series"

    building_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    series: Mapped[list[dict[str, Any]]] = mapped_column(JSON)  # [{date, displacement_mm}]
    rate_mm_per_month: Mapped[float] = mapped_column(Float)
    acceleration: Mapped[float] = mapped_column(Float)
    cumulative_mm: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16), index=True)
    analysis: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class Source(Base):
    """监测数据源（基线配置；实时吞吐由模拟器在内存中刷新）。"""

    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # S-DRONE
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16))
    icon: Mapped[str] = mapped_column(String(8))
    desc: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(8))
    devices_online: Mapped[int] = mapped_column(Integer)
    devices_total: Mapped[int] = mapped_column(Integer)
    throughput: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    coverage: Mapped[str] = mapped_column(String(64))
    last_active: Mapped[datetime] = mapped_column(DateTime)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class AppMeta(Base):
    """键值元数据（种子版本、种子时间等）。"""

    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
