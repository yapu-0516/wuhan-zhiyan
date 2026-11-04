<script setup lang="ts">
// 顶部品牌栏：品牌标识 + 示范区 + 演示模式徽标 + 实时连接状态 + 时钟
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRealtime } from '@/composables/useRealtime'
import { useSystemInfo } from '@/composables/useSystemInfo'
import { apiState } from '@/api/http'

const { connected } = useRealtime()
const { info, region, demoMode, load } = useSystemInfo()

const now = ref(new Date())
let timer: number | undefined
onMounted(() => {
  void load()
  timer = window.setInterval(() => (now.value = new Date()), 1000)
})
onBeforeUnmount(() => window.clearInterval(timer))

const pad = (n: number) => String(n).padStart(2, '0') // taste-skill-ignore numbering: clock/date formatting
const WEEK = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const time = computed(() => `${pad(now.value.getHours())}:${pad(now.value.getMinutes())}:${pad(now.value.getSeconds())}`)
const date = computed(() => `${now.value.getFullYear()}年${pad(now.value.getMonth() + 1)}月${pad(now.value.getDate())}日`)
const week = computed(() => WEEK[now.value.getDay()])

const everConnected = ref(false)
watch(connected, (v) => v && (everConnected.value = true), { immediate: true })

const conn = computed(() => {
  if (connected.value) return { label: '实时连接', cls: 'ok', tip: 'WebSocket 已连接，事件与路况实时推送' }
  if (apiState.mode !== 'live')
    return {
      label: '离线演示',
      cls: 'offline',
      tip: apiState.mode === 'mock' ? '静态演示数据模式（VITE_USE_MOCK）' : `后端不可达，已切换为离线快照数据${apiState.lastError ? `（${apiState.lastError}）` : ''}`
    }
  return { label: everConnected.value ? '重连中' : '连接中', cls: 'retry', tip: '正在建立实时通道…' }
})

const city = computed(() => info.value?.region?.city || '武汉')

const demoTip = computed(() =>
  info.value?.simulator?.enabled
    ? `演示模式：事件模拟器每 ${info.value.simulator.interval_sec} 秒生成一条城市事件`
    : '演示模式'
)
</script>

<template>
  <header class="app-header">
    <div class="brand">
      <svg class="brand-logo" viewBox="0 0 48 48" aria-hidden="true">
        <path d="M3 24 C 11 11, 37 11, 45 24 C 37 37, 11 37, 3 24 Z" fill="none" stroke="#8edbf2" stroke-width="2.4" />
        <circle cx="24" cy="24" r="8.5" fill="#6dc7e7" />
        <circle cx="24" cy="24" r="3.2" fill="#03101f" />
        <circle cx="26.4" cy="21.6" r="1.4" fill="#fff" />
      </svg>
      <div class="brand-text">
        <h1>城市智眼</h1>
        <p>武汉城市运行指挥中心</p>
      </div>
    </div>

    <div class="center">
      <div class="region">
        <span class="region__city">{{ city }}</span>
        <span class="region__dot" />
        <span class="region__name">{{ region.name }}</span>
      </div>
    </div>

    <div class="header-right">
      <span v-if="demoMode" class="demo-badge" :title="demoTip">演示</span>
      <span class="conn" :class="conn.cls" :title="conn.tip">
        <i class="conn__dot" />{{ conn.label }}
      </span>
      <div class="clock">
        <span class="clock__time ce-num">{{ time }}</span>
        <span class="clock__date">
          <span>{{ date }}</span>
          <span>{{ week }}</span>
        </span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: relative;
  z-index: 20;
  height: var(--header-h);
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  padding: 0 16px;
  background: var(--ce-bg);
  border-bottom: 1px solid var(--ce-divider);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.brand-logo {
  flex: none;
  width: 34px;
  height: 34px;
}
.brand-text h1 {
  margin: 0;
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 0;
  line-height: 1.15;
  color: var(--ce-text-strong);
  white-space: nowrap;
}
.brand-text p {
  margin: 2px 0 0;
  font-size: 12px;
  letter-spacing: 0;
  color: var(--ce-text-faint);
  white-space: nowrap;
}

.center {
  display: flex;
  align-items: center;
  justify-content: center;
}
.region {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 28px;
  padding: 0 12px;
  border-left: 1px solid var(--ce-divider);
  border-right: 1px solid var(--ce-divider);
  font-size: 13px;
  letter-spacing: 0;
  white-space: nowrap;
}
.region__city {
  color: var(--ce-text-strong);
  font-weight: 600;
}
.region__dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--ce-text-faint);
}
.region__name {
  color: var(--ce-text-strong);
}

.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 14px;
  min-width: 0;
}
.demo-badge {
  padding: 1px 7px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0;
  color: var(--ce-text-dim);
  background: transparent;
  cursor: help;
}
.conn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 24px;
  padding: 0 8px;
  border: 0;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  cursor: help;
}
.conn__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}
.conn.ok {
  color: var(--ce-success);
  background: transparent;
}
.conn.ok .conn__dot {
  animation: conn-pulse 1.6s ease-out infinite;
}
.conn.offline {
  color: var(--ce-warning);
  background: transparent;
}
.conn.retry {
  color: var(--ce-accent);
  background: transparent;
}
.conn.retry .conn__dot {
  animation: conn-blink 0.9s ease-in-out infinite alternate;
}
@keyframes conn-pulse {
  0% {
    opacity: 1;
  }
  100% {
    opacity: 0.35;
  }
}
@keyframes conn-blink {
  to {
    opacity: 0.25;
  }
}
.clock {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 14px;
  border-left: 1px solid var(--ce-divider);
}
.clock__time {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0;
  color: var(--ce-text-strong);
}
.clock__date {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  line-height: 1.35;
  color: var(--ce-text-dim);
}

@media (max-width: 1280px) {
  .brand-text p {
    display: none;
  }
}
@media (max-width: 1000px) {
  .center {
    display: none;
  }
  .app-header {
    grid-template-columns: 1fr auto;
  }
}
@media (max-width: 700px) {
  .app-header {
    height: 52px;
    padding: 0 16px;
  }
  .brand-logo {
    width: 28px;
    height: 28px;
  }
  .brand {
    gap: 8px;
  }
  .brand-text h1 {
    font-size: 16px;
  }
  .brand-text p,
  .demo-badge,
  .clock__date {
    display: none;
  }
  .header-right {
    gap: 8px;
  }
  .clock {
    padding-left: 8px;
  }
  .clock__time {
    font-size: 16px;
  }
}
</style>
