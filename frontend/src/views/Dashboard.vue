<script setup lang="ts">
// 城市总览（默认首页）—— 三维城市场景为核心
// 阶段3：仅承载 CesiumViewer；阶段4 起在此叠加建筑/事件/详情
import CesiumViewer from '@/components/CesiumViewer.vue'
</script>

<template>
  <div class="dashboard">
    <CesiumViewer class="scene" />
    <!-- 后续阶段的事件详情/建筑信息浮层将挂在此容器内 -->
  </div>
</template>

<style scoped>
.dashboard {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.scene {
  width: 100%;
  height: 100%;
}
</style>
