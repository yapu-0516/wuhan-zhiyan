<script setup lang="ts">
// 大屏 HUD 面板外壳：平面数据分区；focus 时用 1px 边界强调。
defineProps<{ title: string; sub?: string; focus?: boolean }>()
</script>

<template>
  <section class="hud-panel ce-panel" :class="{ 'is-focus': focus }">
    <header class="ce-panel__header">
      <h3 class="ce-panel__title">{{ title }}</h3>
      <div class="hud-panel__extra"><slot name="extra" /></div>
    </header>
    <div class="hud-panel__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.hud-panel {
  transition:
    background-color 0.25s ease,
    border-color 0.25s ease;
}
.hud-panel.is-focus {
  background: #1b1d20;
}
.hud-panel__extra {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--ce-text-dim);
}
.hud-panel__body {
  flex: 1;
  min-height: 0;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
}
</style>
