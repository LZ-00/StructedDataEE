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

## API 概览

| 模块 | 路径前缀 | 说明 |
|------|----------|------|
| 认证 | `POST /api/auth/login` | JWT 登录 |
| 抽取 | `POST /api/extraction/extract`、`/extract-text` | 结构化抽取 |
| 评估 | `POST /api/evaluation/evaluate` | 质量评估 + CoT 日志 |
| 蒸馏 | `POST /api/distillation/generate-dataset` | 思维链蒸馏数据构建 |
| 微调 | `POST /api/finetune/run`、`/publish` | LoRA 微调与发布 |
| 仪表盘 | `GET /api/dashboard/stats`、`/stat-cards`、`/charts` | 汇总统计与图表数据 |
| 配置 | `GET /api/extraction/options`、`/evaluation/options`、`/distillation/options`、`/finetune/options` | 各页面下拉与默认值 |

业务实现位于 `backend/app/services/`，可按需替换为真实模型与数据库。

## 环境变量（可选）

在 `backend/.env` 中配置：

```
SECRET_KEY=your-production-secret
DEFAULT_USERNAME=root
DEFAULT_PASSWORD=123456
```
