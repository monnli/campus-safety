<template>
  <div class="alarm-overlay">
    <div class="alarm-box">
      <div class="alarm-header">
        <el-icon size="32" color="#ff4d4f"><Warning /></el-icon>
        <span>安全预警</span>
      </div>
      <div class="alarm-body">
        <div class="alarm-row">
          <span class="label">地点</span>
          <span class="value">{{ alarm.camera_name }}</span>
        </div>
        <div class="alarm-row">
          <span class="label">行为</span>
          <el-tag type="danger">{{ alarm.behavior }}</el-tag>
        </div>
        <div class="alarm-row">
          <span class="label">时间</span>
          <span class="value">{{ alarm.timestamp?.slice(11, 19) }}</span>
        </div>
        <div class="alarm-row">
          <span class="label">等级</span>
          <el-tag :type="alarm.level === 'HIGH' ? 'danger' : 'warning'">{{ alarm.level }}</el-tag>
        </div>
      </div>
      <div class="alarm-footer">
        <el-button type="danger" @click="$emit('close')">确认知晓</el-button>
        <el-button @click="$emit('close')">稍后处理</el-button>
      </div>
    </div>
    <!-- 警报音效 -->
    <audio ref="alarmAudio" src="/alarm.mp3" autoplay loop />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

defineProps(['alarm'])
defineEmits(['close'])

const alarmAudio = ref(null)

onMounted(() => {
  // 尝试播放警报音
  alarmAudio.value?.play().catch(() => {})
})

onUnmounted(() => {
  alarmAudio.value?.pause()
})
</script>

<style scoped>
.alarm-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
  animation: flash 0.5s infinite alternate;
}

@keyframes flash {
  from { background: rgba(0,0,0,0.7); }
  to { background: rgba(255,0,0,0.15); }
}

.alarm-box {
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  width: 400px;
  border: 3px solid #ff4d4f;
  box-shadow: 0 0 40px rgba(255,77,79,0.5);
}

.alarm-header {
  display: flex; align-items: center; gap: 12px;
  font-size: 22px; font-weight: 700; color: #ff4d4f;
  margin-bottom: 24px;
}

.alarm-row {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 14px;
}

.label { color: #999; width: 40px; flex-shrink: 0; }
.value { font-weight: 600; color: #333; }

.alarm-footer {
  display: flex; gap: 12px; justify-content: flex-end;
  margin-top: 24px;
}
</style>
