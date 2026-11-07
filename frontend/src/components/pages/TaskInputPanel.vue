<script setup lang="ts">
// 分析输入面板：示例数据 / 上传数据 两种输入 + 关联位置 + 自动建事件开关 + 开始分析
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadInstance, UploadUserFile } from 'element-plus'
import { Aim, UploadFilled, VideoPlay } from '@element-plus/icons-vue'
import { getSamples } from '@/api/task'
import { errMsg } from '@/composables/pages/format'
import { isCsvFile, isImageFile, typeMeta, validateFiles } from '@/composables/pages/aiMeta'
import type { SubmitPayload } from '@/composables/pages/aiMeta'
import type { Sample } from '@/types/api'
import type { EventType } from '@/types/event'
import SampleGallery from './SampleGallery.vue'

const props = defineProps<{
  type: EventType
  busy: boolean
  /** 区域中心 [lon, lat]，作为关联位置默认值 */
  center: [number, number]
}>()
const emit = defineEmits<{ (e: 'submit', p: SubmitPayload): void }>()

const meta = computed(() => typeMeta(props.type)!)
const tab = ref<'samples' | 'upload'>('samples')
const samples = ref<Sample[]>([])
const loadingSamples = ref(false)
const selectedId = ref('')
const fileList = ref<UploadUserFile[]>([])
const uploadRef = ref<UploadInstance>()
const longitude = ref<number | null>(props.center[0])
const latitude = ref<number | null>(props.center[1])
const createEvent = ref(true)

async function loadSamples() {
  loadingSamples.value = true
  const t = props.type
  try {
    const list = await getSamples(t)
    if (t === props.type) samples.value = list
  } catch (e) {
    samples.value = []
    ElMessage.warning(errMsg(e, '示例数据加载失败'))
  } finally {
    loadingSamples.value = false
  }
}

function useCenter() {
  longitude.value = props.center[0]
  latitude.value = props.center[1]
}

watch(
  () => props.type,
  () => {
    selectedId.value = ''
    fileList.value = []
    samples.value = []
    useCenter()
    void loadSamples()
  },
  { immediate: true }
)

// 区域中心异步到达时，若用户尚未选择示例，则同步默认位置
watch(
  () => props.center,
  () => {
    if (!selectedId.value) useCenter()
  }
)

function pick(s: Sample) {
  selectedId.value = selectedId.value === s.id ? '' : s.id
  if (selectedId.value) {
    longitude.value = s.longitude ?? props.center[0]
    latitude.value = s.latitude ?? props.center[1]
  }
}

// ---------- 上传 ----------
const allowedExt = computed(() => meta.value.accept.split(','))
const uploadError = computed(() =>
  fileList.value.length
    ? validateFiles(
        props.type,
        fileList.value.map((f) => f.name)
      )
    : null
)

function onFileChange(file: UploadFile) {
  const ok = isImageFile(file.name) || (isCsvFile(file.name) && allowedExt.value.includes('.csv'))
  if (!ok) {
    ElMessage.warning(`「${file.name}」格式不受支持：${meta.value.rule}`)
    uploadRef.value?.handleRemove(file)
  }
}
function onExceed() {
  ElMessage.warning(`最多可选择 ${meta.value.maxFiles} 个文件，请先移除已选文件`)
}

const rawFiles = computed(() => fileList.value.map((f) => f.raw as File | undefined).filter((f): f is File => !!f))

const ready = computed(() =>
  tab.value === 'samples' ? !!selectedId.value : !!rawFiles.value.length && !uploadError.value
)

function start() {
  if (!ready.value || props.busy) return
  const base = {
    type: props.type,
    longitude: longitude.value ?? undefined,
    latitude: latitude.value ?? undefined,
    createEvent: createEvent.value
  }
  emit(
    'submit',
    tab.value === 'samples' ? { ...base, sampleId: selectedId.value, files: [] } : { ...base, files: rawFiles.value }
  )
}
</script>

