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

const pad = (n: number) => String(n).padStart(2, '0')
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
        <defs>
          <linearGradient id="ce-logo-g" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#7ff3ff" />
            <stop offset="1" stop-color="#1f78d1" />
          </linearGradient>
          <radialGradient id="ce-logo-iris" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stop-color="#e8fdff" />
            <stop offset="0.45" stop-color="#36e4ff" />
            <stop offset="1" stop-color="#0d4f91" />
          </radialGradient>
        </defs>
        <path d="M3 24 C 11 11, 37 11, 45 24 C 37 37, 11 37, 3 24 Z" fill="none" stroke="url(#ce-logo-g)" stroke-width="2.4" />
        <circle cx="24" cy="24" r="8.5" fill="url(#ce-logo-iris)" />
        <circle cx="24" cy="24" r="3.2" fill="#03101f" />
        <circle cx="26.4" cy="21.6" r="1.4" fill="#fff" />
        <circle class="brand-logo__scan" cx="24" cy="24" r="13" fill="none" stroke="#4fc3f7" stroke-width="1" stroke-dasharray="6 5" />
      </svg>
      <div class="brand-text">
        <h1>城市智眼</h1>
        <p>CITYEYE · 城市运行指挥中心</p>
      </div>
    </div>

    <div class="center">
      <span class="wing wing--l" />
      <div class="region">
        <span class="region__city">{{ city }}</span>
        <span class="region__dot" />
        <span class="region__name">{{ region.name }}</span>
      </div>
      <span class="wing wing--r" />
    </div>

    <div class="header-right">
      <span v-if="demoMode" class="demo-badge" :title="demoTip">DEMO</span>
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
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0 18px;
  background:
    linear-gradient(180deg, rgba(79, 195, 247, 0.08), transparent),
    linear-gradient(90deg, #071430 0%, #0a1a3c 50%, #071430 100%);
  border-bottom: 1px solid var(--ce-panel-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.45);
}
.app-header::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, var(--ce-accent) 30%, #a8f4ff 50%, var(--ce-accent) 70%, transparent 100%);
  opacity: 0.75;
  box-shadow: 0 0 12px var(--ce-accent);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.brand-logo {
  flex: none;
  width: 40px;
  height: 40px;
  filter: drop-shadow(0 0 8px rgba(54, 228, 255, 0.55));
}
.brand-logo__scan {
  transform-origin: 24px 24px;
  animation: logo-spin 9s linear infinite;
}
@keyframes logo-spin {
  to {
    transform: rotate(360deg);
  }
}
.brand-text h1 {
  margin: 0;
  font-size: 21px;
  font-weight: 700;
  letter-spacing: 6px;
  line-height: 1.15;
  background: linear-gradient(180deg, #ffffff 20%, #9fe9ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  filter: drop-shadow(0 0 10px rgba(79, 195, 247, 0.45));
}
.brand-text p {
  margin: 2px 0 0;
  font-size: 10.5px;
  letter-spacing: 2px;
  color: var(--ce-text-dim);
  white-space: nowrap;
}

.center {
  display: flex;
  align-items: center;
  gap: 12px;
}
.wing {
  width: 90px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(79, 195, 247, 0.7));
}
.wing--r {
  transform: scaleX(-1);
}
.region {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 32px;
  padding: 0 18px;
  border: 1px solid var(--ce-panel-border);
  border-radius: 16px;
  background: rgba(79, 195, 247, 0.06);
  box-shadow: inset 0 0 14px rgba(79, 195, 247, 0.12);
  font-size: 14px;
  letter-spacing: 3px;
  white-space: nowrap;
}
.region__city {
  color: var(--ce-accent);
  font-weight: 600;
}
.region__dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--ce-accent);
  box-shadow: 0 0 6px var(--ce-accent);
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
  padding: 1px 8px;
  border: 1px solid rgba(155, 143, 255, 0.6);
  border-radius: 3px;
  font-family: var(--ce-font-num);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #c4bcff;
  background: rgba(155, 143, 255, 0.12);
  cursor: help;
}
.conn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 26px;
  padding: 0 12px;
  border: 1px solid;
  border-radius: 13px;
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
  color: #2ed47a;
  border-color: rgba(46, 212, 122, 0.45);
  background: rgba(46, 212, 122, 0.08);
}
.conn.ok .conn__dot {
  animation: conn-pulse 1.6s ease-out infinite;
}
.conn.offline {
  color: #f0c050;
  border-color: rgba(240, 192, 80, 0.45);
  background: rgba(240, 192, 80, 0.08);
}
.conn.retry {
  color: #4fc3f7;
  border-color: rgba(79, 195, 247, 0.45);
  background: rgba(79, 195, 247, 0.08);
}
.conn.retry .conn__dot {
  animation: conn-blink 0.9s ease-in-out infinite alternate;
}
@keyframes conn-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(46, 212, 122, 0.7);
  }
  100% {
    box-shadow: 0 0 0 8px rgba(46, 212, 122, 0);
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
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--ce-text-strong);
  text-shadow: 0 0 12px rgba(79, 195, 247, 0.5);
}
.clock__date {
  display: flex;
  flex-direction: column;
  font-size: 11px;
  line-height: 1.35;
  color: var(--ce-text-dim);
}

@media (max-width: 1280px) {
  .wing {
    display: none;
  }
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
</style>
