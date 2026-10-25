<script setup lang="ts">
// 实时事件流：最新在上，新事件滑入 + 高亮；左侧色条为事件等级；点击定位并打开详情
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { CityEvent } from '@/types/event'
import { EVENT_STATUS_COLOR, EVENT_STATUS_LABEL, EVENT_TYPE_META, SEVERITY_META } from '@/types/event'
import { relativeTime } from '@/utils/format'

const props = defineProps<{ events: CityEvent[]; selectedId?: string | null }>()
const emit = defineEmits<{ (e: 'locate', id: string): void }>()

const tab = ref<'all' | 'active'>('active')
const now = ref(Date.now())
let timer: number | undefined
onMounted(() => (timer = window.setInterval(() => (now.value = Date.now()), 30000)))
onBeforeUnmount(() => window.clearInterval(timer))

const sorted = computed(() =>
  [...(props.events ?? [])].sort((a, b) => b.timestamp.localeCompare(a.timestamp) || b.id.localeCompare(a.id))
)
const list = computed(() => (tab.value === 'active' ? sorted.value.filter((e) => e.status !== 'resolved') : sorted.value).slice(0, 40))
const activeCount = computed(() => sorted.value.filter((e) => e.status !== 'resolved').length)

// 新到达的事件高亮 6 秒
const fresh = ref(new Set<string>())
let known: Set<string> | null = null
watch(
  () => props.events.map((e) => e.id),
  (ids) => {
    if (!known) {
      known = new Set(ids)
      return
    }
    const added = ids.filter((id) => !known!.has(id))
    ids.forEach((id) => known!.add(id))
    if (!added.length) return
    const next = new Set(fresh.value)
    added.forEach((id) => next.add(id))
    fresh.value = next
    window.setTimeout(() => {
      const s = new Set(fresh.value)
      added.forEach((id) => s.delete(id))
      fresh.value = s
    }, 6000)
  },
  { immediate: true }
)
</script>

<template>
  <div class="feed">
    <div class="feed__tabs">
      <button :class="{ on: tab === 'active' }" @click="tab = 'active'">未办结 <b class="ce-num">{{ activeCount }}</b></button>
      <button :class="{ on: tab === 'all' }" @click="tab = 'all'">全部 <b class="ce-num">{{ sorted.length }}</b></button>
      <span class="feed__live"><i class="ce-dot ce-dot--pulse" />实时</span>
    </div>
    <TransitionGroup v-if="list.length" tag="ul" name="feed" class="feed__list">
      <li
        v-for="e in list"
        :key="e.id"
        class="feed__item"
        :class="{ 'is-new': fresh.has(e.id), 'is-sel': selectedId === e.id, 'is-done': e.status === 'resolved' }"
        :style="{ '--sev': SEVERITY_META[e.severity]?.color, '--type': EVENT_TYPE_META[e.event_type]?.color }"
        role="button"
        tabindex="0"
        :aria-label="`定位事件：${e.name}`"
        @click="emit('locate', e.id)"
        @keydown.enter.prevent="emit('locate', e.id)"
        @keydown.space.prevent="emit('locate', e.id)"
      >
        <span class="feed__icon">{{ EVENT_TYPE_META[e.event_type]?.icon }}</span>
        <div class="feed__main">
          <div class="feed__name" :title="e.name">{{ e.name }}</div>
          <div class="feed__meta">
            <span class="ce-num">{{ relativeTime(e.timestamp, now) }}</span>
            <span>{{ e.district || '—' }}</span>
            <span class="feed__sev">{{ SEVERITY_META[e.severity]?.short }}级</span>
          </div>
        </div>
        <span class="feed__status" :style="{ color: EVENT_STATUS_COLOR[e.status] }">{{ EVENT_STATUS_LABEL[e.status] }}</span>
      </li>
    </TransitionGroup>
    <div v-else class="feed__empty">暂无{{ tab === 'active' ? '未办结' : '' }}事件</div>
  </div>
</template>

<style scoped>
.feed {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.feed__tabs {
  display: flex;
  align-items: center;
  gap: 6px;
}
.feed__tabs button {
  height: 24px;
  padding: 0 10px;
  border: 1px solid var(--ce-divider);
  border-radius: 2px;
  background: transparent;
  color: var(--ce-text-dim);
  font-size: 12px;
  cursor: pointer;
}
.feed__tabs button b {
  margin-left: 2px;
  color: var(--ce-text);
}
.feed__tabs button.on {
  border-color: var(--ce-panel-border-strong);
  color: var(--ce-text-strong);
  background: rgba(79, 195, 247, 0.14);
}
.feed__live {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--ce-success);
}
.feed__list {
  position: relative;
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 0 2px 0 0;
  list-style: none;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.feed__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7px 8px 7px 11px;
  border: 1px solid transparent;
  border-radius: 3px;
  background: linear-gradient(90deg, rgba(79, 195, 247, 0.07), rgba(79, 195, 247, 0.02));
  cursor: pointer;
  transition:
    background 0.2s ease,
    border-color 0.2s ease;
}
.feed__item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 3px;
  border-radius: 2px;
  background: var(--sev);
  box-shadow: 0 0 8px var(--sev);
}
.feed__item:hover {
  border-color: var(--ce-panel-border);
  background: rgba(79, 195, 247, 0.12);
}
.feed__item.is-sel {
  border-color: var(--ce-panel-border-strong);
  background: rgba(79, 195, 247, 0.16);
}
.feed__item.is-new {
  animation: feed-flash 1.2s ease-in-out 3;
}
.feed__item.is-done {
  opacity: 0.6;
}
@keyframes feed-flash {
  0%,
  100% {
    background: linear-gradient(90deg, rgba(79, 195, 247, 0.07), rgba(79, 195, 247, 0.02));
  }
  50% {
    background: linear-gradient(90deg, color-mix(in srgb, var(--type) 35%, transparent), rgba(79, 195, 247, 0.04));
  }
}
.feed__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 14px;
  background: color-mix(in srgb, var(--type) 22%, #071124);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--type) 60%, transparent);
}
.feed__main {
  flex: 1;
  min-width: 0;
}
.feed__name {
  font-size: 13px;
  color: var(--ce-text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.feed__meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--ce-text-faint);
  white-space: nowrap;
}
.feed__sev {
  color: var(--sev);
}
.feed__status {
  flex: none;
  font-size: 11.5px;
}
.feed__empty {
  flex: 1;
  display: grid;
  place-items: center;
  font-size: 12px;
  color: var(--ce-text-faint);
}
.feed-enter-active {
  transition: all 0.5s var(--ce-ease);
}
.feed-leave-active {
  transition: all 0.3s ease;
  position: absolute;
  left: 0;
  right: 0;
}
.feed-enter-from {
  opacity: 0;
  transform: translateX(-24px);
}
.feed-leave-to {
  opacity: 0;
  transform: translateX(24px);
}
.feed-move {
  transition: transform 0.45s var(--ce-ease);
}
</style>
