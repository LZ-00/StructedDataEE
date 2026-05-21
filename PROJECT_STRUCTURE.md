# 项目目录结构说明

## 完整目录树

```
SDWEB/
├── index.html                    # HTML 入口文件
├── package.json                  # 项目依赖和脚本配置
├── tsconfig.json                 # TypeScript 编译配置
├── tsconfig.node.json            # Node 环境 TypeScript 配置
├── vite.config.ts                # Vite 构建工具配置
├── .gitignore                    # Git 忽略文件配置
├── README.md                     # 项目说明文档
├── PROJECT_STRUCTURE.md          # 项目结构说明（本文件）
│
└── src/                          # 源代码目录
    ├── main.ts                   # 应用入口文件
    ├── App.vue                   # 根组件（包含导航和布局）
    ├── vite-env.d.ts             # Vite 环境变量类型定义
    │
    ├── router/                   # 路由配置
    │   └── index.ts              # Vue Router 路由定义
    │
    ├── views/                    # 页面组件
    │   ├── Dashboard.vue         # 系统仪表盘页面
    │   ├── ExtractionWorkspace.vue # 智能抽取工作台页面
    │   └── EvaluationTracker.vue  # 思维链评估追踪室页面
    │
    ├── types/                    # TypeScript 类型定义
    │   └── index.ts              # 全局类型定义（Entity, Relation, ExtractionResult 等）
    │
    ├── utils/                    # 工具函数
    │   └── api.ts                # API 接口封装（Axios 配置和接口定义）
    │
    └── styles/                   # 样式文件
        └── index.css             # 全局样式和主题变量
```

## 核心文件说明

### 配置文件

- **package.json**: 定义项目依赖（Vue 3, Element Plus, ECharts, Axios 等）和 npm 脚本
- **tsconfig.json**: TypeScript 编译选项，配置路径别名 `@/*` 指向 `src/*`
- **vite.config.ts**: Vite 构建配置，设置开发服务器端口和路径别名

### 入口文件

- **index.html**: HTML 模板，挂载 Vue 应用
- **src/main.ts**: 应用入口，初始化 Vue 应用、注册 Element Plus 和路由

### 核心组件

#### App.vue
- 应用根组件
- 包含顶部导航栏和主内容区域
- 实现页面路由切换

#### Dashboard.vue
- **功能**: 系统全局统计和可视化
- **图表**:
  - 折线图：精确匹配率趋势（不同模型/参数规模）
  - 柱状图：RMSE 均方根误差对比
  - 雷达图：跨域迁移性能（铝合金 / 不锈钢焊接数据集）

#### ExtractionWorkspace.vue
- **功能**: 文献解析与结构化抽取
- **左侧区域**:
  - 文件上传组件（拖拽支持）
  - 原文预览区（支持实体高亮）
- **右侧区域**:
  - 结构化数据 JSON 展示
  - 一键导出功能

#### EvaluationTracker.vue
- **功能**: 自动化评估与思维链可视化
- **组件**:
  - 任务控制区（模型选择、基准选择）
  - 状态机流转图（四步思维链：解析→验证→诊断→统合）
  - 诊断日志面板（实时 CoT 推理轨迹）
  - 结果判定卡片（最终打分和 RMSE 值）

### 工具和类型

- **src/types/index.ts**: 定义所有 TypeScript 接口类型
- **src/utils/api.ts**: Axios 封装，提供 API 调用接口（当前为框架，待集成后端）
- **src/styles/index.css**: 全局样式，定义 CSS 变量和主题色

## 设计特点

1. **科技感风格**: 使用科技蓝 (#409EFF) 和灰白 (#f5f7fa) 主色调
2. **响应式布局**: 使用 Element Plus 的栅格系统，支持不同屏幕尺寸
3. **Mock 数据**: 所有页面使用 Mock 数据，便于立即运行和展示
4. **类型安全**: 完整的 TypeScript 类型定义
5. **模块化设计**: 组件、工具、类型分离，便于维护和扩展

## 后续开发建议

1. **API 集成**: 在 `src/utils/api.ts` 中实现真实的后端接口调用
2. **状态管理**: 如需复杂状态管理，可引入 Pinia
3. **文件处理**: 实现真实的 PDF/TXT 文件解析功能
4. **WebSocket/SSE**: 实现评估日志的实时流式传输
5. **错误处理**: 添加全局错误处理和用户提示
6. **单元测试**: 添加 Vue Test Utils 和 Vitest 进行组件测试
