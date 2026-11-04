<script setup lang="ts">
// 城市治理助手：受控多轮问答，可选关联当前事件；只在用户发送时调用付费 API。
import { computed, nextTick, ref, watch } from 'vue'
import { ChatDotRound, Delete, Promotion } from '@element-plus/icons-vue'
import { apiState } from '@/api/http'
import { chatWithAssistant } from '@/api/llm'
import { errMsg } from '@/composables/pages/format'
import type { AssistantTurn } from '@/types/llm'

const props = defineProps<{ eventId?: string | null }>()

const messages = ref<AssistantTurn[]>([])
const input = ref('')
const busy = ref(false)
const error = ref('')
const dataType = ref('')
const scroller = ref<HTMLDivElement | null>(null)

const offline = computed(() => apiState.mode !== 'live')
const linked = computed(() => Boolean(props.eventId))
const canSend = computed(() => Boolean(input.value.trim()) && !busy.value && !offline.value)
const promptExamples = computed(() =>
  linked.value
    ? ['这起事件目前有哪些未知信息？', '周边设施会带来哪些处置关注点？']
    : ['CityEye 的四类城市风险分别是什么？', '发生内涝时，研判需要哪些信息？']
)

type AnswerBlock = { kind: 'heading' | 'text'; text: string }

function answerBlocks(content: string): AnswerBlock[] {
  return content
    .split('\n')
    .filter((line) => line.trim())
    .map((line) => {
      const heading = line.match(/^#{1,6}\s+(.+)$/)
      const text = heading?.[1] ?? line
      return { kind: heading ? 'heading' : 'text', text: text.replace(/\*\*(.+?)\*\*/g, '$1') }
    })
}

async function scrollToBottom() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

function usePrompt(text: string) {
  input.value = text
  void nextTick(() => document.querySelector<HTMLTextAreaElement>('.ac__input textarea')?.focus())
}

async function send() {
  const text = input.value.trim()
  if (!text || busy.value || offline.value) return
  error.value = ''
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  busy.value = true
  await scrollToBottom()
  try {
    const reply = await chatWithAssistant(messages.value.slice(-8), props.eventId)
    messages.value.push({ role: 'assistant', content: reply.answer })
    dataType.value = reply.data_type ?? ''
    await scrollToBottom()
  } catch (e) {
    messages.value.pop()
    input.value = text
    error.value = errMsg(e, '治理助手暂时无法回答，请稍后重试')
  } finally {
    busy.value = false
  }
}

function clearChat() {
  messages.value = []
  input.value = ''
  error.value = ''
  dataType.value = ''
}

watch(
  () => props.eventId,
  () => clearChat()
)
</script>

<template>
  <section class="ac">
    <div class="ac__context">
      <el-icon><ChatDotRound /></el-icon>
      <span>{{ linked ? `已关联事件 ${eventId}` : '未关联具体事件，可询问一般城市治理问题' }}</span>
      <span v-if="dataType" class="ac__data">{{ dataType }}</span>
      <button v-if="messages.length" class="ac__clear" type="button" :disabled="busy" @click="clearChat">
        <el-icon><Delete /></el-icon>清空
      </button>
    </div>

    <div ref="scroller" class="ac__messages" aria-live="polite">
      <div v-if="!messages.length" class="ac__empty">
        <p>只基于你提供的信息和关联事件作答；信息不足时会明确列为未知。</p>
        <div class="ac__prompts">
          <button v-for="p in promptExamples" :key="p" type="button" @click="usePrompt(p)">{{ p }}</button>
        </div>
      </div>
      <article
        v-for="(message, index) in messages"
        :key="index"
        class="ac__message"
        :class="`is-${message.role}`"
      >
        <span class="ac__role">{{ message.role === 'user' ? '你' : 'CityEye' }}</span>
        <p v-if="message.role === 'user'">{{ message.content }}</p>
        <div v-else class="ac__answer">
          <template v-for="(block, blockIndex) in answerBlocks(message.content)" :key="blockIndex">
            <strong v-if="block.kind === 'heading'">{{ block.text }}</strong>
            <p v-else>{{ block.text }}</p>
          </template>
        </div>
      </article>
      <div v-if="busy" class="ac__message is-assistant ac__message--busy">
        <span class="ac__role">CityEye</span>
        <p>正在整理已知信息与信息缺口…</p>
      </div>
    </div>

    <p v-if="offline" class="ac__hint">离线模式：治理助手需要后端和大模型服务在线。</p>
    <p v-else-if="error" class="ac__hint ac__hint--error">{{ error }}</p>

    <div class="ac__composer">
      <el-input
        v-model="input"
        class="ac__input"
        type="textarea"
        :rows="3"
        maxlength="2000"
        resize="none"
        placeholder="询问事件、所需信息或处置关注点；Ctrl + Enter 发送"
        :disabled="offline"
        @keydown.ctrl.enter.prevent="send"
      />
      <div class="ac__send-row">
        <span>回答用于辅助研判，不替代部门的正式判断与指令。</span>
        <el-button type="primary" :icon="Promotion" :loading="busy" :disabled="!canSend" @click="send">
          发送
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.ac {
  display: flex;
  flex-direction: column;
  min-height: 500px;
  height: min(68vh, 620px);
  border: 1px solid var(--ce-panel-border);
  background: var(--ce-panel-solid);
}
.ac__context {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 0 12px;
  border-bottom: 1px solid var(--ce-divider);
  font-size: 12px;
  color: var(--ce-text-dim);
}
.ac__data {
  margin-left: auto;
  color: #f0c050;
}
.ac__clear {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border: 0;
  background: transparent;
  color: var(--ce-text-dim);
  font-size: 12px;
  cursor: pointer;
}
.ac__messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px;
  scroll-behavior: smooth;
}
.ac__empty {
  max-width: 480px;
  margin: 18px auto;
  color: var(--ce-text-dim);
}
.ac__empty > p {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.7;
}
.ac__prompts {
  display: grid;
  gap: 8px;
}
.ac__prompts button {
  padding: 10px 12px;
  border: 1px solid var(--ce-panel-border);
  background: #1b1d20;
  color: var(--ce-text);
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}
.ac__prompts button:hover,
.ac__prompts button:focus-visible {
  color: var(--ce-text-strong);
  border-color: var(--ce-accent);
  background: #202225;
}
.ac__message {
  max-width: 88%;
  margin-bottom: 14px;
}
.ac__message.is-user {
  margin-left: auto;
}
.ac__role {
  display: block;
  margin-bottom: 5px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: var(--ce-text-dim);
}
.ac__message p {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--ce-panel-border);
  background: #1a1c1e;
  color: var(--ce-text);
  font-size: 13px;
  line-height: 1.75;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.ac__message.is-user p {
  border-color: rgba(79, 195, 247, 0.35);
  background: #1c2225;
  color: #e5f6ff;
}
.ac__answer {
  padding: 10px 12px;
  border: 1px solid var(--ce-panel-border);
  background: #1a1c1e;
  color: var(--ce-text);
  font-size: 13px;
  line-height: 1.75;
}
.ac__answer strong {
  display: block;
  margin: 9px 0 3px;
  color: var(--ce-text-strong);
  font-size: 12px;
}
.ac__answer strong:first-child {
  margin-top: 0;
}
.ac__answer p {
  padding: 0;
  border: 0;
  background: transparent;
}
.ac__answer p + strong {
  margin-top: 12px;
}
.ac__message--busy p {
  color: var(--ce-text-dim);
}
.ac__hint {
  margin: 0;
  padding: 0 14px 8px;
  font-size: 12px;
  color: var(--ce-text-dim);
}
.ac__hint--error {
  color: #ff9a7a;
}
.ac__composer {
  padding: 12px;
  border-top: 1px solid var(--ce-divider);
}
.ac__send-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
}
.ac__send-row > span {
  font-size: 11px;
  color: var(--ce-text-dim);
}
@media (max-width: 640px) {
  .ac {
    min-height: 430px;
    height: calc(100vh - 150px);
  }
  .ac__context {
    flex-wrap: wrap;
    padding-block: 8px;
  }
  .ac__data {
    margin-left: 0;
  }
  .ac__message {
    max-width: 96%;
  }
  .ac__send-row > span {
    display: none;
  }
  .ac__send-row {
    justify-content: flex-end;
  }
}
</style>
