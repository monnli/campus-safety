<template>
  <div class="monitor-page" :class="{ fullscreen: isFullscreen }">
    <el-card shadow="never" class="monitor-card">
      <template #header>
        <span>实时视频监控</span>
        <div style="float:right; display:flex; gap:8px; align-items:center">
          <el-button size="small" @click="loadCameras">刷新状态</el-button>
          <el-button size="small" type="primary" :icon="'Plus'" @click="openAddDialog">添加摄像头</el-button>
          <el-button size="small" :icon="isFullscreen ? 'Aim' : 'FullScreen'" @click="toggleFullscreen">
            {{ isFullscreen ? '退出全屏' : '全屏' }}
          </el-button>
        </div>
      </template>

      <!-- 视频网格 -->
      <div class="video-grid">
        <div
          v-for="cam in pagedCameras"
          :key="cam.id"
          class="video-cell"
          :class="{ alert: cam.status === 'alert', selected: selectedCam?.id === cam.id }"
          @click="selectCamera(cam)"
        >
          <div class="video-header">
            <span>{{ cam.name }}</span>
            <div style="display:flex;gap:4px;align-items:center">
              <el-tag size="small" :type="statusType(cam.status)">{{ statusLabel(cam.status) }}</el-tag>
              <!-- 暂停/恢复 -->
              <el-tooltip v-if="cam.status === 'online' || cam.status === 'alert'" content="暂停">
                <el-icon size="14" style="cursor:pointer;color:#faad14" @click.stop="pauseCamera(cam)"><VideoPause /></el-icon>
              </el-tooltip>
              <el-tooltip v-if="cam.status === 'paused'" content="恢复">
                <el-icon size="14" style="cursor:pointer;color:#52c41a" @click.stop="resumeCamera(cam)"><VideoPlay /></el-icon>
              </el-tooltip>
              <!-- 停止 -->
              <el-tooltip v-if="cam.status !== 'offline'" content="停止">
                <el-icon size="14" style="cursor:pointer;color:#ff7a45" @click.stop="stopCamera(cam)"><CircleClose /></el-icon>
              </el-tooltip>
              <!-- 删除 -->
              <el-tooltip content="删除摄像头">
                <el-icon size="14" style="cursor:pointer;color:#ff4d4f" @click.stop="removeCamera(cam)"><Delete /></el-icon>
              </el-tooltip>
            </div>
          </div>
          <div class="video-body">
            <img v-if="cam.status !== 'offline'"
              :src="`http://localhost:5000/api/stream/${cam.id}`"
              class="video-frame"
            />
            <div v-else class="no-signal">
              <el-icon size="32"><VideoCamera /></el-icon>
              <p>未接入</p>
              <el-button size="small" type="primary" @click.stop="openStartDialog(cam)">接入视频</el-button>
            </div>
          </div>
        </div>

        <!-- 添加占位格已移除，使用顶部"添加摄像头"按钮 -->
      </div>

      <!-- 分页 -->
      <div class="pagination-bar" v-if="cameras.length > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="cameras.length"
          layout="prev, pager, next"
          background
        />
      </div>
    </el-card>

    <!-- 接入视频对话框 -->
    <el-dialog v-model="startDialogVisible" :title="'接入视频 - ' + startTarget?.name" width="480px">
      <el-tabs v-model="startMode">
        <el-tab-pane label="上传视频文件" name="upload">
          <el-upload drag :auto-upload="false" :on-change="onFileChange" accept="video/*">
            <el-icon size="48"><UploadFilled /></el-icon>
            <p>拖拽视频文件到此处，或点击上传</p>
          </el-upload>
        </el-tab-pane>
        <el-tab-pane label="视频流地址" name="url">
          <el-input v-model="streamUrl" placeholder="RTSP地址 / 本地路径 / 0（电脑摄像头）" />
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="startDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startStream" :loading="starting">开始接入</el-button>
      </template>
    </el-dialog>

    <!-- 添加摄像头对话框 -->
    <el-dialog v-model="addDialogVisible" title="添加摄像头" width="400px">
      <el-form :model="newCam" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="newCam.name" placeholder="如：操场东侧" />
        </el-form-item>
        <el-form-item label="位置描述">
          <el-input v-model="newCam.location" placeholder="如：操场东侧入口" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="addCamera" :loading="adding">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import socket from '../socket'

const cameras = ref([])
const selectedCam = ref(null)
const isFullscreen = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = 6
const pagedCameras = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return cameras.value.slice(start, start + pageSize)
})

// 接入视频
const startDialogVisible = ref(false)
const startTarget = ref(null)
const startMode = ref('upload')
const streamUrl = ref('')
const uploadFile = ref(null)
const starting = ref(false)

