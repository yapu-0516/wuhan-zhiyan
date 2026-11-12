<script setup lang="ts">
// 自然语言任务解析面板：一句话 → DeepSeek 解析为结构化任务（POST /api/llm/parse-task）
// 付费 API，仅在点击「解析」时触发；离线 / 快照模式下禁用。
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import { apiState } from '@/api/http'
import { parseTaskText } from '@/api/llm'
import { errMsg } from '@/composables/pages/format'
import type { EventType } from '@/types/event'
import { EVENT_TYPE_META } from '@/types/event'
import { ANALYSIS_TARGET_LABEL, type ParsedTask } from '@/types/llm'

const props = defineProps<{ compact?: boolean; applyable?: boolean }>()
const emit = defineEmits<{
  (e: 'goto', type: EventType): void
  (e: 'apply', payload: { task: ParsedTask; text: string }): void
}>()

const text = ref('')
const busy = ref(false)
const result = ref<ParsedTask | null>(null)
const error = ref('')

const offline = computed(() => apiState.mode !== 'live')
const knownType = computed(() =>
  result.value && result.value.event_type !== 'unknown' ? (result.value.event_type as EventType) : null
)

async function run() {
  const q = text.value.trim()
  if (q.length < 2) {
    ElMessage.warning('请先输入要分析的任务描述')
    return
  }
  busy.value = true
  error.value = ''
  try {
    result.value = await parseTaskText(q)
  } catch (e) {
    result.value = null
    error.value = errMsg(e, '解析失败，请稍后重试')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section class="tp" :class="{ 'cp-panel': !props.compact }">
    <div v-if="!props.compact" class="cp-panel__header">
      <h3 class="cp-panel__title">自然语言任务解析</h3>
      <span class="cp-panel__sub">DeepSeek · 点击才触发</span>
    </div>
    <div :class="{ 'cp-panel__body': !props.compact }">
      <div class="tp__row">
        <el-input
          v-model="text"
          class="tp__input"
          placeholder="例如：帮我分析一起火灾的影响，重点关注周边医院和道路"
          maxlength="500"
          :disabled="offline"
          @keyup.enter="run"
        />
        <el-button type="primary" :icon="MagicStick" :loading="busy" :disabled="offline" @click="run">
          {{ busy ? '解析中…' : '解析' }}
        </el-button>
      </div>
      <p v-if="offline" class="tp__hint">离线演示模式：大模型服务需要后端在线。</p>
      <p v-else-if="error" class="tp__hint tp__hint--err">{{ error }}</p>

      <div v-if="result" class="tp__result">
        <div class="tp__line">
          <span class="cp-label">事件类型</span>
          <template v-if="knownType">
            <span class="tp__type" :style="{ '--c': EVENT_TYPE_META[knownType].color }">
              {{ EVENT_TYPE_META[knownType].icon }} {{ EVENT_TYPE_META[knownType].label }}
            </span>
            <el-button size="small" type="primary" plain @click="emit('goto', knownType!)">
              前往{{ EVENT_TYPE_META[knownType].label }}场景
            </el-button>
            <el-button
              v-if="props.applyable"
              size="small"
              type="primary"
              @click="emit('apply', { task: result, text })"
            >
              填入任务表单
            </el-button>
          </template>
          <span v-else class="tp__unknown">未识别（需要补充事件类型）</span>
          <el-tag v-if="result.needs_clarification" type="warning" size="small" effect="dark">需要补充信息</el-tag>
        </div>

        <div v-if="result.analysis_targets.length" class="tp__line">
          <span class="cp-label">分析目标</span>
          <span v-for="t in result.analysis_targets" :key="t" class="tp__tag">{{ ANALYSIS_TARGET_LABEL[t] ?? t }}</span>
        </div>

        <div v-if="result.location || result.event_time" class="tp__line">
          <span class="cp-label">地点 / 时间</span>
          <span class="tp__val">{{ result.location ?? '未提供' }} · {{ result.event_time ?? '未提供' }}</span>
        </div>

        <div v-if="Object.keys(result.extracted_facts).length" class="tp__line tp__line--top">
          <span class="cp-label">已提取事实</span>
          <dl class="tp__facts">
            <template v-for="(v, k) in result.extracted_facts" :key="k">
              <dt>{{ k }}</dt>
              <dd>{{ v }}</dd>
            </template>
          </dl>
        </div>

        <div v-if="result.missing_information.length" class="tp__line tp__line--top">
          <span class="cp-label">缺失信息</span>
          <ul class="tp__missing">
            <li v-for="m in result.missing_information" :key="m">{{ m }}</li>
          </ul>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tp__row {
  display: flex;
  gap: 10px;
}
.tp__input {
  flex: 1 1 auto;
}
.tp__hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #6f89aa;
}
.tp__hint--err {
  color: #ff9a7a;
}
.tp__result {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed rgba(64, 120, 180, 0.3);
}
.tp__line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.tp__line--top {
  align-items: flex-start;
}
.tp__line .cp-label {
  flex: none;
  width: 64px;
}
.tp__type {
  --c: #4fc3f7;
  padding: 2px 10px;
  font-size: 12.5px;
  border-radius: 999px;
  color: var(--c);
  border: 1px solid color-mix(in srgb, var(--c) 55%, transparent);
  background: color-mix(in srgb, var(--c) 12%, transparent);
}
.tp__unknown {
  font-size: 12.5px;
  color: #f0c050;
}
.tp__tag {
  padding: 1px 8px;
  font-size: 12px;
  border-radius: 4px;
  color: #a9cdf0;
  background: rgba(79, 195, 247, 0.08);
  border: 1px solid rgba(64, 120, 180, 0.3);
}
.tp__val {
  font-size: 12.5px;
  color: #b9cdec;
}
.tp__facts {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3px 12px;
  margin: 0;
  font-size: 12.5px;
}
.tp__facts dt {
  color: #7f98b8;
}
.tp__facts dd {
  margin: 0;
  color: #d6e4ff;
}
.tp__missing {
  margin: 0;
  padding-left: 16px;
  font-size: 12.5px;
  line-height: 1.7;
  color: #f0c050;
}
</style>
