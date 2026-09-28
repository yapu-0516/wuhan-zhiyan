<script setup lang="ts">
// 左侧导航：5 个主页面，使用 Vue Router 切换
import { useRoute } from 'vue-router'
import {
  Location,
  Monitor,
  Warning,
  Files,
  MagicStick
} from '@element-plus/icons-vue'

const route = useRoute()

const navItems = [
  { to: '/dashboard', label: '城市总览', icon: Location },
  { to: '/monitoring', label: '城市监测', icon: Monitor },
  { to: '/event-center', label: '事件中心', icon: Warning },
  { to: '/data-management', label: '数据管理', icon: Files },
  { to: '/ai-analysis', label: 'AI 分析', icon: MagicStick }
]
</script>

<template>
  <aside class="sidebar">
    <nav class="nav-list">
      <RouterLink
        v-for="item in navItems"
        :key="item.to"
        :to="item.to"
        class="nav-item"
        :class="{ active: route.path === item.to }"
      >
        <el-icon class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-label">{{ item.label }}</span>
      </RouterLink>
    </nav>
    <div class="sidebar-footer">
      <span class="ver">CityEye v0.1 · 第3周原型</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-w);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: var(--ce-bg-soft);
  border-right: 1px solid var(--ce-panel-border);
}
.nav-list {
  display: flex;
  flex-direction: column;
  padding: 12px 10px;
  gap: 4px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  color: var(--ce-text-dim);
  text-decoration: none;
  border-radius: 4px;
  font-size: 14px;
  border-left: 2px solid transparent;
  transition: all 0.15s ease;
}
.nav-item:hover {
  color: var(--ce-text);
  background: rgba(79, 195, 247, 0.08);
}
.nav-item.active {
  color: #eaf4ff;
  background: rgba(79, 195, 247, 0.14);
  border-left-color: var(--ce-accent);
}
.nav-icon {
  font-size: 16px;
}
.sidebar-footer {
  padding: 12px 14px;
  font-size: 11px;
  color: #5d748f;
  border-top: 1px solid var(--ce-panel-border);
}
</style>
