<script setup lang="ts">
// 事件研判报告主体（标题由 EventDrawer 的 .sec 提供）：点击生成 → POST /api/llm/report
// 输入为事件目录数据 + 周边 1km POI / 200m 道路；DeepSeek 付费 API，仅点击触发；离线禁用。
import { computed, ref, watch } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { apiState } from '@/api/http'
import { generateEventReport } from '@/api/llm'
import { errMsg } from '@/composables/pages/format'
import { RISK_META, type EventReport, type ReportFinding } from '@/types/llm'

const props = defineProps<{ eventId: string }>()

const report = ref<EventReport | null>(null)
const busy = ref(false)
const error = ref('')

const offline = computed(() => apiState.mode !== 'live')
const KIND_META: Record<ReportFinding['kind'], { label: string; cls: string }> = {
  fact: { label: '事实', cls: 'is-fact' },
  inference: { label: '推断', cls: 'is-infer' },
  unknown: { label: '未知', cls: 'is-unknown' }
}
const risk = computed(() => (report.value ? RISK_META[report.value.risk_assessment.level] : null))

async function run() {
  busy.value = true
  error.value = ''
  try {
    report.value = await generateEventReport(props.eventId)
  } catch (e) {
    report.value = null
    error.value = errMsg(e, '报告生成失败，请稍后重试')
  } finally {
    busy.value = false
  }
}

// 切换事件时清空上一份报告，避免串数据
watch(
  () => props.eventId,
  () => {
    report.value = null
    error.value = ''
    busy.value = false
  }
)
</script>

<template>
  <div class="er">
    <div v-if="!report" class="er__cta">
      <el-button type="primary" plain :icon="MagicStick" :loading="busy" :disabled="offline" @click="run">
        {{ busy ? '生成中…（约 5–20 秒）' : '生成研判报告' }}
      </el-button>
      <span class="er__hint">{{
        offline ? '离线模式：大模型服务需要后端在线' : 'DeepSeek 大模型 · 点击才触发 · 付费 API'
      }}</span>
      <p v-if="error" class="er__err">{{ error }}</p>
    </div>

    <template v-else>
      <div class="er__head">
        <b class="er__title">{{ report.report_title }}</b>
        <span v-if="risk" class="er__risk" :style="{ '--c': risk.color }">{{ risk.label }}</span>
        <el-button class="er__again" link :icon="MagicStick" :loading="busy" :disabled="offline" @click="run"
          >重新生成</el-button
        >
      </div>
      <p class="er__class">{{ report.data_classification }}</p>
      <p class="er__risk-stmt">{{ report.risk_assessment.statement }}</p>

      <div v-if="report.analysis_results.length" class="er__block">
        <span class="er__label">分析结论</span>
        <ul class="er__findings">
          <li v-for="(f, i) in report.analysis_results" :key="i">
            <span class="er__kind" :class="KIND_META[f.kind].cls">{{ KIND_META[f.kind].label }}</span>
            <div class="er__finding">
              <p>{{ f.statement }}</p>
              <small v-if="f.basis">依据：{{ f.basis }}</small>
            </div>
          </li>
        </ul>
      </div>

      <div v-if="report.recommendations.length" class="er__block">
        <span class="er__label">处置建议</span>
        <ol class="er__recs">
          <li v-for="(r, i) in report.recommendations" :key="i">{{ r }}</li>
        </ol>
      </div>

      <div v-if="report.data_gaps_and_uncertainty.length" class="er__block">
        <span class="er__label">数据缺口与不确定性</span>
        <ul class="er__gaps">
          <li v-for="(g, i) in report.data_gaps_and_uncertainty" :key="i">{{ g }}</li>
        </ul>
      </div>
    </template>
  </div>
</template>

<style scoped>
.er__cta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.er__hint {
  font-size: 12px;
  color: #5d748f;
}
.er__err {
  flex-basis: 100%;
  margin: 2px 0 0;
  font-size: 12.5px;
  color: #ff9a7a;
}
.er__head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.er__title {
  font-size: 13.5px;
  color: #e8f2ff;
}
.er__risk {
  --c: #8aa3c4;
  padding: 1px 10px;
  font-size: 12px;
  border-radius: 999px;
  color: var(--c);
  border: 1px solid color-mix(in srgb, var(--c) 55%, transparent);
  background: color-mix(in srgb, var(--c) 12%, transparent);
}
.er__again {
  margin-left: auto;
}
.er__class {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: #5d748f;
}
.er__risk-stmt {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: #c9d6ea;
}
.er__block {
  margin-top: 12px;
}
.er__label {
  display: block;
  margin-bottom: 6px;
  font-size: 11.5px;
  letter-spacing: 1px;
  color: #7f98b8;
}
.er__findings {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
}
.er__findings li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.er__kind {
  flex: none;
  margin-top: 1px;
  padding: 0 6px;
  font-size: 11px;
  line-height: 18px;
  border-radius: 4px;
}
.er__kind.is-fact {
  color: #4fc3f7;
  background: rgba(79, 195, 247, 0.12);
}
.er__kind.is-infer {
  color: #f0c050;
  background: rgba(240, 192, 80, 0.12);
}
.er__kind.is-unknown {
  color: #8aa3c4;
  background: rgba(138, 163, 196, 0.12);
}
.er__finding {
  min-width: 0;
}
.er__finding p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: #d6e4ff;
}
.er__finding small {
  font-size: 11.5px;
  color: #6f89aa;
}
.er__recs {
  margin: 0;
  padding-left: 18px;
  font-size: 12.5px;
  line-height: 1.8;
  color: #b9e6c8;
}
.er__gaps {
  margin: 0;
  padding-left: 16px;
  font-size: 12.5px;
  line-height: 1.8;
  color: #f0c050;
}
</style>
