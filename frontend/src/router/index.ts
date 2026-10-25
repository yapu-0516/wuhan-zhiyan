import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

// 城市智眼路由表（页面按需懒加载；城市总览由 App.vue KeepAlive 缓存）
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
    redirect: (to) => ({ path: '/ai-analysis/fire', query: to.query })
  },
  {
    // 火灾 / 拥堵 / 建筑异常 / 内涝 各自独立页面
    path: '/ai-analysis/:type(fire|traffic|building|flood)',
    name: 'ai-analysis',
    component: () => import('@/views/AIAnalysis.vue'),
    meta: { title: 'AI 分析' }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard'
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

const APP_TITLE = '城市智眼 CityEye'

router.afterEach((to) => {
  const t = typeof to.meta?.title === 'string' ? to.meta.title : ''
  document.title = t ? `${t} · ${APP_TITLE}` : APP_TITLE
})

export default router
