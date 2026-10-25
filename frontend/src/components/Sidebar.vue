<script setup lang="ts">
// 左侧导航：5 个主页面；AI 分析拆分为火灾 / 拥堵 / 建筑异常 / 内涝四个独立页面；事件中心显示未办结事件数徽标；可折叠为图标栏
import { useRoute } from 'vue-router'
import { Location, Monitor, Warning, Files, Sunny, Van, OfficeBuilding, Umbrella, Fold, Expand } from '@element-plus/icons-vue'
import { useCityEvents } from '@/composables/useCityEvents'
import { useLayout } from '@/composables/useLayout'

const route = useRoute()
const { stats } = useCityEvents()
const { sidebarCollapsed, toggleSidebar } = useLayout()

const navItems = [
  { to: '/dashboard', label: '城市总览', en: 'OVERVIEW', icon: Location },
  { to: '/monitoring', label: '城市监测', en: 'MONITOR', icon: Monitor },
  { to: '/event-center', label: '事件中心', en: 'EVENTS', icon: Warning, badge: true },
  { to: '/data-management', label: '数据管理', en: 'DATA', icon: Files }
]

// AI 分析按风险类型独立成页，互不混排
const aiItems = [
  { to: '/ai-analysis/fire', label: '火灾识别', en: 'FIRE', icon: Sunny },
  { to: '/ai-analysis/traffic', label: '交通拥堵', en: 'TRAFFIC', icon: Van },
  { to: '/ai-analysis/building', label: '建筑异常', en: 'BUILDING', icon: OfficeBuilding },
  { to: '/ai-analysis/flood', label: '内涝积水', en: 'FLOOD', icon: Umbrella }
]

const isActive = (to: string) => route.path === to || route.path.startsWith(`${to}/`)
</script>

<template>
  <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
    <nav class="nav-list">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: isActive(item.to) }"
        :title="sidebarCollapsed ? item.label : undefined"
      >
        <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-text">
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-en">{{ item.en }}</span>
        </span>
        <span v-if="item.badge && stats.active > 0" class="nav-badge ce-num">{{ stats.active > 99 ? '99+' : stats.active }}</span>
      </RouterLink>

      <div class="nav-group-label" title="AI 分析">
        <span>AI 分析</span><em>AI LAB</em>
      </div>
      <RouterLink
        v-for="item in aiItems"
        :key="item.to"
        :to="item.to"
        class="nav-item nav-item--sub"
        :class="{ active: isActive(item.to) }"
        :title="sidebarCollapsed ? item.label : undefined"
      >
        <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-text">
          <span class="nav-label">{{ item.label }}</span>
          <span class="nav-en">{{ item.en }}</span>
        </span>
      </RouterLink>
    </nav>
    <div class="sidebar-footer">
      <button class="collapse-btn" :title="sidebarCollapsed ? '展开导航' : '收起导航'" @click="toggleSidebar">
        <el-icon><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
      </button>
      <span class="ver">CityEye v1.0</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
  overflow: hidden;
  background: linear-gradient(180deg, #08122a 0%, #060d1f 100%);
  border-right: 1px solid var(--ce-panel-border);
  box-shadow: 4px 0 18px rgba(0, 0, 0, 0.35);
}
.nav-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 8px;
  overflow-y: auto;
}
.nav-group-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 10px 4px 2px;
  padding: 6px 8px 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #6f89aa;
  border-top: 1px solid var(--ce-divider);
}
.nav-group-label em {
  font-style: normal;
  font-family: var(--ce-font-num);
  font-size: 9.5px;
  letter-spacing: 1.5px;
  color: var(--ce-text-faint);
}
.nav-item--sub {
  height: 40px;
  padding-left: 18px;
}
.nav-item--sub .nav-icon {
  font-size: 16px;
}
.nav-item--sub .nav-label {
  font-size: 13px;
  letter-spacing: 1px;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 46px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--ce-text-dim);
  text-decoration: none;
  white-space: nowrap;
  transition:
    color 0.15s ease,
    background 0.15s ease,
    border-color 0.15s ease;
}
.nav-item:hover {
  color: var(--ce-text-strong);
  background: rgba(79, 195, 247, 0.08);
}
.nav-item.active {
  color: #fff;
  border-color: rgba(79, 195, 247, 0.35);
  background: linear-gradient(90deg, rgba(79, 195, 247, 0.24), rgba(79, 195, 247, 0.04));
  box-shadow: inset 0 0 16px rgba(79, 195, 247, 0.12);
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: -9px;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background: var(--ce-accent-2);
  box-shadow: 0 0 10px var(--ce-accent);
}
.nav-icon {
  flex: none;
  font-size: 18px;
}
.nav-item.active .nav-icon {
  color: var(--ce-accent-2);
  filter: drop-shadow(0 0 5px var(--ce-accent));
}
.nav-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.2;
}
.nav-label {
  font-size: 14px;
  letter-spacing: 2px;
}
.nav-en {
  font-family: var(--ce-font-num);
  font-size: 9.5px;
  letter-spacing: 1.5px;
  color: var(--ce-text-faint);
}
.nav-badge {
  margin-left: auto;
  min-width: 20px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  font-size: 11px;
  line-height: 18px;
  text-align: center;
  color: #fff;
  background: linear-gradient(135deg, #ff6b6b, #e0393e);
  box-shadow: 0 0 10px rgba(255, 107, 107, 0.6);
}
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-top: 1px solid var(--ce-divider);
}
.collapse-btn {
  flex: none;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--ce-divider);
  border-radius: 3px;
  background: transparent;
  color: var(--ce-text-dim);
  cursor: pointer;
}
.collapse-btn:hover {
  color: #fff;
  border-color: var(--ce-panel-border-strong);
}
.ver {
  font-family: var(--ce-font-num);
  font-size: 11px;
  letter-spacing: 1px;
  color: var(--ce-text-faint);
  white-space: nowrap;
}

/* 折叠为图标栏 */
.collapsed .nav-item {
  justify-content: center;
  padding: 0;
}
.collapsed .nav-text,
.collapsed .ver,
.collapsed .nav-group-label {
  display: none;
}
.collapsed .nav-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 16px;
  height: 16px;
  padding: 0 3px;
  font-size: 10px;
  line-height: 16px;
}
.collapsed .sidebar-footer {
  justify-content: center;
  padding: 10px 0;
}
</style>
