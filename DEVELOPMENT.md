# 开发与启动说明

本文档记录本项目的**前后端启动命令**及常用访问地址。开发时需同时运行后端与前端（两个终端）。

## 环境要求

| 组件 | 要求 |
|------|------|
| 后端 | Python 3.9+ |
| 前端 | Node.js 18+、npm |

## 首次安装（仅需一次）

### 后端依赖

**推荐：使用 conda 环境 `lz-HV-FT`（含 torch / modelscope）**

```bash
conda activate lz-HV-FT   # 若无此环境，可用: export SDWEB_CONDA_ENV=lz-FT
cd backend
pip install -r requirements.txt
# 语义分块 embedding（可选，抽取工作台文件上传需要）
python ../scripts/download_embedding_model.py
```

**备选：Python 虚拟环境**

```bash
cd backend
python3 -m venv .venv
chmod +x .venv/bin/python*       # 若 .venv/bin/python 无执行权限需执行此行
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 前端依赖

```bash
cd frontend
npm install
```

或在项目根目录执行：

```bash
cd frontend && npm install
```

---

## 日常启动

在**两个终端**中分别执行后端与前端命令。

### 后端（FastAPI，端口 8000）

**方式一：项目根目录 npm 脚本（推荐）**

```bash
# 在仓库根目录 SDWEB_Welding/ 下执行
npm run dev:backend
```

等价于（自动选择 conda `lz-HV-FT` / `lz-FT`，或 `backend/.venv`）：

```bash
bash scripts/dev-backend.sh
```

指定环境或端口：

```bash
export SDWEB_CONDA_ENV=lz-FT
export SDWEB_BACKEND_PORT=8000
npm run dev:backend
```

**方式二：进入 backend 目录手动启动**

```bash
cd backend
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**注意：** 修改 `backend/app/` 下代码后，必须使用带 `--reload` 的方式启动（方式一或方式二）。若用无热重载方式启动，新增 API 可能不会生效。

**方式三：不启用热重载（仅生产或调试时使用）**

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

修改路由或服务代码后，需**手动重启**该进程。

| 项目 | 值 |
|------|-----|
| 服务地址 | http://127.0.0.1:8000 |
| API 文档 | http://127.0.0.1:8000/docs |
| 健康检查 | `GET http://127.0.0.1:8000/api/health` |

验证后端是否就绪：

```bash
curl http://127.0.0.1:8000/api/health
# 期望返回: {"status":"ok"}
```

### 前端（Vue 3 + Vite，端口 3000）

**方式一：项目根目录 npm 脚本（推荐）**

```bash
# 在仓库根目录 SDWEB_Welding/ 下执行
npm run dev:frontend
```

等价于在 `frontend` 目录执行 `npm run dev`。

**方式二：进入 frontend 目录启动**

```bash
cd frontend
npm run dev
```

**指定主机与端口（端口被占用时）**

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

| 项目 | 值 |
|------|-----|
| 访问地址（本机） | http://localhost:3000 或 http://127.0.0.1:3000 |
| 访问地址（局域网/远程浏览器） | 启动日志中的 `Network: http://<服务器IP>:3000/`（需 `host: 0.0.0.0`，已默认开启） |
| API 代理 | 开发环境下 `/api` 代理至 `http://127.0.0.1:8000`（见 `frontend/vite.config.ts`） |
| 默认账号 | **root** / **123456** |

**注意：** 若仅监听 `127.0.0.1`，在其他机器浏览器输入服务器 IP 会显示「无法访问」。请使用 `npm run dev:frontend`（已配置 `--host 0.0.0.0`）。

### 远程开发：浏览器报 `ERR_CONNECTION_REFUSED`（127.0.0.1:3000）

开发机跑在 Linux 服务器上、浏览器在你自己的电脑上时，`http://127.0.0.1:3000` 指向**你电脑本机**，不是服务器，因此会连接被拒绝。

任选一种方式：

