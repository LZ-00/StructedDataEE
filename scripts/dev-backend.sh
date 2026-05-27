#!/usr/bin/env bash
# 使用 conda 环境（默认 lz-HV-FT，含 torch / modelscope）启动后端
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
PORT="${SDWEB_BACKEND_PORT:-8000}"
CONDA_ENV="${SDWEB_CONDA_ENV:-lz-HV-FT}"

die() {
  echo "错误: $*" >&2
  exit 1
}

resolve_python() {
  if [[ -n "${SDWEB_PYTHON:-}" && -x "${SDWEB_PYTHON}" ]]; then
    echo "${SDWEB_PYTHON}"
    return 0
  fi

  if command -v conda >/dev/null 2>&1; then
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
    for env_name in "$CONDA_ENV" lz-HV-FT lz-FT; do
      if conda env list | awk '{print $1}' | grep -qx "$env_name"; then
        conda activate "$env_name"
        command -v python
        return 0
      fi
    done
  fi

  local venv_py="$BACKEND/.venv/bin/python"
  if [[ -x "$venv_py" ]]; then
    echo "$venv_py"
    return 0
  fi

  if [[ -f "$venv_py" ]]; then
    die "backend/.venv/bin/python 无执行权限。请执行: chmod +x $BACKEND/.venv/bin/python* 或按 DEVELOPMENT.md 重建虚拟环境"
  fi

  die "未找到可用 Python 环境。请安装 conda 环境 lz-HV-FT/lz-FT，或创建 backend/.venv"
}

if command -v ss >/dev/null 2>&1; then
  if ss -tln | grep -q ":${PORT} "; then
    die "端口 ${PORT} 已被占用。请先停止旧进程: pkill -f 'uvicorn app.main:app' 或 export SDWEB_BACKEND_PORT=8001"
  fi
fi

PYTHON="$(resolve_python)"
echo "使用 Python: $PYTHON"
cd "$BACKEND"

"$PYTHON" -c "from app.main import app" 2>/dev/null || {
  echo "正在检查/安装后端依赖…" >&2
  "$PYTHON" -m pip install -q -r requirements.txt || die "依赖安装失败，请手动: pip install -r backend/requirements.txt"
  "$PYTHON" -c "from app.main import app" || die "应用导入失败，请查看上方 Python 报错"
}

"$PYTHON" -c "
from app.services.extraction.embedding_loader import check_embedding_runtime
check_embedding_runtime()
print('BGE-M3 embedding 依赖检查通过')
" 2>/dev/null || {
  echo "警告: BGE-M3 语义分块依赖未就绪，将回退为段落分块。" >&2
  echo "  修复: pip install 'torch>=2.6,<2.7' 'torchvision>=0.21,<0.22' 'transformers>=4.40,<5'" >&2
}

exec "$PYTHON" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
