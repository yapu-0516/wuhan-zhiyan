<script setup lang="ts">
// 示例数据画廊：图片示例显示缩略图，CSV 示例显示通用图表卡片
import { reactive } from 'vue'
import { Check, DataLine } from '@element-plus/icons-vue'
import { fileUrl } from '@/config/api'
import type { Sample } from '@/types/api'

defineProps<{ samples: Sample[]; selectedId: string; loading?: boolean; color: string }>()
const emit = defineEmits<{ (e: 'select', s: Sample): void }>()

const broken = reactive<Record<string, boolean>>({})
const KIND: Record<Sample['kind'], string> = { image: '影像', csv: 'CSV 时序', image_pair: '前后时相' }
</script>

<template>
  <div>
    <div v-if="loading" class="sg">
      <el-skeleton v-for="i in 3" :key="i" animated>
        <template #template><el-skeleton-item variant="image" style="width: 100%; height: 150px" /></template>
      </el-skeleton>
    </div>
    <el-empty v-else-if="!samples.length" :image-size="72" description="该分析类型暂无示例数据，请使用「上传数据」" />
    <div v-else class="sg" :style="{ '--c': color }">
      <button
        v-for="s in samples"
        :key="s.id"
        type="button"
        class="sc"
        :class="{ 'is-on': selectedId === s.id }"
        @click="emit('select', s)"
      >
        <div class="sc__thumb">
          <img
            v-if="s.kind !== 'csv' && s.thumbnail_url && !broken[s.id]"
            :src="fileUrl(s.thumbnail_url)"
            :alt="s.name"
            loading="lazy"
            @error="broken[s.id] = true"
          />
          <div v-else class="sc__chart">
            <el-icon><DataLine /></el-icon>
            <span>{{ s.kind === 'csv' ? 'CSV 时序数据' : '影像预览不可用' }}</span>
          </div>
          <span class="sc__kind">{{ KIND[s.kind] ?? s.kind }}</span>
          <span class="sc__check"><el-icon v-if="selectedId === s.id"><Check /></el-icon></span>
        </div>
        <div class="sc__txt">
          <b>{{ s.name }}</b>
          <span>{{ s.description }}</span>
        </div>
      </button>
    </div>
  </div>
</template>

<style scoped>
.sg {
  --c: #4fc3f7;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 12px;
}
.sc {
  display: flex;
  flex-direction: column;
  text-align: left;
  font: inherit;
  padding: 0;
  overflow: hidden;
  border-radius: 9px;
  cursor: pointer;
  color: var(--ce-text, #d6e4ff);
  background: rgba(9, 16, 34, 0.6);
  border: 1px solid rgba(64, 120, 180, 0.3);
  transition: all 0.18s;
}
.sc:hover {
  border-color: color-mix(in srgb, var(--c) 60%, transparent);
  transform: translateY(-1px);
}
.sc.is-on {
  border-color: var(--c);
  box-shadow:
    0 0 0 1px color-mix(in srgb, var(--c) 45%, transparent),
    0 0 20px color-mix(in srgb, var(--c) 28%, transparent);
}
.sc:focus-visible {
  outline: 2px solid var(--c);
  outline-offset: 2px;
}
.sc__thumb {
  position: relative;
  aspect-ratio: 16 / 10;
  background: #060b1a;
  overflow: hidden;
}
.sc__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s;
}
.sc:hover .sc__thumb img {
  transform: scale(1.04);
}
.sc__chart {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: #6f89aa;
  background:
    linear-gradient(rgba(79, 195, 247, 0.07) 1px, transparent 1px) 0 0 / 100% 22px,
    linear-gradient(90deg, rgba(79, 195, 247, 0.07) 1px, transparent 1px) 0 0 / 22px 100%,
    linear-gradient(135deg, rgba(79, 195, 247, 0.08), rgba(155, 143, 255, 0.06));
}
.sc__chart .el-icon {
  font-size: 34px;
  color: var(--c);
  opacity: 0.85;
}
.sc__kind {
  position: absolute;
  left: 8px;
  top: 8px;
  padding: 0 7px;
  line-height: 18px;
  font-size: 11px;
  border-radius: 4px;
  color: #dff3ff;
  background: rgba(6, 12, 28, 0.78);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(79, 195, 247, 0.35);
}
.sc__check {
  position: absolute;
  right: 8px;
  top: 8px;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  font-size: 13px;
  color: #06101f;
  background: rgba(6, 12, 28, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.3);
}
.sc.is-on .sc__check {
  background: var(--c);
  border-color: var(--c);
  box-shadow: 0 0 10px var(--c);
}
.sc__txt {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 9px 11px 11px;
}
.sc__txt b {
  font-size: 13px;
  font-weight: 600;
  color: #eaf2ff;
}
.sc__txt span {
  font-size: 12px;
  line-height: 1.5;
  color: #8aa3c4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
