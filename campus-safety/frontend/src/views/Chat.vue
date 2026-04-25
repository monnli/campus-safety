<template>
  <div class="chat-page">
    <el-card shadow="never" class="chat-card">
      <template #header>
        <span>智能安全助手</span>
        <span style="font-size:12px;color:#999;margin-left:8px">可用自然语言查询历史事件、分析安全态势</span>
      </template>

      <!-- 消息列表 -->
      <div class="message-list" ref="messageList">
        <div v-for="(msg, i) in messages" :key="i" class="message" :class="msg.role">
          <div class="avatar">
            <el-icon v-if="msg.role === 'assistant'"><Robot /></el-icon>
            <el-icon v-else><User /></el-icon>
          </div>
          <div class="bubble">
            <p class="text">{{ msg.content }}</p>
            <!-- 相关事件 -->
            <div v-if="msg.events && msg.events.length" class="related-events">
              <p class="related-title">相关事件：</p>
              <el-tag
                v-for="e in msg.events.slice(0,5)"
                :key="e.id"
                size="small"
                style="margin:2px"
              >
                {{ e.timestamp.slice(11,16) }} {{ e.camera_name }} {{ behaviorCn(e.behavior) }}
              </el-tag>
            </div>
          </div>
        </div>
        <div v-if="loading" class="message assistant">
          <div class="avatar"><el-icon><Robot /></el-icon></div>
          <div class="bubble"><el-icon class="loading-icon"><Loading /></el-icon> 正在分析...</div>
        </div>
      </div>

      <!-- 输入框 -->
      <div class="input-area">
        <el-input
          v-model="inputText"
          placeholder="例如：今天操场发生了几次打架？最近有哪些霸凌事件？"
          @keyup.enter="sendMessage"
          :disabled="loading"
        />
        <el-button type="primary" @click="sendMessage" :loading="loading">发送</el-button>
      </div>

      <!-- 快捷问题 -->
      <div class="quick-questions">
        <el-button size="small" text v-for="q in quickQuestions" :key="q" @click="quickAsk(q)">{{ q }}</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import axios from 'axios'

const messages = ref([
  { role: 'assistant', content: '你好，我是校园安全AI助手。你可以问我关于校园安全事件的任何问题，例如事件统计、区域分析、处置建议等。' }
])
const inputText = ref('')
const loading = ref(false)
const messageList = ref(null)

const behaviorCn = (b) => ({ fighting:'打架斗殴', bullying:'校园霸凌', falling:'人员跌倒', gathering:'异常聚集', intrusion:'陌生人入侵' }[b] || b)

const quickQuestions = [
  '今天发生了哪些事件？',
  '哪个区域最危险？',
  '最近有霸凌事件吗？',
  '给我一份安全建议',
]

async function sendMessage() {
  const q = inputText.value.trim()
  if (!q || loading.value) return

  messages.value.push({ role: 'user', content: q })
  inputText.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const { data } = await axios.post('/api/query', { query: q })
    messages.value.push({
      role: 'assistant',
      content: data.answer,
      events: data.related_events,
    })
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '查询失败，请稍后再试。' })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function quickAsk(q) {
  inputText.value = q
  sendMessage()
}

async function scrollToBottom() {
  await nextTick()
  if (messageList.value) {
    messageList.value.scrollTop = messageList.value.scrollHeight
  }
}
</script>

<style scoped>
.chat-page { height: calc(100vh - 120px); }

.chat-card { height: 100%; display: flex; flex-direction: column; }

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
  min-height: 400px;
  max-height: calc(100vh - 280px);
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  align-items: flex-start;
}

.message.user { flex-direction: row-reverse; }

.avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: #1677ff;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.message.user .avatar { background: #52c41a; }

.bubble {
  max-width: 70%;
  background: #f5f5f5;
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.7;
}

.message.user .bubble { background: #1677ff; color: #fff; }

.text { white-space: pre-wrap; }

.related-events { margin-top: 8px; }
.related-title { font-size: 12px; color: #999; margin-bottom: 4px; }

.input-area {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.quick-questions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.loading-icon { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
