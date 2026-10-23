<script setup lang="ts">
// 大屏 HUD 面板外壳：玻璃底 + 四角高亮 + 标题栏；focus 时（演示导览聚焦）外发光
defineProps<{ title: string; sub?: string; focus?: boolean }>()
</script>

<template>
  <section class="hud-panel ce-panel" :class="{ 'is-focus': focus }">
    <header class="ce-panel__header">
      <h3 class="ce-panel__title">{{ title }}<small v-if="sub" class="hud-panel__sub">{{ sub }}</small></h3>
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
    box-shadow 0.4s ease,
    border-color 0.4s ease;
}
.hud-panel.is-focus {
  border-color: var(--ce-accent);
  box-shadow:
    0 0 0 1px rgba(79, 195, 247, 0.4),
    0 0 28px rgba(79, 195, 247, 0.35),
    inset 0 0 30px rgba(79, 195, 247, 0.1);
}
.hud-panel__sub {
  margin-left: 2px;
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 1px;
  color: var(--ce-text-faint);
  text-shadow: none;
}
.hud-panel__extra {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ce-text-dim);
}
.hud-panel__body {
  flex: 1;
  min-height: 0;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
}
</style>
