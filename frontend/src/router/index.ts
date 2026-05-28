import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    redirect: '/extraction'
  },
  {
    path: '/',
    component: () => import('@/Layout.vue'),
    children: [
      { path: '', redirect: 'extraction' },
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

export default router
