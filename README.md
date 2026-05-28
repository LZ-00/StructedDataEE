# 激光焊接结构化数据抽取与质量评估系统

前后端分离的单仓结构：`frontend`（Vue 3 + Vite）与 `backend`（FastAPI）。

## 目录结构

```
SDWEB_Welding/
├── frontend/          # 前端 UI、路由、可视化
├── backend/           # 业务 API：登录、抽取、评估、蒸馏、微调
├── README.md
├── DEVELOPMENT.md     # 开发与启动命令说明（详见此文）
└── PROJECT_STRUCTURE.md
```

## 快速启动

完整说明（首次安装、多种启动方式、端口与验证）见 **[DEVELOPMENT.md](./DEVELOPMENT.md)**。

日常开发在**两个终端**分别执行：

```bash
# 终端 1：后端（8000）
npm run dev:backend

# 终端 2：前端（3000，/api 代理到后端）
npm run dev:frontend
```

浏览器访问 http://localhost:3000 ，默认账号：**root** / **123456**。

## Docker 部署（离线可用）

项目已提供 Docker Compose 双服务部署：
- `frontend`：Nginx 托管前端静态资源，并反向代理 `/api` 到后端。
- `backend`：FastAPI 服务，镜像构建阶段预打包 `BAAI/bge-m3` 权重，离线运行可直接使用语义分块能力。

### 1) 构建并启动（CPU）

```bash
docker compose up -d --build
```

访问地址：
- 前端：`http://<host>:3000`
- 后端健康检查：`http://<host>:8000/api/health`

### 2) 启用 GPU（可选）

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

要求宿主机已安装 NVIDIA 驱动与 nvidia-container-toolkit。

### 3) 离线交付（镜像导出/导入）

在可联网构建机执行：

```bash
docker compose build
docker save -o sdweb-backend.tar sdweb/backend:latest
docker save -o sdweb-frontend.tar sdweb/frontend:latest
```

在离线目标机执行：

```bash
docker load -i sdweb-backend.tar
docker load -i sdweb-frontend.tar
docker compose up -d
```

## API 概览

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | `POST /api/auth/login` | JWT 登录 |
| 抽取 | `POST /api/extraction/extract`、`/extract-text` | 结构化抽取 |
| 评估 | `POST /api/evaluation/evaluate` | 质量评估 + CoT 日志 |
| 蒸馏 | `POST /api/distillation/generate-dataset` | 思维链蒸馏数据构建 |
| 微调 | `POST /api/finetune/run`、`/publish` | LoRA 微调与发布 |
| 配置 | `GET /api/extraction/options`、`/evaluation/options`、`/distillation/options`、`/finetune/options` | 各页面下拉与默认值 |

业务实现位于 `backend/app/services/`，可按需替换为真实模型与数据库。

## 环境变量（可选）

在 `backend/.env` 中配置：

```
SECRET_KEY=your-production-secret
DEFAULT_USERNAME=root
DEFAULT_PASSWORD=123456
```
