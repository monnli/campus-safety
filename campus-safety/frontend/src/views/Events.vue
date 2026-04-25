<template>
  <div>
    <!-- 筛选栏 -->
    <el-card shadow="never" style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="行为类型">
          <el-select v-model="filterBehavior" clearable placeholder="全部" style="width:140px">
            <el-option label="打架斗殴" value="fighting" />
            <el-option label="校园霸凌" value="bullying" />
            <el-option label="人员跌倒" value="falling" />
            <el-option label="异常聚集" value="gathering" />
            <el-option label="陌生人入侵" value="intrusion" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width:240px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadEvents">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
        <el-form-item style="float:right">
          <el-button @click="getDailyReport" :loading="reportLoading">生成今日日报</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 事件列表 -->
    <el-card shadow="never">
      <el-table :data="events" stripe style="width:100%">
        <el-table-column prop="timestamp" label="时间" width="160">
          <template #default="{ row }">{{ row.timestamp.slice(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
        <el-table-column prop="camera_name" label="地点" width="100" />
        <el-table-column prop="behavior" label="行为" width="120">
          <template #default="{ row }">
            <el-tag :type="behaviorType(row.behavior)">{{ behaviorCn(row.behavior) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="90">
          <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'handled' ? 'success' : 'warning'" size="small">
              {{ row.status === 'handled' ? '已处理' : '待处理' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="viewEvent(row)">详情</el-button>
            <el-button size="small" type="success" v-if="row.status === 'pending'" @click="handleEvent(row)">标记处理</el-button>
            <el-button size="small" type="warning" v-if="row.status === 'pending'" @click="markFalse(row)">误报</el-button>
            <el-tag v-if="row.status === 'handled'" type="success" size="small">已处理</el-tag>
            <el-tag v-if="row.status === 'false_alarm'" type="warning" size="small">误报</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 事件详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="事件详情" size="500px">
      <div v-if="currentEvent" class="event-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="事件ID">{{ currentEvent.id }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ currentEvent.timestamp.slice(0,19).replace('T',' ') }}</el-descriptions-item>
          <el-descriptions-item label="地点">{{ currentEvent.camera_name }}</el-descriptions-item>
          <el-descriptions-item label="行为">
            <el-tag :type="behaviorType(currentEvent.behavior)">{{ behaviorCn(currentEvent.behavior) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">{{ (currentEvent.confidence * 100).toFixed(1) }}%</el-descriptions-item>
        </el-descriptions>

        <el-divider>Qwen-VL 分析结果</el-divider>
        <p class="detail-text">{{ currentEvent.vl_result }}</p>

        <el-divider>AI 预警报告</el-divider>
        <p class="detail-text">{{ currentEvent.report }}</p>

        <el-divider>存档视频</el-divider>
        <div v-if="currentEvent.clip_path">
          <video controls style="width:100%;border-radius:6px;background:#000" preload="metadata">
            <source :src="`http://localhost:5000/static/alerts/${currentEvent.clip_path.split('/').pop()}`" type="video/mp4" />
            <source :src="`http://localhost:5000/static/alerts/${currentEvent.clip_path.split('/').pop()}`" type="video/webm" />
            您的浏览器不支持视频播放，请
            <a :href="`http://localhost:5000/static/alerts/${currentEvent.clip_path.split('/').pop()}`" target="_blank">点击下载</a>
            后查看
          </video>
          <div style="margin-top:6px;text-align:right">
            <a :href="`http://localhost:5000/static/alerts/${currentEvent.clip_path.split('/').pop()}`"
               target="_blank" style="font-size:12px;color:#1677ff">
              <el-icon><Download /></el-icon> 下载视频
            </a>
          </div>
        </div>
        <p v-else style="color:#999">暂无存档视频</p>
      </div>
    </el-drawer>

    <!-- 日报对话框 -->
    <el-dialog v-model="reportVisible" title="今日安全日报" width="600px">
      <pre class="report-text">{{ dailyReport }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import socket from '../socket'

const events = ref([])
const filterBehavior = ref('')
const dateRange = ref([])
const drawerVisible = ref(false)
const currentEvent = ref(null)
const reportVisible = ref(false)
const dailyReport = ref('')
const reportLoading = ref(false)

const behaviorCn = (b) => ({ fighting:'打架斗殴', bullying:'校园霸凌', falling:'人员跌倒', gathering:'异常聚集', intrusion:'陌生人入侵' }[b] || b)
const behaviorType = (b) => ({ fighting:'danger', bullying:'danger', falling:'warning', gathering:'warning', intrusion:'danger' }[b] || 'info')

async function loadEvents() {
  const params = {}
  if (filterBehavior.value) params.behavior = filterBehavior.value
  if (dateRange.value?.length === 2) {
    params.date_start = dateRange.value[0]
    params.date_end = dateRange.value[1]
  }
  const { data } = await axios.get('/api/events', { params })
  events.value = data
}

function resetFilter() {
  filterBehavior.value = ''
  dateRange.value = []
  loadEvents()
}

function viewEvent(row) {
  currentEvent.value = row
  drawerVisible.value = true
}

async function handleEvent(row) {
  await axios.post(`/api/events/${row.id}/handle`)
  row.status = 'handled'
}

async function markFalse(row) {
  await axios.post(`/api/events/${row.id}/false-alarm`)
  row.status = 'false_alarm'
}

async function getDailyReport() {
  reportLoading.value = true
  try {
    const { data } = await axios.get('/api/daily-report')
    dailyReport.value = data.report
    reportVisible.value = true
  } finally {
    reportLoading.value = false
  }
}

onMounted(() => {
  loadEvents()
  socket.on('new_event', () => loadEvents())
})
</script>

<style scoped>
.event-detail { padding: 0 4px; }
.detail-text { font-size: 14px; color: #333; line-height: 1.8; white-space: pre-wrap; }
.report-text { white-space: pre-wrap; font-size: 14px; line-height: 1.8; color: #333; }
</style>
