FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    EMBEDDING_CACHE_DIR=/data/lz/modelscope/embedding

ARG PRELOAD_EMBEDDING=true

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install -r /app/backend/requirements.txt

COPY backend /app/backend
COPY scripts /app/scripts

# 为离线部署预下载 BGE-M3 到镜像内。
RUN mkdir -p /data/lz/modelscope/embedding && \
    if [ "$PRELOAD_EMBEDDING" = "true" ]; then \
      python /app/scripts/download_embedding_model.py; \
    fi

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
