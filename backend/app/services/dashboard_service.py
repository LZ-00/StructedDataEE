"""仪表盘汇总统计与图表数据（可由任务队列、数据库聚合替换）。"""

from __future__ import annotations

from typing import Any

from app.config import model_catalog as catalog

_STAT_CARDS: list[dict[str, str]] = [
    {"key": "total_extractions", "title": "总抽取任务数"},
    {"key": "evaluations_done", "title": "评估完成数"},
    {"key": "avg_accuracy_percent", "title": "评估平均准确率"},
    {"key": "model_count", "title": "模型数量"},
]


def get_dashboard_stats() -> dict[str, Any]:
    return {
        "total_extractions": 26,
        "evaluations_done": 15,
        "avg_accuracy_percent": "79.8%",
        "model_count": catalog.model_count_for_dashboard(),
    }


def get_stat_cards() -> list[dict[str, str]]:
    """统计卡片元数据（标题与数据键），数值由 stats 接口填充。"""
    return list(_STAT_CARDS)


def get_dashboard_charts() -> dict[str, Any]:
    metrics = catalog.DASHBOARD_MODEL_METRICS
    models = [m["name"] for m in metrics]
    return {
        "exact_match": {
            "models": models,
            "values": [m["exact_match"] for m in metrics],
        },
        "rmse": {
            "models": models,
            "values": [m["rmse"] for m in metrics],
        },
    }
