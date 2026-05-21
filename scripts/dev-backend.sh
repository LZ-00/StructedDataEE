#!/usr/bin/env bash
# 使用 lz-HV-FT（含 torch / modelscope）启动后端，避免误用 backend/.venv
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONDA_ENV="${SDWEB_CONDA_ENV:-lz-HV-FT}"

if command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "$CONDA_ENV"
else
  echo "未找到 conda，请设置 SDWEB_CONDA_ENV 对应的 Python 路径" >&2
  exit 1
fi

cd "$ROOT/backend"
exec python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
