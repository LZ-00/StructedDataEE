#!/usr/bin/env bash
# 启动前端开发服务器（监听 0.0.0.0:3000）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${SDWEB_FRONTEND_PORT:-3000}"
API_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:8000}"

die() {
  echo "错误: $*" >&2
  exit 1
}

if command -v ss >/dev/null 2>&1; then
  if ss -tln | grep -q ":${PORT} "; then
    echo "警告: 端口 ${PORT} 已被占用，Vite 将尝试其他端口（strictPort=false）" >&2
  fi
fi

if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
  echo "未找到 node_modules，正在安装前端依赖…" >&2
  npm install --prefix "$ROOT/frontend"
fi

export VITE_API_PROXY_TARGET="$API_TARGET"
cd "$ROOT/frontend"

echo "----------------------------------------"
echo "前端启动后请用下列地址之一访问："
echo "  在服务器本机浏览器:  http://127.0.0.1:${PORT}/"
if command -v hostname >/dev/null 2>&1; then
  for ip in $(hostname -I 2>/dev/null); do
  [[ "$ip" =~ ^127\. ]] && continue
  echo "  局域网其他电脑:      http://${ip}:${PORT}/"
  done
fi
echo "  若你在自己电脑浏览器打开 127.0.0.1:${PORT} 出现 ERR_CONNECTION_REFUSED，"
echo "  说明需先在 Cursor/VS Code「端口」面板转发 ${PORT}，或改用上面的局域网 IP。"
echo "  后端 API 代理目标: ${API_TARGET}"
echo "----------------------------------------"

exec npm run dev
