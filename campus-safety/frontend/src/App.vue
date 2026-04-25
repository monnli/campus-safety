<template>
  <!-- 大屏/登录页不走主布局，但告警弹窗需要全局可见 -->
  <router-view v-if="$route.meta.fullscreen || $route.meta.public" />

  <el-container v-else class="app-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <el-icon size="24"><VideoCamera /></el-icon>
        <span>校园安全系统</span>
      </div>
      <el-menu :router="true" :default-active="$route.path" background-color="#001529" text-color="#ffffffa0" active-text-color="#ffffff">
        <el-menu-item v-if="hasPermission('monitor')" index="/monitor">
          <el-icon><Monitor /></el-icon><span>实时监控</span>
        </el-menu-item>
        <el-menu-item v-if="hasPermission('events')" index="/events">
          <el-icon><Bell /></el-icon><span>事件记录</span>
          <el-badge v-if="pendingCount > 0" :value="pendingCount" class="badge" />
        </el-menu-item>
        <el-menu-item v-if="hasPermission('events')" index="/recordings">
          <el-icon><Film /></el-icon><span>历史录像</span>
        </el-menu-item>
        <el-menu-item v-if="hasPermission('stats')" index="/stats">
          <el-icon><DataAnalysis /></el-icon><span>数据统计</span>
        </el-menu-item>
        <el-menu-item v-if="hasPermission('chat')" index="/chat">
          <el-icon><ChatDotRound /></el-icon><span>智能查询</span>
        </el-menu-item>
        <el-menu-item v-if="hasPermission('events')" index="/patrol">
          <el-icon><Location /></el-icon><span>巡逻任务</span>
        </el-menu-item>
        <el-menu-item v-if="hasPermission('dashboard')" index="/drone">
          <el-icon><Promotion /></el-icon><span>无人机规划</span>
        </el-menu-item>
        <el-menu-item v-if="hasPermission('dashboard')" index="/dashboard">
          <el-icon><Monitor /></el-icon><span>安全大屏</span>
        </el-menu-item>
        <el-menu-item v-if="hasPermission('settings')" index="/settings">
          <el-icon><Setting /></el-icon><span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="page-title">{{ $route.meta.title }}</span>
        <div class="header-right">
          <el-tag :type="systemOnline ? 'success' : 'danger'" size="small">
            {{ systemOnline ? '系统运行中' : '系统离线' }}
          </el-tag>
          <span class="time">{{ currentTime }}</span>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              {{ authStore.user?.name }}（{{ authStore.user?.display }}）
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>

    <OnboardingGuide v-if="isLoggedIn" />
  </el-container>

  <!-- 告警弹窗：无论是否 fullscreen，都需要显示（但要求已登录） -->
  <AlarmDialog v-if="isLoggedIn && alarm" :alarm="alarm" @close="clearAlarm" />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import socket from './socket'
import AlarmDialog from './components/AlarmDialog.vue'
import OnboardingGuide from './components/OnboardingGuide.vue'
import { useAuthStore } from './stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const systemOnline = ref(false)
const currentTime = ref('')
const alarm = ref(null)
const pendingCount = ref(0)

const isLoggedIn = computed(() => authStore.isLoggedIn)
const hasPermission = (p) => authStore.hasPermission(p)

// 广播配置
const broadcastConfig = ref({ repeat_times: 3, custom_texts: {} })
async function loadBroadcastConfig() {
  try {
    const { data } = await axios.get('/api/broadcast/config')
    broadcastConfig.value = data
  } catch {}
}

function speakText(text, times) {
  if (!text || !window.speechSynthesis) return
  let count = 0
  function speak() {
    if (count >= times) return
    window.speechSynthesis.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = 'zh-CN'
    utter.rate = 0.9
    utter.volume = 1
    utter.onend = () => {
      count++
      if (count < times) setTimeout(speak, 800)
    }
    window.speechSynthesis.speak(utter)
    count++
  }
  speak()
}

let timer = null

function updateTime() {
  currentTime.value = new Date().toLocaleString('zh-CN')
}

function clearAlarm() { alarm.value = null }

function handleCommand(cmd) {
  if (cmd === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  loadBroadcastConfig()
  socket.on('connect', () => { systemOnline.value = true })
  socket.on('disconnect', () => { systemOnline.value = false })
  socket.on('new_event', (data) => {
    alarm.value = data.alarm
    pendingCount.value++
    const times = broadcastConfig.value.repeat_times || 3
    if (data.audio_path) {
      // TTS 音频：重复播放
      let count = 0
      function playAudio() {
        if (count >= times) return
        const audio = new Audio(`/static/alerts/${data.audio_path.split('/').pop()}`)
        audio.onended = () => { count++; if (count < times) setTimeout(playAudio, 800) }
        audio.play().catch(() => {})
        count++
      }
      playAudio()
    } else if (data.broadcast_text) {
      // 优先用自定义广播内容，没有则用AI生成的
      const behavior = data.event?.behavior || ''
      const customText = broadcastConfig.value.custom_texts?.[behavior]
      const text = customText || data.broadcast_text
      speakText(text, times)
    }
  })
})

onUnmounted(() => {
  clearInterval(timer)
  socket.off('new_event')
})
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #f0f2f5; font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }

.app-container { height: 100vh; }

.sidebar {
  background: #001529;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  border-bottom: 1px solid #ffffff15;
}

.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  height: 60px;
}

.page-title { font-size: 16px; font-weight: 600; color: #333; }

.header-right { display: flex; align-items: center; gap: 16px; }

.time { font-size: 13px; color: #666; }

.main-content { padding: 20px; overflow-y: auto; }

.user-info {
  cursor: pointer;
  font-size: 13px;
  color: #333;
  display: flex;
  align-items: center;
  gap: 4px;
}

.user-info:hover { color: #1677ff; }
</style>
