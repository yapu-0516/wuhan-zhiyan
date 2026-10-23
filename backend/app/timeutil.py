"""时间工具：系统统一使用东八区（Asia/Shanghai，无夏令时）本地时间，数据库存无时区的本地时间。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8), "Asia/Shanghai")


def now() -> datetime:
    """当前东八区本地时间（naive，精确到秒）。"""
    return datetime.now(CST).replace(tzinfo=None, microsecond=0)


def fmt(dt: datetime | None) -> str | None:
    """yyyy-MM-dd HH:mm:ss"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def fmt_minute(dt: datetime) -> str:
    """yyyy-MM-dd HH:mm（DataItem.time 兼容原型格式）"""
    return dt.strftime("%Y-%m-%d %H:%M")


def start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)
