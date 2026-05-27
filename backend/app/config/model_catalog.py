"""
系统模型与演示指标的统一配置。

各业务模块通过 model_config_service 读取本文件中的定义；
修改可用模型、默认选型或仪表盘基准数据时，仅需维护此文件。
"""

from __future__ import annotations

from typing import Any, Literal, Optional

ModelType = Literal["api", "local"]
ModelUsage = Literal["extraction", "evaluation", "finetune", "distillation_teacher"]

# ---------------------------------------------------------------------------
# 基础设施
# ---------------------------------------------------------------------------

DEFAULT_LOCAL_BASE_DIR = "/data/lz/modelscope"

# ---------------------------------------------------------------------------
# 模型注册表种子（写入 models_registry.json 的初始条目，不含时间戳）
# ---------------------------------------------------------------------------

REGISTRY_SEED_MODELS: list[dict[str, Any]] = [
    {
        "id": "local-qwen-7b",
        "name": "Qwen2.5-7B-Instruct",
        "type": "local",
        "enabled": True,
        "description": "ModelScope 本地权重，激光焊接关系抽取主模型",
        "local_config": {
            "model_id": "Qwen/Qwen2.5-7B-Instruct",
            "base_dir": DEFAULT_LOCAL_BASE_DIR,
            "local_path": "",
        },
        "api_config": None,
    },
    {
        "id": "local-qwen-3b",
        "name": "Qwen2.5-3B-Instruct",
        "type": "local",
        "enabled": True,
        "description": "轻量级本地 instruct 模型",
        "local_config": {
            "model_id": "Qwen/Qwen2.5-3B-Instruct",
            "base_dir": DEFAULT_LOCAL_BASE_DIR,
            "local_path": "",
        },
        "api_config": None,
    },
    {
        "id": "local-llama-8b",
        "name": "Llama-3.1-8B-Instruct",
        "type": "local",
        "enabled": True,
        "description": "Meta Llama 3.1 8B 本地部署",
        "local_config": {
            "model_id": "LLM-Research/Meta-Llama-3.1-8B-Instruct",
            "base_dir": DEFAULT_LOCAL_BASE_DIR,
            "local_path": "",
        },
        "api_config": None,
    },
    {
        "id": "api-gpt4o",
        "name": "GPT-4o",
        "type": "api",
        "enabled": True,
        "description": "OpenAI 兼容 API，适用于蒸馏教师模型",
        "api_config": {
            "base_url": "",
            "api_key": "",
            "model_id": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "local_config": None,
    },
    {
        "id": "api-claude-sonnet",
        "name": "Claude-3.5-Sonnet",
        "type": "api",
        "enabled": True,
        "description": "Anthropic Claude API 教师模型",
        "api_config": {
            "base_url": "",
            "api_key": "",
            "model_id": "claude-3-5-sonnet-20241022",
            "temperature": 0.7,
            "max_tokens": 4096,
        },
        "local_config": None,
    },
]

# ---------------------------------------------------------------------------
# 各模块默认模型（注册表 id；注册表为空时与下方 fallback 首项 value 一致）
# ---------------------------------------------------------------------------

DEFAULT_MODEL_ID: dict[ModelUsage, str] = {
    "extraction": "local-qwen-7b",
    "evaluation": "local-qwen-7b",
    "finetune": "local-qwen-7b",
    "distillation_teacher": "api-gpt4o",
}

# 注册表不可用时的下拉备选（label / value）
FALLBACK_SELECT_OPTIONS: dict[ModelUsage, list[dict[str, str]]] = {
    "extraction": [
        {"label": "Qwen2.5-7B-Instruct", "value": "local-qwen-7b"},
        {"label": "Qwen2.5-3B-Instruct", "value": "local-qwen-3b"},
    ],
    "evaluation": [
        {"label": "Qwen2.5-7B-Instruct-CoT", "value": "local-qwen-7b"},
        {"label": "Llama-3.1-8B-Instruct-CoT", "value": "local-llama-8b"},
    ],
    "finetune": [
        {"label": "Qwen2.5-7B-Instruct", "value": "local-qwen-7b"},
        {"label": "Llama-3.1-8B-Instruct", "value": "local-llama-8b"},
    ],
    "distillation_teacher": [
        {"label": "GPT-4o", "value": "api-gpt4o"},
        {"label": "Claude-3.5-Sonnet", "value": "api-claude-sonnet"},
    ],
}

# 模型管理表单中的示例 ModelScope / API 标识
FORM_EXAMPLE_MODELSCOPE_IDS: list[str] = [
    "Qwen/Qwen2.5-7B-Instruct",
    "Qwen/Qwen2.5-3B-Instruct",
    "LLM-Research/Meta-Llama-3.1-8B-Instruct",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
]

FORM_EXAMPLE_API_MODEL_IDS: list[str] = [
    "deepseek-v4-flash",
    "deepseek-v4-pro",
    "kimi-k2.6",
    "glm-5.1",
]

# ---------------------------------------------------------------------------
# 模型检测（参考 DSE script/model_test.ipynb）
# ---------------------------------------------------------------------------

MODEL_TEST_USER_PROMPT = "Give me a short introduction to large language model."
MODEL_TEST_MAX_NEW_TOKENS = 64
MODEL_TEST_API_MAX_TOKENS = 64
# 写入注册表前 API 试连（较短，降低保存时延迟与费用）
MODEL_VALIDATE_API_MAX_TOKENS = 8

# ---------------------------------------------------------------------------
# 微调默认超参（modelName 为发布/展示用名称，非注册表 id）
# ---------------------------------------------------------------------------

FINETUNE_DEFAULTS: dict[str, Any] = {
    "loraRank": 64,
    "loraAlpha": 128,
    "loraDropout": 0.05,
    "epoch": 3,
    "batchSize": 1,
    "learningRate": "2e-5",
    "modelName": "Qwen2.5-7B-Instruct-CoT",
}

FINETUNE_LEARNING_RATES: list[str] = ["1e-5", "2e-5", "5e-5", "1e-4"]

# ---------------------------------------------------------------------------
# 仪表盘：模型基准评测（展示用短名称，与注册表 id 独立）
# ---------------------------------------------------------------------------

DASHBOARD_MODEL_METRICS: list[dict[str, Any]] = [
    {"name": "Qwen2.5-1.5B", "exact_match": 41.00, "rmse": 1.285},
    {"name": "Phi-3.5-mini", "exact_match": 56.10, "rmse": 0.896},
    {"name": "Qwen2.5-3B", "exact_match": 68.00, "rmse": 0.893},
    {"name": "Qwen2.5-7B", "exact_match": 79.80, "rmse": 0.414},
    {"name": "Llama-3.1-8B", "exact_match": 76.00, "rmse": 0.519},
    {"name": "DeepSeek-R1-Qwen-7B", "exact_match": 73.40, "rmse": 0.960},
    {"name": "DeepSeek-R1-Llama-8B", "exact_match": 74.30, "rmse": 0.987},
]


def fallback_select_options(
    usage: ModelUsage,
    *,
    types: Optional[list[ModelType]] = None,
) -> list[dict[str, str]]:
    """注册表为空或类型过滤无结果时，按业务场景返回备选模型列表。"""
    options = list(FALLBACK_SELECT_OPTIONS.get(usage, []))
    if not types:
        return options
    allowed = {m["id"] for m in REGISTRY_SEED_MODELS if m.get("type") in types}
    filtered = [o for o in options if o["value"] in allowed]
    return filtered or options


def resolve_default_model_id(usage: ModelUsage) -> str:
    """解析某业务场景的默认模型 id。"""
    configured = DEFAULT_MODEL_ID.get(usage, "")
    fallbacks = FALLBACK_SELECT_OPTIONS.get(usage, [])
    if configured:
        return configured
    if fallbacks:
        return fallbacks[0]["value"]
    return ""


def model_count_for_dashboard() -> int:
    """仪表盘「模型数量」统计：以基准评测模型数为准。"""
    return len(DASHBOARD_MODEL_METRICS)
