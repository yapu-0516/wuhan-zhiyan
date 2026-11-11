<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MapLocation } from '@element-plus/icons-vue'
import PageShell from '@/components/pages/PageShell.vue'
import ScenarioWorkspace from '@/components/pages/ScenarioWorkspace.vue'

const router = useRouter()
const route = useRoute()
const sourceEventId = computed(() => (typeof route.query.eventId === 'string' ? route.query.eventId : undefined))
</script>

<template>
  <PageShell
    title="情景推演"
    hint="用一句话建立假设，比较常规、不利与提前干预三种可能结果，并核对所用参数、数据性质与模型限制"
  >
    <template #actions>
      <el-button :icon="MapLocation" @click="router.push('/dashboard')">打开三维总览</el-button>
    </template>
    <section class="scenario-page">
      <ScenarioWorkspace
        :viewer="null"
        :source-event-id="sourceEventId"
        embedded
        @view-map="router.push('/dashboard')"
        @close="router.push('/dashboard')"
      />
    </section>
  </PageShell>
</template>

<style scoped>
.scenario-page {
  max-width: 1180px;
  min-height: 620px;
  margin: 0 auto;
  border: 1px solid var(--ce-panel-border);
  background: var(--ce-panel-solid);
}
</style>
