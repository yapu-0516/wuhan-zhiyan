<script setup lang="ts">
// 上报事件对话框：人工 / 市民上报 → POST /api/events
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Aim } from '@element-plus/icons-vue'
import { createEvent } from '@/api/event'
import { getSystemInfo } from '@/api/system'
import { apiState } from '@/api/http'
import { useCityEvents } from '@/composables/useCityEvents'
import { errMsg } from '@/composables/pages/format'
import type { CityEvent, EventSource, EventType, Severity } from '@/types/event'
import { EVENT_TYPES, EVENT_TYPE_META, SEVERITY_META, SOURCE_META } from '@/types/event'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'created', ev: CityEvent): void
}>()

const FALLBACK_CENTER: [number, number] = [114.2955, 30.5895]
const center = ref<[number, number]>(FALLBACK_CENTER)
const bbox = ref<[number, number, number, number] | null>(null)

const formRef = ref<FormInstance>()
const submitting = ref(false)

interface FormState {
  event_type: EventType
  name: string
  longitude: number
  latitude: number
  severity: Severity
  source: EventSource
  description: string
}

const form = reactive<FormState>({
  event_type: 'fire',
  name: '',
  longitude: FALLBACK_CENTER[0],
  latitude: FALLBACK_CENTER[1],
  severity: 'medium',
  source: 'citizen',
  description: ''
})

const rules: FormRules<FormState> = {
  name: [
    { required: true, message: '请填写事件名称', trigger: 'blur' },
    { min: 2, max: 40, message: '名称长度应为 2~40 个字', trigger: 'blur' }
  ],
  longitude: [
    { type: 'number', required: true, min: -180, max: 180, message: '经度应在 -180 ~ 180 之间', trigger: 'change' }
  ],
  latitude: [
    { type: 'number', required: true, min: -90, max: 90, message: '纬度应在 -90 ~ 90 之间', trigger: 'change' }
  ]
}

const severityOptions = (Object.keys(SEVERITY_META) as Severity[]).map((k) => ({
  value: k,
  label: SEVERITY_META[k].short + ' ' + SEVERITY_META[k].label.replace(/^\S+\s/, '')
}))
const sourceOptions = (['citizen', 'drone', 'video', 'sensor', 'satellite'] as EventSource[]).map((k) => ({
  value: k,
  label: `${SOURCE_META[k].icon} ${SOURCE_META[k].label}`
}))

const outOfRegion = computed(() => {
  if (!bbox.value) return false
  const [w, s, e, n] = bbox.value
  return form.longitude < w || form.longitude > e || form.latitude < s || form.latitude > n
})

const offline = computed(() => apiState.mode !== 'live')

function useCenter() {
  form.longitude = center.value[0]
  form.latitude = center.value[1]
}

function reset() {
  form.event_type = 'fire'
  form.name = ''
  form.severity = 'medium'
  form.source = 'citizen'
  form.description = ''
  useCenter()
  formRef.value?.clearValidate()
}

async function loadRegion() {
  try {
    const info = await getSystemInfo()
    if (info.region?.center?.length === 2) {
      center.value = info.region.center
      if (!form.name) useCenter()
    }
    bbox.value = info.region?.bbox ?? null
  } catch {
    /* 沿用默认中心 */
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      reset()
      void loadRegion()
    }
  }
)

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    const created = await createEvent({
      event_type: form.event_type,
      name: form.name.trim(),
      longitude: Number(form.longitude),
      latitude: Number(form.latitude),
      severity: form.severity,
      source: form.source,
      description: form.description.trim() || undefined,
      confidence: 1.0
    })
    useCityEvents().upsert(created)
    ElMessage.success(`事件 ${created.id} 已上报，状态：待核查`)
    emit('created', created)
    emit('update:modelValue', false)
  } catch (e) {
    ElMessage.error(errMsg(e, '上报失败，请检查后端服务'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="上报事件"
    width="580px"
    modal-class="cp-overlay"
    :close-on-click-modal="false"
    destroy-on-close
    align-center
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
  >
    <el-alert
      v-if="offline"
      class="dlg-alert"
      type="warning"
      :closable="false"
      show-icon
      title="离线演示模式：无法提交事件上报，请先启动后端服务。"
    />
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
      <el-form-item label="事件类型" prop="event_type">
        <div class="types">
          <button
            v-for="t in EVENT_TYPES"
            :key="t"
            type="button"
            class="types__item"
            :class="{ 'is-on': form.event_type === t }"
            :style="{ '--c': EVENT_TYPE_META[t].color }"
            @click="form.event_type = t"
          >
            <span class="types__icon">{{ EVENT_TYPE_META[t].icon }}</span>
            <span>{{ EVENT_TYPE_META[t].label }}</span>
          </button>
        </div>
      </el-form-item>

      <el-form-item label="事件名称" prop="name">
        <el-input v-model="form.name" maxlength="40" show-word-limit placeholder="例如：江汉路步行街商铺疑似火情" />
      </el-form-item>

      <div class="row2">
        <el-form-item label="经度" prop="longitude">
          <el-input-number
            v-model="form.longitude"
            :precision="6"
            :step="0.001"
            :controls="false"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="纬度" prop="latitude">
          <el-input-number v-model="form.latitude" :precision="6" :step="0.001" :controls="false" style="width: 100%" />
        </el-form-item>
      </div>
      <div class="geo-tip">
        <el-button link type="primary" :icon="Aim" @click="useCenter">使用中心城区中心</el-button>
        <span v-if="outOfRegion" class="geo-tip__warn">坐标超出中心城区范围，三维场景中可能无法显示</span>
      </div>

      <div class="row2">
        <el-form-item label="事件等级">
          <el-segmented v-model="form.severity" :options="severityOptions" size="default" />
        </el-form-item>
        <el-form-item label="上报来源">
          <el-select v-model="form.source" popper-class="cp-popper" style="width: 100%">
            <el-option v-for="o in sourceOptions" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item label="事件描述">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          maxlength="200"
          show-word-limit
          placeholder="补充现场情况、影响范围等（选填）"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">提交上报</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dlg-alert {
  margin-bottom: 14px;
}
.types {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  width: 100%;
}
.types__item {
  --c: #4fc3f7;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 6px;
  border-radius: 8px;
  border: 1px solid rgba(64, 120, 180, 0.3);
  background: rgba(9, 16, 34, 0.6);
  color: var(--ce-text-dim, #8aa3c4);
  font-size: 12.5px;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease;
}
.types__icon {
  font-size: 22px;
  filter: grayscale(0.6);
  transition: filter 0.18s;
}
.types__item:hover {
  border-color: color-mix(in srgb, var(--c) 60%, transparent);
  color: var(--ce-text, #d6e4ff);
}
.types__item.is-on {
  border-color: var(--c);
  color: var(--c);
  background: color-mix(in srgb, var(--c) 14%, rgba(9, 16, 34, 0.6));
}
.types__item.is-on .types__icon {
  filter: none;
}
.row2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.geo-tip {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: -8px 0 12px;
  font-size: 12px;
}
.geo-tip__warn {
  color: #f0c050;
}
</style>