// 添加摄像头
const addDialogVisible = ref(false)
const newCam = ref({ name: '', location: '' })
const adding = ref(false)

function statusType(s) {
  return { online: 'success', alert: 'danger', offline: 'info', paused: 'warning' }[s] || 'info'
}
function statusLabel(s) {
  return { online: '正常', alert: '告警', offline: '离线', paused: '已暂停' }[s] || s
}

async function loadCameras() {
  const { data } = await axios.get('/api/cameras')
  cameras.value = data
}

function selectCamera(cam) { selectedCam.value = cam }

function openStartDialog(cam) {
  startTarget.value = cam
  streamUrl.value = ''
  uploadFile.value = null
  startDialogVisible.value = true
}

function openAddDialog() {
  newCam.value = { name: '', location: '' }
  addDialogVisible.value = true
}

function onFileChange(file) { uploadFile.value = file.raw }

async function startStream() {
  if (!startTarget.value) return
  starting.value = true
  try {
    if (startMode.value === 'upload' && uploadFile.value) {
      const form = new FormData()
      form.append('camera_id', startTarget.value.id)
      form.append('video', uploadFile.value)
      await axios.post('/api/cameras/upload', form)
    } else if (startMode.value === 'url' && streamUrl.value !== '') {
      await axios.post('/api/cameras/start', {
        camera_id: startTarget.value.id,
        source: streamUrl.value,
      })
    }
    startDialogVisible.value = false
    await loadCameras()
  } finally {
    starting.value = false
  }
}

async function addCamera() {
  if (!newCam.value.name.trim()) return
  adding.value = true
  try {
    const { data } = await axios.post('/api/cameras/add', newCam.value)
    cameras.value.push(data.camera)
    addDialogVisible.value = false
    // 跳到最后一页
    currentPage.value = Math.ceil(cameras.value.length / pageSize)
    // 自动弹出接入视频
    openStartDialog(data.camera)
  } finally {
    adding.value = false
  }
}

async function removeCamera(cam) {
  try {
    await axios.delete(`/api/cameras/${cam.id}`)
    cameras.value = cameras.value.filter(c => c.id !== cam.id)
    if (currentPage.value > Math.ceil(cameras.value.length / pageSize)) {
      currentPage.value = Math.max(1, currentPage.value - 1)
    }
  } catch (e) {
    console.error(e)
  }
}

async function pauseCamera(cam) {
  await axios.post('/api/cameras/pause', { camera_id: cam.id })
  cam.status = 'paused'
}

async function resumeCamera(cam) {
  await axios.post('/api/cameras/resume', { camera_id: cam.id })
  cam.status = 'online'
}

async function stopCamera(cam) {
  await axios.post('/api/cameras/stop', { camera_id: cam.id })
  cam.status = 'offline'
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  const aside = document.querySelector('.el-aside')
  const header = document.querySelector('.el-header')
  if (aside) aside.style.display = isFullscreen.value ? 'none' : ''
  if (header) header.style.display = isFullscreen.value ? 'none' : ''
}

function onKeydown(e) {
  if (e.key === 'Escape' && isFullscreen.value) toggleFullscreen()
}

onMounted(() => {
  loadCameras()
  window.addEventListener('keydown', onKeydown)
  socket.on('cameras', (data) => { cameras.value = data })
  socket.on('new_event', (data) => {
    const cam = cameras.value.find(c => c.id === data.event.camera_id)
    if (cam) cam.status = 'alert'
  })
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
  if (isFullscreen.value) toggleFullscreen()
  socket.off('cameras')
  socket.off('new_event')
})
</script>

<style scoped>
.monitor-page.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: #000;
  overflow: auto;
}
.monitor-page.fullscreen .monitor-card {
  height: 100vh;
  border-radius: 0;
  border: none;
}
.monitor-page.fullscreen .video-body {
  height: calc((100vh - 160px) / 2 - 32px);
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.video-cell {
  border: 2px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s;
}
.video-cell.alert { border-color: #ff4d4f; box-shadow: 0 0 12px rgba(255,77,79,0.3); }
.video-cell.selected { border-color: #1677ff; }

.add-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 212px;
  color: #999;
  border: 2px dashed #d9d9d9;
  background: #fafafa;
  font-size: 13px;
  transition: all 0.2s;
}
.add-cell:hover { border-color: #1677ff; color: #1677ff; background: #e6f4ff; }

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 10px;
  background: #001529;
  color: #fff;
  font-size: 13px;
}

.video-body { height: 180px; background: #000; position: relative; }
.video-frame { width: 100%; height: 100%; object-fit: contain; background: #000; }

.no-signal {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #666;
  gap: 8px;
  font-size: 13px;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
</style>
