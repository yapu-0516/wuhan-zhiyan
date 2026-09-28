import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

// 城市之眼路由表
// 阶段3：5 个主页面占位，具体内容由后续阶段填充
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '城市总览' }
  },
  {
    path: '/monitoring',
    name: 'monitoring',
    component: () => import('@/views/Monitoring.vue'),
    meta: { title: '城市监测' }
  },
  {
    path: '/event-center',
    name: 'event-center',
    component: () => import('@/views/EventCenter.vue'),
    meta: { title: '事件中心' }
  },
  {
    path: '/data-management',
    name: 'data-management',
    component: () => import('@/views/DataManagement.vue'),
    meta: { title: '数据管理' }
  },
  {
    path: '/ai-analysis',
    name: 'ai-analysis',
    component: () => import('@/views/AIAnalysis.vue'),
    meta: { title: 'AI 分析' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
