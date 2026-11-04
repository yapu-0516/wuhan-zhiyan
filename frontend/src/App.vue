<script setup lang="ts">
// 城市智眼应用外壳：顶栏 + 左侧导航 + 路由主区 + 底部状态栏
// 城市总览（Dashboard）使用 KeepAlive 缓存：切换到管理页面再返回时不重建 Cesium Viewer。
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import Sidebar from '@/components/Sidebar.vue'
import StatusPanel from '@/components/StatusPanel.vue'
import { useLayout } from '@/composables/useLayout'

const { sidebarCollapsed } = useLayout()
const route = useRoute()
const isDrill = computed(() => route.path.startsWith('/drill'))
</script>

<template>
  <div class="app-shell" :class="{ 'is-collapsed': sidebarCollapsed, 'is-drill': isDrill }">
    <AppHeader />
    <Sidebar />
    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <KeepAlive include="Dashboard">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>
    <StatusPanel v-if="!isDrill" />
  </div>
</template>

<style scoped>
.app-shell {
  --sidebar-w: 184px;
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
.app-shell.is-drill {
  --status-h: 0px;
  grid-template-rows: var(--header-h) minmax(0, 1fr);
}
.app-main {
  position: relative;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
  background: var(--ce-bg);
}

@media (max-width: 1100px) {
  .app-shell {
    --sidebar-w: 56px;
  }
}
@media (max-width: 700px) {
  .app-shell {
    --sidebar-w: 0px;
    --status-h: 0px;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: 52px minmax(0, 1fr);
  }
  .app-main {
    grid-column: 1;
    grid-row: 2;
    padding-bottom: 56px;
  }
  .status-panel {
    display: none;
  }
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