<template>
  <div class="tip" :style="{ '--c': meta.color }">
    <el-tabs v-model="tab" class="tip__tabs">
      <el-tab-pane label="示例数据" name="samples">
        <SampleGallery
          :samples="samples"
          :selected-id="selectedId"
          :loading="loadingSamples"
          :color="meta.color"
          @select="pick"
        />
      </el-tab-pane>
      <el-tab-pane label="上传数据" name="upload">
        <el-upload
          ref="uploadRef"
          v-model:file-list="fileList"
          class="tip__upload"
          drag
          multiple
          action="#"
          list-type="picture"
          :auto-upload="false"
          :accept="meta.accept"
          :limit="meta.maxFiles"
          :on-change="onFileChange"
          :on-exceed="onExceed"
        >
          <el-icon class="tip__upicon"><UploadFilled /></el-icon>
          <div class="tip__uptext">拖拽文件到此处，或 <em>点击选择</em></div>
          <template #tip>
            <div class="tip__rule" :class="{ 'is-bad': !!uploadError }">
              <template v-if="uploadError">上传错误：{{ uploadError }}</template>
              <template v-else-if="fileList.length"
                >已选择 {{ fileList.length }} 个文件，满足「{{ meta.label }}」输入要求</template
              >
              <template v-else>{{ meta.rule }}</template>
            </div>
          </template>
        </el-upload>
      </el-tab-pane>
    </el-tabs>

    <div class="tip__opts">
      <div class="tip__loc">
        <span class="cp-label">关联位置</span>
        <el-input-number
          v-model="longitude"
          :precision="6"
          :step="0.001"
          :controls="false"
          placeholder="经度"
          size="small"
        />
        <el-input-number
          v-model="latitude"
          :precision="6"
          :step="0.001"
          :controls="false"
          placeholder="纬度"
          size="small"
        />
        <el-button link type="primary" :icon="Aim" @click="useCenter">示范区中心</el-button>
      </div>
      <label class="tip__sw">
        <el-switch v-model="createEvent" />
        <span>检测到异常时自动生成事件</span>
        <small>事件将进入「事件中心」并在三维场景中标注</small>
      </label>
    </div>

    <el-button
      class="tip__go"
      type="primary"
      size="large"
      :icon="VideoPlay"
      :loading="busy"
      :disabled="!ready"
      @click="start"
    >
      {{ busy ? '分析进行中…' : '开始分析' }}
    </el-button>
  </div>
</template>

<style scoped>
.tip {
  --c: #4fc3f7;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.tip__tabs :deep(.el-tabs__header) {
  margin-bottom: 14px;
}
.tip__tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(64, 120, 180, 0.22);
}
.tip__tabs :deep(.el-tabs__item) {
  font-size: 14px;
  letter-spacing: 1px;
}
.tip__tabs :deep(.el-tabs__active-bar) {
  background: var(--c);
  box-shadow: 0 0 8px var(--c);
}
.tip__tabs :deep(.el-tabs__item.is-active) {
  color: var(--c);
}
.tip__upload :deep(.el-upload-dragger) {
  padding: 28px 16px;
  background: rgba(9, 16, 34, 0.5);
  border: 1px dashed rgba(79, 195, 247, 0.4);
  border-radius: 10px;
}
.tip__upload :deep(.el-upload-dragger:hover),
.tip__upload :deep(.el-upload-dragger.is-dragover) {
  border-color: var(--c);
  background: color-mix(in srgb, var(--c) 8%, rgba(9, 16, 34, 0.5));
}
.tip__upicon {
  font-size: 44px;
  color: var(--c);
  margin-bottom: 8px;
}
.tip__uptext {
  font-size: 14px;
  color: #b9cdec;
}
.tip__uptext em {
  font-style: normal;
  color: var(--c);
}
.tip__rule {
  margin-top: 8px;
  font-size: 12.5px;
  color: #8aa3c4;
}
.tip__rule.is-bad {
  color: #ff9f7a;
}
.tip__upload :deep(.el-upload-list__item) {
  background: rgba(9, 16, 34, 0.55);
  border-color: rgba(64, 120, 180, 0.3);
}
.tip__opts {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 9px;
  background: rgba(7, 12, 28, 0.5);
  border: 1px solid rgba(64, 120, 180, 0.2);
}
.tip__loc {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 10px;
}
.tip__loc .el-input-number {
  width: 140px;
}
.tip__sw {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 13px;
  color: #cfe0fa;
  cursor: pointer;
}
.tip__sw small {
  font-size: 12px;
  color: #6f89aa;
}
.tip .tip__go.el-button--primary {
  width: 100%;
  height: 46px;
  font-size: 16px;
  letter-spacing: 4px;
  border-radius: 10px;
  --el-button-bg-color: var(--c);
  --el-button-border-color: var(--c);
  --el-button-hover-bg-color: color-mix(in srgb, var(--c) 80%, #fff);
  --el-button-hover-border-color: color-mix(in srgb, var(--c) 80%, #fff);
  --el-button-active-bg-color: color-mix(in srgb, var(--c) 85%, #000);
  --el-button-active-border-color: color-mix(in srgb, var(--c) 85%, #000);
  box-shadow: 0 0 22px color-mix(in srgb, var(--c) 35%, transparent);
}
.tip .tip__go.el-button--primary.is-disabled {
  box-shadow: none;
  --el-button-disabled-text-color: rgba(4, 18, 31, 0.6);
}
</style>
