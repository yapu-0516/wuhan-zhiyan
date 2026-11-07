<script setup lang="ts">
// 实时事件流：最新在上，新事件滑入 + 高亮；左侧色条为事件等级；点击定位并打开详情
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { CityEvent } from '@/types/event'
import { EVENT_STATUS_COLOR, EVENT_STATUS_LABEL, EVENT_TYPE_META, SEVERITY_META } from '@/types/event'
import { rankEventsByPriority } from '@/components/scene/eventPriority'
import { relativeTime } from '@/utils/format'

const props = defineProps<{ events: CityEvent[]; selectedId?: string | null }>()
const emit = defineEmits<{ (e: 'locate', id: string): void }>()

const tab = ref<'priority' | 'active' | 'all'>('priority')
const now = ref(Date.now())
let timer: number | undefined
onMounted(() => (timer = window.setInterval(() => (now.value = Date.now()), 30000)))
onBeforeUnmount(() => window.clearInterval(timer))

const sorted = computed(() =>
  [...(props.events ?? [])].sort((a, b) => b.timestamp.localeCompare(a.timestamp) || b.id.localeCompare(a.id))
)
const activeCount = computed(() => sorted.value.filter((e) => e.status !== 'resolved').length)
const activeEvents = computed(() => sorted.value.filter((e) => e.status !== 'resolved'))
const priorityEvents = computed(() => rankEventsByPriority(activeEvents.value, now.value))
const list = computed(() =>
  (tab.value === 'priority' ? priorityEvents.value : tab.value === 'active' ? activeEvents.value : sorted.value).slice(
    0,
    40
  )
)

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
      <button :class="{ on: tab === 'priority' }" :aria-pressed="tab === 'priority'" @click="tab = 'priority'">
        优先
      </button>
      <button :class="{ on: tab === 'active' }" :aria-pressed="tab === 'active'" @click="tab = 'active'">
        未办结 <b class="ce-num">{{ activeCount }}</b>
      </button>
      <button :class="{ on: tab === 'all' }" :aria-pressed="tab === 'all'" @click="tab = 'all'">
        全部 <b class="ce-num">{{ sorted.length }}</b>
      </button>
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
        <span class="feed__type-dot" />
        <div class="feed__main">
          <div class="feed__name" :title="e.name">{{ e.name }}</div>
          <div class="feed__meta">
            <span class="ce-num">{{ relativeTime(e.timestamp, now) }}</span>
            <span>{{ e.district || '—' }}</span>
            <span class="feed__sev">{{ SEVERITY_META[e.severity]?.short }}级</span>
          </div>
        </div>
        <span class="feed__status" :style="{ color: EVENT_STATUS_COLOR[e.status] }">{{
          EVENT_STATUS_LABEL[e.status]
        }}</span>
      </li>
    </TransitionGroup>
    <div v-else class="feed__empty">暂无{{ tab === 'priority' || tab === 'active' ? '未办结' : '' }}事件</div>
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
  gap: 12px;
  border-bottom: 1px solid var(--ce-divider);
}
.feed__tabs button {
  flex: none;
  height: 30px;
  padding: 0;
  border: 0;
  border-bottom: 1px solid transparent;
  border-radius: 0;
  background: transparent;
  color: var(--ce-text-dim);
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
}
.feed__tabs button b {
  margin-left: 2px;
  color: var(--ce-text);
}
.feed__tabs button.on {
  color: var(--ce-text-strong);
  border-bottom-color: var(--ce-accent);
}
.feed__live {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
  font-size: 12px;
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
  gap: 0;
}
.feed__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 7px 8px;
  border: 0;
  border-bottom: 1px solid var(--ce-divider);
  border-radius: 0;
  background: transparent;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    border-color 0.2s ease;
}
.feed__item:hover {
  background: #1b1d20;
}
.feed__item.is-sel {
  background: #1d1f22;
  border-left: 1px solid var(--ce-accent);
  padding-left: 7px;
}
.feed__item.is-new {
  animation: feed-flash 1.2s ease-in-out 2;
}
.feed__item.is-done {
  opacity: 0.6;
}
@keyframes feed-flash {
  0%,
  100% {
    background: transparent;
  }
  50% {
    background: #1d1f22;
  }
}
.feed__type-dot {
  flex: none;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--type);
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
  font-size: 12.5px;
  color: var(--ce-text-dim);
  white-space: nowrap;
}
.feed__sev {
  color: var(--sev);
}
.feed__status {
  flex: none;
  font-size: 12.5px;
}
.feed__empty {
  flex: 1;
  display: grid;
  place-items: center;
  font-size: 13px;
  color: var(--ce-text-faint);
}
.feed-enter-active {
  transition:
    opacity 0.3s ease,
    transform 0.3s var(--ce-ease);
}
.feed-leave-active {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
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
