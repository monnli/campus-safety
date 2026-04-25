<template>
  <div>
    <el-card shadow="never" style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="摄像头">
          <el-select v-model="filterCamera" clearable placeholder="全部" style="width:140px">
            <el-option v-for="cam in cameras" :key="cam.id" :label="cam.name" :value="cam.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="filterDate" type="date" value-format="YYYY-MM-DD"
            placeholder="选择日期" style="width:160px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadRecordings">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>历史录像</span>
        <el-tag type="info" size="small" style="margin-left:8px">共 {{ recordings.length }} 段</el-tag>
        <el-button size="small" style="float:right" @click="$router.push('/settings')">
          配置录像设置
        </el-button>
      </template>

      <el-empty v-if="!recordings.length" description="暂无录像记录，请在系统设置中启用持续录像功能" />

      <el-table v-else :data="recordings" stripe>
        <el-table-column label="录像时间" width="180">
          <template #default="{ row }">{{ row.timestamp?.slice(0,19).replace('T',' ') }}</template>
        </el-table-column>
        <el-table-column label="摄像头" prop="camera_name" width="100" />
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">{{ row.size_mb }} MB</template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="playRecording(row)">播放</el-button>
            <el-button size="small" @click="downloadRecording(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 播放对话框 -->
    <el-dialog v-model="playerVisible" :title="currentRecording?.camera_name + ' - ' + currentRecording?.timestamp?.slice(0,19).replace('T',' ')"
      width="720px" @close="stopPlay">
      <video v-if="playerVisible" ref="videoEl" controls autoplay style="width:100%;border-radius:6px;background:#000">
        <source :src="`http://localhost:5000/static/recordings/${currentRecording?.filename}`" type="video/mp4" />
      </video>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const recordings = ref([])
const cameras = ref([])
const filterCamera = ref('')
const filterDate = ref('')
const playerVisible = ref(false)
const currentRecording = ref(null)
const videoEl = ref(null)

async function loadRecordings() {
  const params = {}
  if (filterCamera.value) params.camera_id = filterCamera.value
  if (filterDate.value) params.date = filterDate.value
  const { data } = await axios.get('/api/recording/list', { params })
  recordings.value = data
}

function resetFilter() {
  filterCamera.value = ''
  filterDate.value = ''
  loadRecordings()
}

function playRecording(row) {
  currentRecording.value = row
  playerVisible.value = true
}

function stopPlay() {
  if (videoEl.value) videoEl.value.pause()
  playerVisible.value = false
}

async function downloadRecording(row) {
  const url = `http://localhost:5000/static/recordings/${row.filename}`
  const a = document.createElement('a')
  a.href = url
  a.download = row.filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

onMounted(async () => {
  const { data } = await axios.get('/api/cameras')
  cameras.value = data
  loadRecordings()
})
</script>
