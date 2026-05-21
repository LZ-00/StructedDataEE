# 开发与启动说明

本文档记录本项目的**前后端启动命令**及常用访问地址。开发时需同时运行后端与前端（两个终端）。

## 环境要求

| 组件 | 要求 |
|------|------|
| 后端 | Python 3.9+ |
| 前端 | Node.js 18+、npm |

## 首次安装（仅需一次）

### 后端依赖

```bash
cd backend
python3 -m venv .venv
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

等价于：

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**方式二：进入 backend 目录手动启动**

```bash
cd backend
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**注意：** 修改 `backend/app/` 下代码后，必须使用带 `--reload` 的方式启动（方式一或方式二）。若用无热重载方式启动，新增 API（如 `GET /api/dashboard/charts`）不会生效，前端会出现 **404** 并提示「仪表盘数据加载失败」。

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
| 访问地址 | http://localhost:3000 |
| API 代理 | 开发环境下 `/api` 代理至 `http://127.0.0.1:8000`（见 `frontend/vite.config.ts`） |
| 默认账号 | **root** / **123456** |

---

## 根目录 npm 脚本一览

在仓库根目录 `package.json` 中已配置：

| 命令 | 说明 |
|------|------|
| `npm run dev:backend` | 启动后端（uvicorn，8000，带 `--reload`） |
| `npm run dev:frontend` | 启动前端开发服务器（3000） |
| `npm run build:frontend` | 构建前端生产包 |

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
2. **3000 端口被占用**：Vite 会自动尝试其他端口，或使用 `npm run dev -- --port 3001` 指定端口。
3. **未创建虚拟环境**：先执行上文「首次安装 → 后端依赖」中的 `venv` 与 `pip install` 步骤。
