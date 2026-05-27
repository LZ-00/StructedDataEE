"""项目统一时区工具（Asia/Shanghai）。"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

ASIA_SHANGHAI = ZoneInfo("Asia/Shanghai")


def now_asia_shanghai() -> datetime:
    return datetime.now(ASIA_SHANGHAI)


def iso_now_asia_shanghai() -> str:
    return now_asia_shanghai().isoformat()


def time_now_asia_shanghai() -> str:
    return now_asia_shanghai().strftime("%H:%M:%S")


def slug_now_asia_shanghai() -> str:
    return now_asia_shanghai().strftime("%Y%m%d_%H%M%S")
