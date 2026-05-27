"""语义分块 embedding 模型配置。"""

from __future__ import annotations

# ModelScope 模型 ID
DEFAULT_EMBEDDING_MODEL_ID = "BAAI/bge-m3"

# 权重统一存放目录（用户指定）
DEFAULT_EMBEDDING_CACHE_DIR = "/data/lz/modelscope/embedding"

# 科研论文分块 token 范围
DEFAULT_MIN_CHUNK_TOKENS = 800
DEFAULT_MAX_CHUNK_TOKENS = 1200

# 相邻片段余弦相似度低于该阈值时断开分块
DEFAULT_SIMILARITY_THRESHOLD = 0.55

# 相似度相对骤降（与上一对相比下降超过该值时也断开）
DEFAULT_SIMILARITY_DROP_DELTA = 0.15
