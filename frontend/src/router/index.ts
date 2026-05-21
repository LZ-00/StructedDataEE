import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { isAuthenticated } from '@/utils/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true }
  },
  {
    path: '/',
    component: () => import('@/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: 'extraction' },
      { path: 'dashboard', redirect: 'extraction' },
      {
        path: 'extraction',
        name: 'Extraction',
        component: () => import('@/views/ExtractionWorkspace.vue')
      },
      {
        path: 'evaluation',
        name: 'Evaluation',
        component: () => import('@/views/EvaluationTracker.vue')
      },
      {
        path: 'distillation',
        name: 'Distillation',
        component: () => import('@/views/DistillationPlatform.vue')
      },
      {
        path: 'models',
        name: 'ModelConfig',
        component: () => import('@/views/ModelConfig.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const authed = isAuthenticated()
  if (to.meta.requiresAuth && !authed) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'Login' && authed) {
    return { path: '/extraction' }
  }
  return true
})

export default router
