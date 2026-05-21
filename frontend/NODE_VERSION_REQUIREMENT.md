# Node.js 版本要求说明

## 问题
当前系统的 Node.js 版本为 **v10.19.0**，而本项目需要 **Node.js 18.0.0 或更高版本**。

## 解决方案

### 方案 1：使用 NVM 安装新版本 Node.js（推荐）

```bash
# 1. 安装 NVM
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 2. 重新加载 shell 配置
source ~/.bashrc

# 3. 安装 Node.js 18 LTS
nvm install 18

# 4. 使用 Node.js 18
nvm use 18

# 5. 验证版本
node --version  # 应该显示 v18.x.x

# 6. 重新安装依赖并运行
cd /home/lab106-dell/lz/code/SDWEB
npm install
npm run dev
```

### 方案 2：使用系统包管理器升级 Node.js

**Ubuntu/Debian:**
```bash
# 使用 NodeSource 仓库
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证
node --version
```

**CentOS/RHEL:**
```bash
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
```

### 方案 3：手动编译安装（不推荐，较复杂）

如果以上方案都不可行，可以手动编译安装 Node.js 18，但这需要较长时间和编译工具。

## 验证安装

安装完成后，运行以下命令验证：

```bash
node --version  # 应该 >= v18.0.0
npm --version   # 应该 >= 8.0.0
```

然后重新运行项目：

```bash
cd /home/lab106-dell/lz/code/SDWEB
npm install
npm run dev
```

## 为什么需要 Node.js 18+？

- **Vite 5.x** 要求 Node.js >= 18.0.0
- **Vue 3** 和相关工具链需要现代 JavaScript 特性
- **TypeScript 5.x** 需要较新的 Node.js 版本
- **更好的性能和安全性**

## 注意事项

- 升级 Node.js 不会影响系统其他部分（如果使用 NVM）
- 建议使用 LTS（长期支持）版本，如 Node.js 18 LTS
- 如果使用 NVM，可以在不同项目间切换 Node.js 版本
