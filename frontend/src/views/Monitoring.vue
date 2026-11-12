<script setup lang="ts">
// 城市监测页面，实时更新数据源吞吐和路网状态。
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getBuildings, getRoads } from '@/api/geo'
import { getSources, getSystemInfo } from '@/api/system'
import { useRealtime } from '@/composables/useRealtime'
import { errMsg, nowText } from '@/composables/pages/format'
import PageShell from '@/components/pages/PageShell.vue'
import RegionHeader from '@/components/pages/RegionHeader.vue'
import SourceCard from '@/components/pages/SourceCard.vue'
import TrafficPanel from '@/components/pages/TrafficPanel.vue'
import BuildingSafetyPanel from '@/components/pages/BuildingSafetyPanel.vue'
import type { DataSource, SystemInfo } from '@/types/api'
import type { Building, Road } from '@/types/building'

const HISTORY_MAX = 40

const rt = useRealtime()
const { connected } = rt

const loading = ref(true)
const info = ref<SystemInfo | null>(null)
const buildings = ref<Building[]>([])
const roads = ref<Road[]>([])
const sources = ref<DataSource[]>([])
const cityTpi = ref<number | null>(null)
const history = reactive<Record<string, number[]>>({})
const updatedAt = ref('')
const lastPushAt = ref(0)
const now = ref(Date.now())

const monitored = computed(() => buildings.value.filter((b) => b.monitored))
const devicesOnline = computed(() => sources.value.reduce((s, x) => s + x.devices_online, 0))
const devicesTotal = computed(() => sources.value.reduce((s, x) => s + x.devices_total, 0))
const roadNameCount = computed(() => new Set(roads.value.map((r) => r.name?.trim() || r.id)).size)
const ageSec = computed(() => (lastPushAt.value ? Math.max(0, Math.round((now.value - lastPushAt.value) / 1000)) : 0))

function touch() {
  lastPushAt.value = Date.now()
  updatedAt.value = nowText()
}

async function load() {
  loading.value = true
  const [i, b, r, s] = await Promise.allSettled([getSystemInfo(), getBuildings(), getRoads(), getSources()])
  if (i.status === 'fulfilled') info.value = i.value
  if (b.status === 'fulfilled') buildings.value = b.value.features.map((f) => f.properties)
  else ElMessage.warning(errMsg(b.reason, '建筑数据加载失败'))
  if (r.status === 'fulfilled') roads.value = r.value.features.map((f) => f.properties)
  else ElMessage.warning(errMsg(r.reason, '路网数据加载失败'))
  if (s.status === 'fulfilled') {
    sources.value = s.value
    for (const src of s.value) history[src.id] = [src.throughput]
  } else ElMessage.warning(errMsg(s.reason, '数据源加载失败'))
  updatedAt.value = nowText()
  loading.value = false
}

const unsubs: (() => void)[] = []
let clock: number | undefined

onMounted(() => {
  void load()
  rt.start()
  unsubs.push(
    rt.on('sensor.tick', (d) => {
      const byId = new Map(sources.value.map((s) => [s.id, s]))
      for (const u of d.sources) {
        const s = byId.get(u.id)
        if (!s) continue
        s.throughput = u.throughput
        s.devices_online = u.devices_online
        s.last_active = nowText()
        const h = history[u.id] ?? (history[u.id] = [])
        h.push(u.throughput)
        if (h.length > HISTORY_MAX) h.splice(0, h.length - HISTORY_MAX)
      }
      touch()
    }),
    rt.on('traffic.updated', (d) => {
      const byId = new Map(roads.value.map((r) => [r.id, r]))
      for (const u of d.roads) {
        const r = byId.get(u.id)
        if (!r) continue
        r.speed = u.speed
        r.tpi = u.tpi
        r.level = u.level
      }
      cityTpi.value = d.city_tpi
      touch()
    })
  )
  clock = window.setInterval(() => (now.value = Date.now()), 1000)
})

onBeforeUnmount(() => {
  unsubs.forEach((u) => u())
  window.clearInterval(clock)
})
</script>

<template>
  <PageShell title="城市监测" hint="监测区域概况、多源感知数据实时吞吐、路网拥堵态势与建筑沉降安全一屏掌握">
    <RegionHeader
      :info="info"
      :building-count="buildings.length"
      :road-count="roadNameCount"
      :segment-count="roads.length"
      :devices-online="devicesOnline"
      :devices-total="devicesTotal"
      :updated-at="updatedAt"
      :age-sec="ageSec"
      :live="connected"
      :loading="loading"
    />

    <section>
      <h3 class="sec-label">
        数据来源 <small>{{ sources.length }} 类感知源</small>
      </h3>
      <div v-if="loading && !sources.length" class="sources">
        <el-skeleton v-for="i in 4" :key="i" animated class="cp-panel sk"
          ><template #template><el-skeleton-item variant="rect" style="height: 168px" /></template
        ></el-skeleton>
      </div>
      <el-empty v-else-if="!sources.length" class="cp-panel" :image-size="72" description="暂无数据源信息" />
      <div v-else class="sources">
        <SourceCard v-for="s in sources" :key="s.id" :source="s" :history="history[s.id] ?? []" :now="now" />
      </div>
    </section>

    <div class="lower">
      <TrafficPanel :roads="roads" :city-tpi="cityTpi" :loading="loading" :live="connected" />
      <BuildingSafetyPanel :buildings="monitored" :loading="loading" />
    </div>
  </PageShell>
</template>

<style scoped>
.sec-label {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0;
  color: var(--ce-text);
}
.sec-label::before {
  align-self: center;
  content: '';
  width: 3px;
  height: 14px;
  background: var(--ce-accent, #4fc3f7);
}
.sec-label small {
  font-size: 12px;
  font-weight: 400;
  letter-spacing: 0;
  color: var(--ce-text-faint);
}
.sources {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 14px;
}
.sk {
  padding: 4px;
}
.lower {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}
@media (min-width: 1900px) {
  .lower {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
}
</style>