1. **Cursor / VS Code 端口转发（推荐）**  
   - 先 `npm run dev:frontend`  
   - 打开「端口 / Ports」面板，确认 **3000** 已转发到本地  
   - 在本地浏览器访问 Cursor 提示的地址（多为 `http://127.0.0.1:3000`）

2. **局域网 IP**（与服务器同一网段）  
   - 看启动日志里的 `Network: http://172.x.x.x:3000/`  
   - 在本机浏览器访问该地址（不要用服务器的 127.0.0.1）

3. **SSH 隧道**（在本地终端执行）  
   ```bash
   ssh -L 3000:127.0.0.1:3000 用户名@服务器IP
   ```  
   然后本地浏览器打开 http://127.0.0.1:3000

---

## 根目录 npm 脚本一览

在仓库根目录 `package.json` 中已配置：

| 命令 | 说明 |
|------|------|
| `npm run dev:backend` | 启动后端（uvicorn，8000，带 `--reload`） |
| `npm run dev:frontend` | 启动前端开发服务器（3000） |
| `npm run build:frontend` | 构建前端生产包 |

---

## Docker 部署（统一环境）

适用于将项目部署到任意主机并保持一致运行环境（前端 + 后端）。

### CPU 默认部署

```bash
cd /path/to/code
docker compose up -d --build
```

访问：
- 前端：`http://<host>:3000`
- 后端健康检查：`http://<host>:8000/api/health`

### GPU 可选部署（NVIDIA）

```bash
cd /path/to/code
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

要求宿主机已安装 NVIDIA 驱动与 `nvidia-container-toolkit`。

### 离线部署说明（含 BGE-M3）

- `backend/Dockerfile` 在构建阶段会预下载并打包 `BAAI/bge-m3` 到 `/data/lz/modelscope/embedding`。
- 部署运行时无需访问外网即可加载 embedding 权重。

联网构建机导出镜像：

```bash
docker compose build
docker save -o sdweb-backend.tar sdweb/backend:latest
docker save -o sdweb-frontend.tar sdweb/frontend:latest
```

离线目标机导入并启动：

```bash
docker load -i sdweb-backend.tar
docker load -i sdweb-frontend.tar
docker compose up -d
```

### 常用运维命令

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
docker compose down -v
```

---

## 环境变量（可选）

在 `backend/.env` 中可配置：

```env
SECRET_KEY=your-production-secret
DEFAULT_USERNAME=root
DEFAULT_PASSWORD=123456
```

---

## 常见问题

1. **前端无法访问接口**：确认后端已在 8000 端口运行，且 `curl http://127.0.0.1:8000/api/health` 返回正常。
2. **后端启动报 `Address already in use`**：8000 端口被旧进程占用。执行 `pkill -f 'uvicorn app.main:app'` 后重试，或 `export SDWEB_BACKEND_PORT=8001`。
3. **conda 环境 `lz-HV-FT` 不存在**：`export SDWEB_CONDA_ENV=lz-FT` 后重新 `npm run dev:backend`；或安装 micromamba/conda 中的 `lz-HV-FT`。
4. **`.venv/bin/python: Permission denied`**：执行 `chmod +x backend/.venv/bin/python*` 或重建虚拟环境。
5. **前端页面无法打开 / 无法访问**：确认 Vite 日志中有 `Network: http://<IP>:3000/`；用 `ss -tln | grep 3000` 应看到 `0.0.0.0:3000` 而非仅 `127.0.0.1:3000`。重启：`pkill -f vite/bin/vite && npm run dev:frontend`。
6. **3000 端口被占用**：Vite 会自动尝试其他端口，或使用 `SDWEB_FRONTEND_PORT=3001 npm run dev:frontend`。
7. **抽取报「语义 embedding 不可用」**：在 `lz-HV-FT`/`lz-FT` 中安装 `sentence-transformers`，并运行 `python scripts/download_embedding_model.py` 下载 BGE-M3 至 `/data/lz/modelscope/embedding`。
8. **Docker GPU 不生效**：执行 `docker info | rg -i nvidia` 检查运行时；若缺失，请安装 `nvidia-container-toolkit` 并重启 Docker。
