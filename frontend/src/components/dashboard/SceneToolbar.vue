<script setup lang="ts">
// 场景浮动工具条：图层开关 / 底图切换 / 自动追踪 / 复位视角 / 一键演示
import { OfficeBuilding, Guide, Location, FirstAidKit, Aim, RefreshLeft, VideoPlay, SwitchButton } from '@element-plus/icons-vue'
import type { LayerKey, LayerVisibility } from '@/components/scene/types'
import type { BasemapKey } from '@/config/cesium'

defineProps<{ layers: LayerVisibility; basemap: BasemapKey; autoTrack: boolean; touring: boolean }>()
const emit = defineEmits<{
  (e: 'toggle-layer', key: LayerKey): void
  (e: 'basemap', key: BasemapKey): void
  (e: 'auto-track', on: boolean): void
  (e: 'home'): void
  (e: 'tour'): void
}>()

const LAYERS: { key: LayerKey; label: string; icon: typeof OfficeBuilding }[] = [
  { key: 'buildings', label: '建筑', icon: OfficeBuilding },
  { key: 'roads', label: '路况', icon: Guide },
  { key: 'events', label: '事件', icon: Location },
  { key: 'pois', label: '应急资源', icon: FirstAidKit }
]
const BASEMAP_OPTIONS: { key: BasemapKey; label: string }[] = [
  { key: 'dark', label: '暗色' },
  { key: 'satellite', label: '卫星' },
  { key: 'offline', label: '离线' }
]
</script>

<template>
  <div class="toolbar">
    <div class="tb-group">
      <button
        v-for="l in LAYERS"
        :key="l.key"
        class="tb-chip"
        :class="{ on: layers[l.key] }"
        :title="(layers[l.key] ? '隐藏' : '显示') + l.label + '图层'"
        @click="emit('toggle-layer', l.key)"
      >
        <el-icon><component :is="l.icon" /></el-icon><span class="tb-label">{{ l.label }}</span>
      </button>
    </div>
    <span class="tb-sep" />
    <div class="tb-seg" role="radiogroup" aria-label="底图">
      <button
        v-for="b in BASEMAP_OPTIONS"
        :key="b.key"
        role="radio"
        :aria-checked="basemap === b.key"
        :class="{ on: basemap === b.key }"
        @click="emit('basemap', b.key)"
      >
        {{ b.label }}
      </button>
    </div>
    <span class="tb-sep" />
    <button class="tb-switch" :class="{ on: autoTrack }" title="新事件到达时相机自动飞往" @click="emit('auto-track', !autoTrack)">
      <i class="tb-switch__knob" />
      <el-icon><Aim /></el-icon><span class="tb-label">自动追踪</span>
    </button>
    <button class="tb-btn" title="复位到示范区默认视角" @click="emit('home')">
      <el-icon><RefreshLeft /></el-icon><span class="tb-label">复位视角</span>
    </button>
    <button class="tb-btn tb-btn--tour" :class="{ running: touring }" @click="emit('tour')">
      <el-icon><component :is="touring ? SwitchButton : VideoPlay" /></el-icon>{{ touring ? '退出演示' : '一键演示' }}
    </button>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 6px;
  background: linear-gradient(180deg, rgba(12, 28, 58, 0.88), rgba(6, 15, 34, 0.84));
  box-shadow:
    0 10px 30px rgba(0, 0, 0, 0.45),
    inset 0 1px 0 rgba(79, 195, 247, 0.15);
  backdrop-filter: blur(10px);
  white-space: nowrap;
}
.tb-group,
.tb-seg {
  display: flex;
  align-items: center;
  gap: 4px;
}
.tb-sep {
  width: 1px;
  height: 20px;
  background: var(--ce-divider);
}
button {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 3px;
  background: transparent;
  color: var(--ce-text-dim);
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.15s ease;
}
button:hover {
  color: var(--ce-text-strong);
  background: rgba(79, 195, 247, 0.1);
}
.tb-chip.on {
  color: var(--ce-text-strong);
  border-color: rgba(79, 195, 247, 0.35);
  background: rgba(79, 195, 247, 0.14);
}
.tb-chip.on .el-icon {
  color: var(--ce-accent-2);
  filter: drop-shadow(0 0 4px var(--ce-accent));
}
.tb-seg {
  padding: 2px;
  border: 1px solid var(--ce-divider);
  border-radius: 4px;
  background: rgba(3, 8, 18, 0.4);
  gap: 2px;
}
.tb-seg button {
  height: 24px;
  padding: 0 10px;
}
.tb-seg button.on {
  color: #04121f;
  background: linear-gradient(90deg, #36a6f0, #5fe0ff);
  font-weight: 600;
}
.tb-switch {
  position: relative;
  padding-left: 36px;
}
.tb-switch__knob {
  position: absolute;
  left: 6px;
  top: 50%;
  width: 24px;
  height: 12px;
  margin-top: -6px;
  border-radius: 6px;
  background: rgba(79, 195, 247, 0.15);
  transition: background 0.2s ease;
}
.tb-switch__knob::after {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ce-text-dim);
  transition: all 0.2s ease;
}
.tb-switch.on {
  color: var(--ce-text-strong);
}
.tb-switch.on .tb-switch__knob {
  background: rgba(46, 212, 122, 0.45);
}
.tb-switch.on .tb-switch__knob::after {
  left: 14px;
  background: #2ed47a;
  box-shadow: 0 0 6px #2ed47a;
}
.tb-btn {
  border-color: var(--ce-divider);
}
.tb-btn--tour {
  color: #04121f;
  font-weight: 600;
  border-color: transparent;
  background: linear-gradient(90deg, #1f8fe0, #36d6f5);
  box-shadow: 0 0 16px rgba(54, 214, 245, 0.45);
  animation: tb-breathe 2.6s ease-in-out infinite;
}
.tb-btn--tour:hover {
  color: #04121f;
  background: linear-gradient(90deg, #36a6f0, #6ae6ff);
}
.tb-btn--tour.running {
  color: #fff;
  background: linear-gradient(90deg, #c2414b, #ff6b6b);
  box-shadow: 0 0 16px rgba(255, 107, 107, 0.45);
  animation: none;
}
/* 中心区域较窄时（容器查询）仅保留图标 */
@container hud-toolbar (max-width: 860px) {
  .tb-label {
    display: none;
  }
  button {
    padding: 0 8px;
  }
  .tb-switch {
    padding-left: 34px;
  }
}
@keyframes tb-breathe {
  0%,
  100% {
    box-shadow: 0 0 10px rgba(54, 214, 245, 0.3);
  }
  50% {
    box-shadow: 0 0 22px rgba(54, 214, 245, 0.7);
  }
}
</style>
