<template>
  <div class="login-page">
    <!-- 动态背景 -->
    <canvas ref="canvas" class="bg-canvas"></canvas>

    <!-- 登录卡片 -->
    <div class="login-box">
      <div class="login-logo">
        <el-icon size="48" color="#1677ff"><VideoCamera /></el-icon>
        <h2>校园安全智能监控系统</h2>
        <p class="slogan">守护每一个孩子的平安成长</p>
        <div class="key-stats">
          <div class="stat-item"><span class="stat-val">&lt;3s</span><span class="stat-desc">响应时间</span></div>
          <div class="stat-item"><span class="stat-val">&lt;5%</span><span class="stat-desc">误报率</span></div>
          <div class="stat-item"><span class="stat-val">24h</span><span class="stat-desc">全天守护</span></div>
          <div class="stat-item"><span class="stat-val">90%</span><span class="stat-desc">带宽节省</span></div>
        </div>
      </div>

      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-button type="primary" size="large" style="width:100%" :loading="loading" @click="handleLogin">
          登录
        </el-button>
      </el-form>

      <div class="login-footer">
        黔视护苗 · AI Safety Guardian
        <div class="privacy-note">
          <el-icon size="12"><Lock /></el-icon>
          本系统仅分析行为模式，不采集人脸信息，符合个人信息保护法规
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const canvas = ref(null)

async function handleLogin() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await axios.post('/api/login', form.value)
    authStore.setUser(data)
    router.push('/monitor')
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '登录失败')
  } finally {
    loading.value = false
  }
}

// 粒子动画
let animId = null
function initParticles() {
  const c = canvas.value
  if (!c) return
  const ctx = c.getContext('2d')
  c.width = window.innerWidth
  c.height = window.innerHeight

  const particles = Array.from({ length: 80 }, () => ({
    x: Math.random() * c.width,
    y: Math.random() * c.height,
    r: Math.random() * 2 + 1,
    vx: (Math.random() - 0.5) * 0.6,
    vy: (Math.random() - 0.5) * 0.6,
    alpha: Math.random() * 0.5 + 0.2,
  }))

  function draw() {
    ctx.clearRect(0, 0, c.width, c.height)
    particles.forEach(p => {
      p.x += p.vx
      p.y += p.vy
      if (p.x < 0 || p.x > c.width) p.vx *= -1
      if (p.y < 0 || p.y > c.height) p.vy *= -1

      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(100,180,255,${p.alpha})`
      ctx.fill()
    })

    // 连线
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x
        const dy = particles[i].y - particles[j].y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 120) {
          ctx.beginPath()
          ctx.moveTo(particles[i].x, particles[i].y)
          ctx.lineTo(particles[j].x, particles[j].y)
          ctx.strokeStyle = `rgba(100,180,255,${0.15 * (1 - dist / 120)})`
          ctx.lineWidth = 0.8
          ctx.stroke()
        }
      }
    }
    animId = requestAnimationFrame(draw)
  }
  draw()

  window.addEventListener('resize', () => {
    c.width = window.innerWidth
    c.height = window.innerHeight
  })
}

onMounted(initParticles)
onUnmounted(() => { if (animId) cancelAnimationFrame(animId) })
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #020e1f 0%, #0a2a4a 50%, #001529 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.bg-canvas {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login-box {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  padding: 48px 40px 32px;
  width: 420px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255,255,255,0.1);
}

.login-logo { text-align: center; margin-bottom: 32px; }

.login-logo h2 {
  font-size: 20px;
  color: #001529;
  margin: 12px 0 4px;
  font-weight: 700;
}

.slogan { font-size: 14px; color: #1677ff; font-weight: 500; margin: 4px 0 16px; }

.key-stats { display: flex; gap: 10px; justify-content: center; margin-bottom: 4px; }
.stat-item { text-align: center; background: #f0f7ff; border-radius: 8px; padding: 6px 12px; }
.stat-val { display: block; font-size: 15px; font-weight: 700; color: #1677ff; }
.stat-desc { display: block; font-size: 11px; color: #999; margin-top: 1px; }

.login-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 12px;
  color: #bbb;
  letter-spacing: 1px;
}
.privacy-note {
  display: flex; align-items: center; justify-content: center; gap: 4px;
  margin-top: 6px; font-size: 11px; color: #52c41a;
}
</style>
