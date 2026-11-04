<script setup lang="ts">
// 演示导览字幕条：步骤序号 + 标题 + 解说 + 进度点 + 退出按钮
import type { TourState } from './types'

defineProps<{ state: TourState }>()
const emit = defineEmits<{ (e: 'stop'): void }>()
</script>

<template>
  <transition name="tour-cap">
    <div v-if="state.running" class="tour-caption" role="status" aria-live="polite">
      <div class="tc-step">
        <span class="tc-step__label">STEP</span>
        <span class="tc-step__num ce-num">{{ String(state.index).padStart(2, '0') }}</span>
        <span class="tc-step__total ce-num">/ {{ String(state.total).padStart(2, '0') }}</span>
      </div>
      <div class="tc-main">
        <transition name="tc-swap" mode="out-in">
          <div :key="state.index + state.title" class="tc-text">
            <h4>{{ state.title }}</h4>
            <p>{{ state.caption }}</p>
          </div>
        </transition>
        <div class="tc-dots">
          <i v-for="n in state.total" :key="n" :class="{ done: n < state.index, on: n === state.index }" />
        </div>
      </div>
      <button class="tc-stop" @click="emit('stop')">退出演示 <kbd>Esc</kbd></button>
    </div>
  </transition>
</template>

<style scoped>
.tour-caption {
  display: flex;
  align-items: stretch;
  gap: 16px;
  width: min(820px, calc(100% - 32px));
  padding: 12px 14px 12px 16px;
  border: 1px solid var(--ce-panel-border-strong);
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(6, 16, 36, 0.94), rgba(10, 26, 54, 0.9));
  box-shadow:
    0 14px 40px rgba(0, 0, 0, 0.55),
    0 0 30px rgba(79, 195, 247, 0.18),
    inset 0 0 30px rgba(79, 195, 247, 0.06);
  backdrop-filter: blur(10px);
  pointer-events: auto;
}
.tc-step {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-right: 16px;
  border-right: 1px solid var(--ce-divider);
}
.tc-step__label {
  font-size: 10px;
  letter-spacing: 3px;
  color: var(--ce-accent);
}
.tc-step__num {
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  color: #fff;
  text-shadow: 0 0 14px var(--ce-accent-glow);
}
.tc-step__total {
  font-size: 11px;
  color: var(--ce-text-dim);
}
.tc-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
}
.tc-text h4 {
  margin: 0 0 3px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 3px;
  color: var(--ce-text-strong);
}
.tc-text p {
  margin: 0;
  font-size: 13.5px;
  line-height: 1.6;
  color: #c8daf5;
}
.tc-dots {
  display: flex;
  gap: 5px;
}
.tc-dots i {
  width: 22px;
  height: 3px;
  border-radius: 2px;
  background: rgba(79, 195, 247, 0.18);
  transition: background 0.3s ease;
}
.tc-dots i.done {
  background: rgba(79, 195, 247, 0.55);
}
.tc-dots i.on {
  background: var(--ce-accent-2);
  box-shadow: 0 0 8px var(--ce-accent);
}
.tc-stop {
  flex: none;
  align-self: center;
  height: 30px;
  padding: 0 10px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 3px;
  background: rgba(79, 195, 247, 0.06);
  color: var(--ce-text);
  font-size: 12.5px;
  cursor: pointer;
}
.tc-stop:hover {
  border-color: var(--ce-danger);
  color: #fff;
  background: rgba(255, 107, 107, 0.15);
}
.tc-stop kbd {
  margin-left: 4px;
  padding: 0 4px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 2px;
  font-family: var(--ce-font);
  font-size: 10px;
  color: var(--ce-text-dim);
}
.tour-cap-enter-active,
.tour-cap-leave-active {
  transition: all 0.35s var(--ce-ease);
}
.tour-cap-enter-from,
.tour-cap-leave-to {
  opacity: 0;
  transform: translateY(16px);
}
.tc-swap-enter-active,
.tc-swap-leave-active {
  transition: all 0.25s ease;
}
.tc-swap-enter-from {
  opacity: 0;
  transform: translateX(10px);
}
.tc-swap-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}
</style>
