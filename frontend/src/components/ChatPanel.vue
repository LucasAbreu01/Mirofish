<template>
  <div class="chat-panel">
    <div class="chat-header">
      <h3>Ask about the report</h3>
    </div>
    <div class="chat-messages" ref="messagesContainer">
      <div v-if="messages.length === 0" class="chat-empty">
        <p>Ask follow-up questions about the simulation report.</p>
      </div>
      <div
        v-for="(msg, index) in messages"
        :key="index"
        class="message"
        :class="msg.role === 'user' ? 'message-user' : 'message-assistant'"
      >
        <div class="message-bubble">
          {{ msg.content }}
        </div>
      </div>
      <div v-if="loading" class="message message-assistant">
        <div class="message-bubble typing">
          <span class="dot" /><span class="dot" /><span class="dot" />
        </div>
      </div>
    </div>
    <div class="chat-input">
      <input
        v-model="inputText"
        type="text"
        placeholder="Type a question..."
        @keydown.enter="sendMessage"
        :disabled="loading"
      />
      <button @click="sendMessage" :disabled="loading || !inputText.trim()">
        Send
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { chatWithReport } from '../api/report'

const props = defineProps({
  simulationId: {
    type: String,
    required: true
  }
})

const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const messagesContainer = ref(null)

async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const history = messages.value
      .filter(m => m.role !== undefined)
      .map(m => ({ role: m.role, content: m.content }))

    const response = await chatWithReport(props.simulationId, text, history)
    messages.value.push({
      role: 'assistant',
      content: response.answer || response.response || response.content || 'No response received.'
    })
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      content: 'Sorry, something went wrong. Please try again.'
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.chat-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.chat-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-messages::-webkit-scrollbar {
  width: 4px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 2px;
}

.chat-empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 30px 10px;
}

.message {
  display: flex;
}

.message-user {
  justify-content: flex-end;
}

.message-assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 85%;
  padding: 8px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  word-wrap: break-word;
}

.message-user .message-bubble {
  background: var(--accent);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.message-assistant .message-bubble {
  background: var(--bg-card);
  color: var(--text);
  border: 1px solid var(--border);
  border-bottom-left-radius: 4px;
}

.typing {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 10px 16px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.chat-input {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid var(--border);
}

.chat-input input {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
}

.chat-input input:focus {
  outline: none;
  border-color: var(--accent);
}

.chat-input input::placeholder {
  color: var(--text-muted);
}

.chat-input button {
  padding: 8px 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  font-weight: 600;
  white-space: nowrap;
}

.chat-input button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-input button:not(:disabled):hover {
  opacity: 0.9;
}
</style>
