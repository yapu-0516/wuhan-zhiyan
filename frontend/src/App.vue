<script setup lang="ts">
// 城市之眼应用外壳：顶栏 + 左侧导航 + 路由主区 + 底部状态栏
import AppHeader from '@/components/AppHeader.vue'
import Sidebar from '@/components/Sidebar.vue'
import StatusPanel from '@/components/StatusPanel.vue'
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <Sidebar />
    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <component :is="Component" />
      </RouterView>
    </main>
    <StatusPanel />
  </div>
</template>

<style scoped>
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  grid-template-rows: var(--header-h) 1fr auto;
  width: 100vw;
  height: 100vh;
  background: var(--ce-bg);
}
.app-main {
  position: relative;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
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
