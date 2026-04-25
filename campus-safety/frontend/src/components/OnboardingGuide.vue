<template>
  <el-dialog v-model="visible" title="欢迎使用校园安全智能监控系统" width="560px" :close-on-click-modal="false">
    <div class="guide-steps">
      <el-steps :active="step" direction="vertical" finish-status="success">
        <el-step title="接入视频源" description="在「实时监控」页面，点击摄像头格子中的「接入视频」按钮，上传视频文件或输入摄像头地址（0=电脑摄像头）" />
        <el-step title="查看实时检测" description="视频接入后，AI 自动开始检测危险行为。检测到异常时系统会弹出告警弹窗并播放广播" />
        <el-step title="查看事件记录" description="在「事件记录」页面查看所有告警事件，点击「详情」可查看 AI 分析报告和存档视频" />
        <el-step title="查看安全大屏" description="点击侧边栏「安全大屏」进入全屏可视化大屏，适合答辩展示和领导汇报" />
        <el-step title="AI 智能查询" description="在「智能查询」页面用自然语言提问，如「今天操场发生了几次异常？」" />
      </el-steps>
    </div>

    <div class="guide-tip">
      <el-icon color="#1677ff"><InfoFilled /></el-icon>
      <span>当前账号：<strong>{{ userName }}</strong>（{{ userDisplay }}）&nbsp;|&nbsp;API 不可用时系统自动切换 Mock 模式，演示不受影响</span>
    </div>

    <template #footer>
      <el-button v-if="step > 0" @click="step--">上一步</el-button>
      <el-button v-if="step < 4" type="primary" @click="step++">下一步</el-button>
      <el-button v-if="step === 4" type="primary" @click="finish">开始使用</el-button>
      <el-button text @click="finish">跳过引导</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const visible = ref(false)
const step = ref(0)

const userName = authStore.user?.name || ''
const userDisplay = authStore.user?.display || ''

function finish() {
  visible.value = false
  localStorage.setItem('guide_done', '1')
}

onMounted(() => {
  if (!localStorage.getItem('guide_done')) {
    setTimeout(() => { visible.value = true }, 500)
  }
})
</script>

<style scoped>
.guide-steps { padding: 8px 0 16px; }
.guide-tip {
  display: flex; align-items: center; gap: 8px;
  background: #e6f4ff; border-radius: 6px; padding: 10px 14px;
  font-size: 13px; color: #333;
}
</style>
