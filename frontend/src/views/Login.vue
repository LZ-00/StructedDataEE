<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <div class="brand-icon-wrap">
          <el-icon class="brand-icon" :size="44"><Coin /></el-icon>
        </div>
        <h1 class="brand-title">激光焊接结构化数据抽取与质量评估系统</h1>
      </div>

      <el-form class="login-form" @submit.prevent="handleSubmit">
        <el-form-item>
          <el-input
            v-model="username"
            size="large"
            placeholder="用户名"
            clearable
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="password"
            size="large"
            type="password"
            placeholder="密码"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item class="submit-item">
          <el-button
            type="primary"
            native-type="submit"
            size="large"
            class="login-btn"
            :loading="submitting"
          >
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-notice" aria-hidden="true" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Coin } from '@element-plus/icons-vue'
import { loginWithApi, DEFAULT_USERNAME, DEFAULT_PASSWORD } from '@/utils/auth'

const route = useRoute()
const router = useRouter()

const username = ref(DEFAULT_USERNAME)
const password = ref(DEFAULT_PASSWORD)
const submitting = ref(false)

const handleSubmit = async () => {
  submitting.value = true
  try {
    await new Promise((r) => setTimeout(r, 180))
    const result = await loginWithApi(username.value.trim(), password.value)
    if (!result.ok) {
      ElMessage.error(result.message)
      return
    }
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/extraction'
    const target = redirect === '/dashboard' ? '/extraction' : redirect || '/extraction'
    router.replace(target)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(
    135deg,
    #3d566e 0%,
    #2c3e50 38%,
    #34495e 72%,
    #4a6d82 100%
  );
}

.login-card {
  width: 100%;
  max-width: 440px;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: var(--shadow-dark);
  padding: 40px 40px 32px;
}

.login-brand {
  text-align: center;
  margin-bottom: 24px;
}

.brand-icon-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 16px;
  border: 2px solid rgba(107, 174, 214, 0.85);
  background: rgba(107, 174, 214, 0.08);
  margin-bottom: 18px;
}

.brand-icon {
  color: #6baed6;
}

.brand-title {
  font-size: var(--el-font-size-extra-large);
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.35;
  letter-spacing: 0.5px;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  background-color: #f5f8fb;
  box-shadow: 0 0 0 1px var(--border-light) inset;
}

.login-form :deep(.el-input__wrapper:hover),
.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px rgba(107, 174, 214, 0.45) inset;
}

.submit-item {
  margin-bottom: 0;
}

.login-btn {
  width: 100%;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  letter-spacing: 2px;
  background: linear-gradient(90deg, #5a9ec4 0%, #2c3e50 100%);
}

.login-btn:hover,
.login-btn:focus {
  background: linear-gradient(90deg, #6baed6 0%, #34495e 100%);
}

.login-notice {
  margin-top: 24px;
  min-height: 12px;
  border-radius: 8px;
  background: rgba(107, 174, 214, 0.12);
  border: 1px solid rgba(107, 174, 214, 0.25);
  border-left: 4px solid var(--primary-color);
}
</style>
