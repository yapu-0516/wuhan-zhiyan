<script setup lang="ts">
// 管理页面通用外壳：标题区 + 离线提示条 + 内容区，并加载共享主题样式。
// 页面根节点自带滚动（height:100%; overflow:auto），适配 1280 ~ 2560 宽度。
import { onMounted } from 'vue'
import './page-theme.css'
import ApiModeBanner from './ApiModeBanner.vue'

defineProps<{
  title: string
  hint?: string
  /** 离线提示条的补充说明 */
  bannerDetail?: string
}>()

onMounted(() => {
  // Element Plus 暗色变量依赖 html.dark；幂等添加，保证弹层/下拉也使用暗色主题
  document.documentElement.classList.add('dark')
})
</script>

<template>
  <div class="cp-page">
    <header class="cp-page__head">
      <div>
        <h2 class="cp-page__title">{{ title }}</h2>
        <p v-if="hint" class="cp-page__hint">{{ hint }}</p>
      </div>
      <div v-if="$slots.actions" class="cp-page__actions"><slot name="actions" /></div>
    </header>
    <ApiModeBanner :detail="bannerDetail" />
    <div class="cp-page__body"><slot /></div>
  </div>
</template>
