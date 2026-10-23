<script setup lang="ts">
// 城市之眼应用外壳：顶栏 + 左侧导航 + 路由主区 + 底部状态栏
// 城市总览（Dashboard）使用 KeepAlive 缓存：切换到管理页面再返回时不重建 Cesium Viewer。
import AppHeader from '@/components/AppHeader.vue'
import Sidebar from '@/components/Sidebar.vue'
import StatusPanel from '@/components/StatusPanel.vue'
import { useLayout } from '@/composables/useLayout'

const { sidebarCollapsed } = useLayout()
</script>

<template>
  <div class="app-shell" :class="{ 'is-collapsed': sidebarCollapsed }">
    <AppHeader />
    <Sidebar />
    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <KeepAlive include="Dashboard">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>
    <StatusPanel />
  </div>
</template>

<style scoped>
.app-shell {
  --sidebar-w: 200px;
  display: grid;
  grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
  grid-template-rows: var(--header-h) minmax(0, 1fr) var(--status-h);
  width: 100vw;
  height: 100vh;
  background: var(--ce-bg);
  transition: grid-template-columns 0.3s var(--ce-ease);
}
.app-shell.is-collapsed {
  --sidebar-w: 60px;
}
.app-main {
  position: relative;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(79, 195, 247, 0.06), transparent 60%),
    var(--ce-bg);
}
</style>

<style>
/* 顶层布局项的位置（非 scoped 以命中网格直接子元素） */
.app-header {
  grid-column: 1 / -1;
  grid-row: 1;
}
.sidebar {
  grid-column: 1;
  grid-row: 2;
}
.app-main {
  grid-column: 2;
  grid-row: 2;
}
.status-panel {
  grid-column: 1 / -1;
  grid-row: 3;
}
</style>
