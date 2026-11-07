<script setup lang="ts">
// 监测区域头卡：区域名称 / 范围 / 建筑·主干道·感知设备统计 / 数据更新时间
import { computed } from 'vue'
import { Location } from '@element-plus/icons-vue'
import AnimatedNumber from '../common/AnimatedNumber.vue'
import type { SystemInfo } from '@/types/api'

const props = defineProps<{
  info: SystemInfo | null
  buildingCount: number
  roadCount: number
  segmentCount: number
  devicesOnline: number
  devicesTotal: number
  /** 最近一次数据更新时间文本 */
  updatedAt: string
  /** 距上次更新的秒数 */
  ageSec: number
  live: boolean
  loading?: boolean
}>()

const extent = computed(() => {
  const b = props.info?.region?.bbox
  if (!b) return null
  const [w, s, e, n] = b
  const midLat = (s + n) / 2
  const wKm = (e - w) * 111.32 * Math.cos((midLat * Math.PI) / 180)
  const hKm = (n - s) * 110.57
  return {
    text: `${w.toFixed(3)}°–${e.toFixed(3)}°E · ${s.toFixed(3)}°–${n.toFixed(3)}°N`,
    size: `约 ${wKm.toFixed(1)} × ${hKm.toFixed(1)} km`,
    area: (wKm * hKm).toFixed(1)
  }
})

const online = computed(() => (props.devicesTotal ? Math.round((props.devicesOnline / props.devicesTotal) * 100) : 0))
const age = computed(() =>
  props.ageSec < 3 ? '刚刚' : props.ageSec < 60 ? `${props.ageSec} 秒前` : `${Math.floor(props.ageSec / 60)} 分钟前`
)
</script>

<template>
  <section class="rh cp-panel">
    <div class="rh__main">
      <span class="cp-label">当前监测区域</span>
      <el-skeleton v-if="loading && !info" animated :rows="1" style="width: 240px" />
      <template v-else>
        <h3 class="rh__name">
          <el-icon><Location /></el-icon>{{ info?.region?.name ?? '监测区域' }}
          <span v-if="info?.region?.city" class="cp-pill cp-pill--sm">{{ info.region.city }}</span>
          <span v-if="info?.demo_mode" class="cp-pill cp-pill--sm" style="--c: #f0c050">演示数据</span>
        </h3>
        <p v-if="extent" class="rh__ext">
          <span class="cp-mono">{{ extent.text }}</span>
          <span>{{ extent.size }} · 面积约 {{ extent.area }} km²</span>
        </p>
      </template>
    </div>

    <div class="rh__stats">
      <div class="rs" style="--c: #9b8fff">
        <span class="cp-label">纳管建筑</span>
        <b><AnimatedNumber :value="buildingCount" /><small>栋</small></b>
      </div>
      <div class="rs" style="--c: #f0c050">
        <span class="cp-label">主干道</span>
        <b><AnimatedNumber :value="roadCount" /><small>条</small></b>
        <em>共 {{ segmentCount }} 个路段</em>
      </div>
      <div class="rs" style="--c: #4dd984">
        <span class="cp-label">感知设备在线</span>
        <b
          ><AnimatedNumber :value="devicesOnline" /><small>/ {{ devicesTotal }}</small></b
        >
        <span class="cp-bar" style="--c: #4dd984"><i :style="{ width: `${online}%` }"></i></span>
      </div>
      <div class="rs rs--time" style="--c: #4fc3f7">
        <span class="cp-label">数据更新时间</span>
        <b class="cp-mono rs__t">{{ updatedAt || '—' }}</b>
        <em>
          <i class="cp-dot" :class="{ 'cp-dot--pulse': live }" :style="{ '--c': live ? '#4dd984' : '#8aa3c4' }"></i>
          {{ live ? `实时推送 · ${age}` : '静态快照 · 未连接实时通道' }}
        </em>
      </div>
    </div>
  </section>
</template>

<style scoped>
.rh {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 18px 36px;
  padding: 18px 24px;
  overflow: hidden;
  background: var(--ce-panel-solid);
  border-top: 2px solid var(--ce-accent);
}
.rh__main {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 260px;
}
.rh__name {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 0;
  color: var(--ce-text-strong);
}
.rh__name .el-icon {
  color: var(--ce-accent);
}
.rh__ext {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  margin: 0;
  font-size: 13px;
  color: var(--ce-text-dim);
}
.rh__stats {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 14px 34px;
}
.rs {
  --c: #4fc3f7;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 110px;
  padding-left: 12px;
  border-left: 2px solid color-mix(in srgb, var(--c) 60%, transparent);
}
.rs b {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 28px;
  line-height: 1.1;
  font-weight: 600;
  color: color-mix(in srgb, var(--c) 30%, #fff);
  font-variant-numeric: tabular-nums;
}
.rs b small {
  font-size: 12px;
  font-weight: 400;
  color: var(--ce-text-dim);
}
.rs em {
  display: flex;
  align-items: center;
  gap: 6px;
  font-style: normal;
  font-size: 12px;
  color: var(--ce-text-faint);
}
.rs .cp-bar {
  width: 100%;
}
.rs__t {
  font-size: 17px !important;
  padding-top: 5px;
}
.rs--time {
  min-width: 190px;
}
@media (max-width: 700px) {
  .rh {
    gap: 12px;
    padding: 14px;
  }
  .rh__main {
    min-width: 0;
    width: 100%;
  }
  .rh__name {
    font-size: 22px;
  }
  .rh__ext {
    font-size: 12px;
  }
  .rh__stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px 16px;
    width: 100%;
  }
  .rs,
  .rs--time {
    min-width: 0;
  }
  .rs b {
    font-size: 23px;
  }
}
</style>
