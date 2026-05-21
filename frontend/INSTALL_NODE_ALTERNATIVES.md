# Node.js 安装替代方案

由于网络问题无法下载 NVM，以下是几种替代安装 Node.js 18+ 的方法：

## 方案 1：使用 NodeSource 仓库（推荐，需要 sudo 权限）

```bash
# 1. 添加 NodeSource 仓库（使用国内镜像加速）
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# 如果上面的命令也超时，可以手动添加仓库：
echo "deb https://deb.nodesource.com/node_18.x focal main" | sudo tee /etc/apt/sources.list.d/nodesource.list
echo "deb-src https://deb.nodesource.com/node_18.x focal main" | sudo tee -a /etc/apt/sources.list.d/nodesource.list

# 2. 更新包列表
sudo apt-get update

# 3. 安装 Node.js 18
sudo apt-get install -y nodejs

# 4. 验证安装
node --version
npm --version
```

## 方案 2：手动下载 Node.js 二进制文件（无需 sudo，推荐）

如果无法使用 sudo 或网络受限，可以手动下载 Node.js 二进制文件：

```bash
# 1. 创建安装目录
mkdir -p ~/.local/nodejs
cd ~/.local/nodejs

# 2. 下载 Node.js 18 LTS 二进制文件（Linux x64）
# 如果 curl 无法访问，可以：
# - 使用浏览器下载：https://nodejs.org/dist/v18.20.4/node-v18.20.4-linux-x64.tar.xz
# - 或使用 wget（如果可用）
wget https://nodejs.org/dist/v18.20.4/node-v18.20.4-linux-x64.tar.xz

# 如果 wget 也失败，可以尝试使用代理或从其他源下载
# 或者使用国内镜像：
wget https://npmmirror.com/mirrors/node/v18.20.4/node-v18.20.4-linux-x64.tar.xz

# 3. 解压
tar -xf node-v18.20.4-linux-x64.tar.xz

# 4. 添加到 PATH（添加到 ~/.bashrc）
echo 'export PATH="$HOME/.local/nodejs/node-v18.20.4-linux-x64/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 5. 验证安装
node --version
npm --version
```

## 方案 3：使用国内镜像安装 NVM

如果 GitHub 访问受限，可以尝试使用国内镜像：

```bash
# 使用 gitee 镜像
export NVM_SOURCE=https://gitee.com/mirrors/nvm.git
curl -o- https://gitee.com/mirrors/nvm/raw/master/install.sh | bash

# 或者使用代理（如果有）
export https_proxy=http://your-proxy:port
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
```

## 方案 4：检查是否已有其他 Node.js 版本

```bash
# 检查系统中是否有其他 Node.js 安装
find /usr -name node 2>/dev/null
find /opt -name node 2>/dev/null
find ~ -name node 2>/dev/null | grep -v node_modules

# 检查是否有 nvm 已安装但未加载
ls -la ~/.nvm 2>/dev/null
cat ~/.bashrc | grep nvm
```

## 方案 5：使用 conda（如果已安装）

```bash
# 如果系统有 conda/anaconda
conda install -c conda-forge nodejs=18
```

## 验证安装

安装完成后，运行：

```bash
node --version  # 应该显示 v18.x.x 或更高
npm --version   # 应该显示 9.x.x 或更高

# 然后重新安装项目依赖
cd /home/lab106-dell/lz/code/SDWEB
rm -rf node_modules package-lock.json
npm install
npm run dev
```

## 如果所有方案都不可行

如果以上方案都因网络或权限问题无法执行，可以考虑：

1. **联系系统管理员**升级 Node.js
2. **使用 Docker** 运行项目（如果系统有 Docker）：
   ```bash
   docker run -it -v $(pwd):/app -p 3000:3000 node:18 bash
   cd /app && npm install && npm run dev
   ```
3. **降级项目依赖**（不推荐，会失去很多功能）

## 当前系统信息

- OS: Ubuntu 20.04.6 LTS
- 当前 Node.js: v10.19.0
- 需要 Node.js: v18.0.0+
