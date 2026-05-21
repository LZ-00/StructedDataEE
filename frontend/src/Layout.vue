<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <div class="logo">
          <el-icon :size="30"><DataAnalysis /></el-icon>
          <span class="title">激光焊接结构化数据抽取与质量评估系统</span>
        </div>
        <div class="header-right">
          <el-menu
            mode="horizontal"
            :default-active="activeIndex"
            class="header-menu"
            @select="handleMenuSelect"
          >
            <el-menu-item index="extraction">
              <el-icon><DocumentCopy /></el-icon>
              <span>智能抽取工作台</span>
            </el-menu-item>
            <el-menu-item index="evaluation">
              <el-icon><Monitor /></el-icon>
              <span>思维链评估</span>
            </el-menu-item>
            <el-menu-item index="distillation">
              <el-icon><Setting /></el-icon>
              <span>数据蒸馏与微调平台</span>
            </el-menu-item>
            <el-menu-item index="models">
              <el-icon><Cpu /></el-icon>
              <span>模型配置</span>
            </el-menu-item>
          </el-menu>
          <el-button type="primary" link class="logout-btn" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            <span>退出登录</span>
          </el-button>
        </div>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DataAnalysis,
  DocumentCopy,
  Monitor,
  Setting,
  Cpu,
  SwitchButton
} from '@element-plus/icons-vue'
import { logout } from '@/utils/auth'

const route = useRoute()
const router = useRouter()

const activeIndex = computed(() => {
  const path = route.path
  if (path.includes('extraction')) return 'extraction'
  if (path.includes('evaluation')) return 'evaluation'
  if (path.includes('distillation')) return 'distillation'
  if (path.includes('models')) return 'models'
  return 'extraction'
})

const handleMenuSelect = (key: string) => {
  router.push(`/${key}`)
}

const handleLogout = () => {
  logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  background: #ffffff;
}

.app-header {
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 0;
  height: 78px;
  border-bottom: 1px solid rgba(107, 174, 214, 0.2);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 32px;
  max-width: 1600px;
  margin: 0 auto;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  justify-content: flex-end;
}

.logo {
  display: flex;
  align-items: center;
  gap: 14px;
  color: #ffffff;
  font-size: var(--el-font-size-large);
  font-weight: 600;
  font-family: 'Arial', 'Helvetica Neue', sans-serif;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.logo :deep(.el-icon) {
  color: #6baed6;
}

.title {
  letter-spacing: 0.8px;
}

.header-menu {
  background: transparent;
  border: none;
  flex: 1;
  min-width: 0;
  justify-content: flex-end;
}

.header-menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.85);
  border-bottom: 2px solid transparent;
  font-weight: 500;
  font-size: var(--el-font-size-base);
  transition: all 0.3s ease;
  margin: 0 4px;
}

.header-menu :deep(.el-menu-item:hover) {
  color: #ffffff;
  background: rgba(107, 174, 214, 0.15);
  border-bottom-color: #6baed6;
}

.header-menu :deep(.el-menu-item.is-active) {
  color: #ffffff;
  background: rgba(107, 174, 214, 0.2);
  border-bottom-color: #6baed6;
  font-weight: 600;
}

.header-menu :deep(.el-menu-item .el-icon) {
  color: inherit;
}

.logout-btn {
  color: rgba(255, 255, 255, 0.9) !important;
  font-size: var(--el-font-size-base);
  flex-shrink: 0;
  margin-left: 8px;
}

.logout-btn:hover {
  color: #6baed6 !important;
}

.app-main {
  padding: 20px 24px;
  overflow-y: auto;
  background: var(--bg-tertiary);
  font-size: var(--el-font-size-base);
}
</style>
