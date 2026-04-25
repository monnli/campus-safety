<template>
  <div class="dashboard">
    <!-- 顶部标题栏 -->
    <div class="dash-header">
      <div class="dash-title">
        <span class="title-main">黔视护苗 · 校园安全智能监控系统</span>
        <span class="title-sub">AI Safety Guardian</span>
      </div>
      <div class="dash-time">{{ currentTime }}</div>
      <div class="dash-actions">
        <el-button size="small" text style="color:#7ec8e3" @click="toggleFullscreen">
          {{ isFullscreen ? '退出全屏' : '全屏展示' }}
        </el-button>
        <el-button size="small" text style="color:#7ec8e3" @click="$router.push('/monitor')">返回系统</el-button>
      </div>
    </div>

    <!-- 主体内容 -->
    <div class="dash-body">
      <!-- 左栏 -->
      <div class="dash-col">
        <!-- 风险等级 -->
        <div class="dash-card">
          <div class="card-title">校园安全指数</div>
          <div class="risk-gauge">
            <div class="risk-score" :style="{ color: riskColor }">{{ risk.risk_score }}</div>
            <div class="risk-label" :style="{ color: riskColor }">风险等级：{{ risk.risk_level }}</div>
            <div class="risk-bar">
              <div class="risk-fill" :style="{ width: risk.risk_score + '%', background: riskColor }"></div>
            </div>
          </div>
          <div class="risk-summary">{{ risk.summary }}</div>
        </div>

        <!-- 高危区域 -->
        <div class="dash-card">
          <div class="card-title">高危区域 TOP3</div>
          <div class="area-list">
            <div v-for="(a, i) in risk.high_risk_areas" :key="i" class="area-item">
              <span class="area-rank" :class="'rank-' + (i+1)">{{ i+1 }}</span>
              <span class="area-name">{{ a.area }}</span>
              <span class="area-count">{{ a.count }} 次</span>
              <div class="area-bar-bg">
                <div class="area-bar-fill" :style="{ width: (a.count / (risk.high_risk_areas[0]?.count || 1) * 100) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 风险预测 -->
        <div class="dash-card">
          <div class="card-title">AI 风险预测</div>
          <div class="prediction-list">
            <div v-for="(p, i) in risk.predictions" :key="i" class="prediction-item">
              <el-icon color="#faad14"><Warning /></el-icon>
              <span>{{ p }}</span>
            </div>
          </div>
        </div>

        <!-- 高危时段分布 -->
        <div class="dash-card" style="flex-shrink:0">
          <div class="card-title">高危时段分布</div>
          <v-chart :option="hourlyChart" style="height:110px" autoresize />
        </div>
      </div>

      <!-- 中栏：实时视频 -->
      <div class="dash-col dash-center">
        <div class="dash-card video-card">
          <div class="card-title">实时监控画面</div>
          <div class="video-grid-dash" :style="videoGridStyle">
            <div v-for="(cam, idx) in onlineCameras.slice(0,4)" :key="cam.id"
              class="video-cell-dash" :class="{ alert: cam.status === 'alert' }"
              :style="videoCellStyle(idx)">
              <img :src="`http://localhost:5000/api/stream/${cam.id}`" class="video-img" />
              <div class="video-label">
                <span>{{ cam.name }}</span>
                <el-tag size="small" :type="cam.status === 'alert' ? 'danger' : 'success'">
                  {{ cam.status === 'alert' ? '告警' : '正常' }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <!-- 今日事件统计 -->
        <div class="dash-card overview-card">
          <div class="card-title" style="margin-bottom:6px">今日事件概览</div>
          <div class="overview-nums">
            <div class="num-item" v-for="item in overviewItems" :key="item.label">
              <div class="num-val" :style="{ color: item.color }">{{ item.value }}</div>
              <div class="num-label">{{ item.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右栏 -->
      <div class="dash-col">
        <!-- 最新告警 -->
        <div class="dash-card">
          <div class="card-title">最新告警</div>
          <div class="alert-list">
            <div v-for="e in recentEvents" :key="e.id" class="alert-item">
              <div class="alert-time">{{ e.timestamp.slice(11,16) }}</div>
              <div class="alert-info">
                <span class="alert-cam">{{ e.camera_name }}</span>
                <span class="alert-badge" :style="{ background: alertColor(e.behavior) }">{{ behaviorCn(e.behavior) }}</span>
              </div>
            </div>
            <div v-if="!recentEvents.length" class="no-data">暂无告警记录</div>
          </div>
        </div>

        <!-- 防控建议 -->
        <div class="dash-card">
          <div class="card-title">AI 防控建议</div>
          <div class="suggestion-list">
            <div v-for="(s, i) in risk.suggestions" :key="i" class="suggestion-item">
              <el-icon color="#52c41a"><CircleCheck /></el-icon>
              <span>{{ s }}</span>
            </div>
          </div>
        </div>

        <!-- 行为分布 -->
        <div class="dash-card behavior-card">
          <div class="card-title">行为类型统计</div>
          <div class="behavior-chart-wrap">
            <v-chart :option="behaviorChart" style="width:100%;height:100%" autoresize />
          </div>
        </div>      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'

use([CanvasRenderer, PieChart, BarChart, TooltipComponent, LegendComponent, GridComponent])

const currentTime = ref('')
const isFullscreen = ref(false)

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}
const risk = ref({ risk_score: 0, risk_level: '低', high_risk_areas: [], high_risk_hours: [], predictions: [], suggestions: [], summary: '加载中...' })
const cameras = ref([])
const recentEvents = ref([])
const stats = ref({ total: 0, by_behavior: {} })

const onlineCameras = computed(() => cameras.value.filter(c => c.status !== 'offline'))

// 根据摄像头数量动态计算网格布局
const videoGridStyle = computed(() => {
  const n = Math.min(onlineCameras.value.length, 4)
  if (n <= 1) return { gridTemplateColumns: '1fr', gridTemplateRows: '1fr' }
  if (n === 2) return { gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr' }
  if (n === 3) return { gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr' }
  return { gridTemplateColumns: '1fr 1fr', gridTemplateRows: '1fr 1fr' }
})

// 3个摄像头时第3个铺满第二行
const videoCellStyle = computed(() => (index) => {
  const n = Math.min(onlineCameras.value.length, 4)
  if (n === 3 && index === 2) return { gridColumn: '1 / -1' }
  return {}
})

const riskColor = computed(() => {
  const s = risk.value.risk_score
  return s >= 60 ? '#ff4d4f' : s >= 30 ? '#faad14' : '#52c41a'
})

const behaviorCn = (b) => ({ person:'人员异常', fighting:'打架斗殴', bullying:'校园霸凌', falling:'人员跌倒', gathering:'异常聚集', intrusion:'陌生人入侵' }[b] || b)

const alertColor = (b) => ({
  fighting:  '#ff4d4f',   // 红 - 打架
  bullying:  '#ff4d4f',   // 红 - 霸凌
  intrusion: '#722ed1',   // 紫 - 入侵
  falling:   '#1677ff',   // 蓝 - 跌倒
  gathering: '#fa8c16',   // 橙 - 聚集
  person:    '#52c41a',   // 绿 - 人员
}[b] || '#666')
const overviewItems = computed(() => [
  { label: '今日事件', value: stats.value.total, color: '#1677ff' },
  { label: '打架/霸凌', value: (stats.value.by_behavior?.fighting || 0) + (stats.value.by_behavior?.bullying || 0), color: '#ff4d4f' },
  { label: '跌倒/聚集', value: (stats.value.by_behavior?.falling || 0) + (stats.value.by_behavior?.gathering || 0), color: '#faad14' },
  { label: '入侵事件', value: stats.value.by_behavior?.intrusion || 0, color: '#722ed1' },
])

const hourlyChart = computed(() => {
  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2,'0')}`)
  const byHour = stats.value.by_hour || {}
  const data = hours.map(h => byHour[h + ':00'] || 0)
  const max = Math.max(...data, 1)
  return {
    backgroundColor: 'transparent',
    grid: { top: 8, bottom: 20, left: 28, right: 8 },
    xAxis: {
      type: 'category',
      data: hours,
      axisLabel: { color: '#4a8fb5', fontSize: 9, interval: 3 },
      axisLine: { lineStyle: { color: '#0d4f8c' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#4a8fb5', fontSize: 9 },
      splitLine: { lineStyle: { color: '#0d3a6e' } },
    },
    series: [{
      type: 'bar',
      data: data.map(v => ({
        value: v,
        itemStyle: { color: v >= max * 0.7 ? '#ff4d4f' : v >= max * 0.4 ? '#faad14' : '#1677ff' }
      })),
      barMaxWidth: 10,
    }]
  }
})

const behaviorChartHeight = ref(160)

function updateBehaviorChartSize() {
  const card = document.querySelector('.behavior-card')
  const title = document.querySelector('.behavior-card .card-title')
  if (card && title) {
    const h = card.clientHeight - title.clientHeight - 28
    behaviorChartHeight.value = Math.max(80, h)
  }
}

const behaviorChart = computed(() => {
  const behaviorColors = {
    fighting: '#ff4d4f', bullying: '#ff4d4f',
    intrusion: '#722ed1', falling: '#1677ff',
    gathering: '#fa8c16', person: '#52c41a',
  }
  const entries = Object.entries(stats.value.by_behavior || {})
  const names = entries.map(([k]) => behaviorCn(k))
  const values = entries.map(([, v]) => v)
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 8, bottom: 8, left: 8, right: 40, containLabel: true },
    xAxis: { type: 'value', axisLabel: { color: '#4a8fb5', fontSize: 9 }, splitLine: { lineStyle: { color: '#0d3a6e' } } },
    yAxis: { type: 'category', data: names, axisLabel: { color: '#7ec8e3', fontSize: 10 } },
    series: [{
      type: 'bar',
      data: entries.map(([k, v]) => ({ value: v, itemStyle: { color: behaviorColors[k] || '#1677ff' } })),
      barMaxWidth: 16,
      label: { show: true, position: 'right', color: '#7ec8e3', fontSize: 10 }
    }]
  }
})

async function loadAll() {
  const today = new Date().toISOString().slice(0, 10)
  const [riskRes, camRes, evtRes, statsRes] = await Promise.allSettled([
    axios.get('/api/risk-analysis'),
    axios.get('/api/cameras'),
    axios.get('/api/events', { params: { limit: 8 } }),
    axios.get('/api/stats', { params: { date_start: today, date_end: today } }),
  ])
  if (riskRes.status === 'fulfilled') risk.value = riskRes.value.data
  if (camRes.status === 'fulfilled') cameras.value = camRes.value.data
  if (evtRes.status === 'fulfilled') recentEvents.value = evtRes.value.data
  if (statsRes.status === 'fulfilled') stats.value = statsRes.value.data
}

let timer = null
let refreshTimer = null

onMounted(() => {
  loadAll()
  timer = setInterval(() => { currentTime.value = new Date().toLocaleString('zh-CN') }, 1000)
  refreshTimer = setInterval(loadAll, 30000)
  document.addEventListener('fullscreenchange', onFullscreenChange)
  // 进入大屏自动全屏
  setTimeout(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {})
    }
    updateBehaviorChartSize()
  }, 300)
  window.addEventListener('resize', updateBehaviorChartSize)
  document.addEventListener('fullscreenchange', () => {
    setTimeout(updateBehaviorChartSize, 300)
  })
})

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(refreshTimer)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  window.removeEventListener('resize', updateBehaviorChartSize)
  if (document.fullscreenElement) document.exitFullscreen()
})
</script>

<style scoped>
.dashboard {
  height: 100vh;
  overflow: hidden;
  background: #020e1f;
  color: #e0f0ff;
  display: flex;
  flex-direction: column;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.dash-header {
  height: 64px;
  background: linear-gradient(90deg, #001529, #003a70, #001529);
  border-bottom: 1px solid #0d4f8c;
  display: flex;
  align-items: center;
  padding: 0 24px;
  gap: 24px;
}

.dash-title { flex: 1; }
.title-main { font-size: 20px; font-weight: 700; color: #7ec8e3; letter-spacing: 2px; }
.title-sub { font-size: 12px; color: #4a8fb5; margin-left: 12px; }
.dash-time { font-size: 14px; color: #7ec8e3; font-variant-numeric: tabular-nums; }

.dash-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px 1fr 280px;
  gap: 12px;
  padding: 12px;
  overflow: hidden;
}

.dash-col { display: flex; flex-direction: column; gap: 12px; min-height: 0; overflow: hidden; }

/* 左栏各卡片比例分配，不允许溢出 */
.dash-col:first-child .dash-card { flex-shrink: 0; }
.dash-col:first-child .dash-card:nth-child(1) { flex: 0 0 auto; }
.dash-col:first-child .dash-card:nth-child(2) { flex: 0 0 auto; }
.dash-col:first-child .dash-card:nth-child(3) { flex: 1; min-height: 0; overflow: hidden; }
.dash-col:first-child .dash-card:nth-child(4) { flex: 0 0 140px; }

/* 右栏最后一个撑满 */
.dash-col:last-child .dash-card:last-child { flex: 1; min-height: 0; }

.behavior-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.behavior-chart-wrap {
  flex: 1;
  min-height: 0;
  position: relative;
}

/* 中栏专属 */
.dash-center { overflow: hidden; }
.dash-center .video-card { flex: 1; min-height: 0; }
.dash-center .overview-card { flex: 0 0 80px; padding: 8px 14px; }

.dash-card {
  background: rgba(0, 60, 120, 0.3);
  border: 1px solid #0d4f8c;
  border-radius: 8px;
  padding: 14px;
  backdrop-filter: blur(4px);
}

.card-title {
  font-size: 13px;
  color: #7ec8e3;
  border-left: 3px solid #1677ff;
  padding-left: 8px;
  margin-bottom: 12px;
  font-weight: 600;
}

/* 风险仪表 */
.risk-gauge { text-align: center; padding: 8px 0; }
.risk-score { font-size: 48px; font-weight: 700; line-height: 1; }
.risk-label { font-size: 14px; margin: 4px 0 12px; }
.risk-bar { height: 6px; background: #0d3a6e; border-radius: 3px; overflow: hidden; }
.risk-fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.risk-summary { font-size: 12px; color: #7ec8e3; margin-top: 10px; line-height: 1.6; }

/* 高危区域 */
.area-item { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; font-size: 13px; }
.area-rank { width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; }
.rank-1 { background: #ff4d4f; color: #fff; }
.rank-2 { background: #faad14; color: #fff; }
.rank-3 { background: #1677ff; color: #fff; }
.area-name { flex: 1; }
.area-count { color: #7ec8e3; font-size: 12px; width: 40px; text-align: right; }
.area-bar-bg { width: 60px; height: 4px; background: #0d3a6e; border-radius: 2px; overflow: hidden; }
.area-bar-fill { height: 100%; background: #1677ff; border-radius: 2px; }

/* 预测/建议 */
.prediction-item, .suggestion-item { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: #b0d4f0; margin-bottom: 8px; line-height: 1.6; }
.prediction-list, .suggestion-list { overflow: hidden; }

/* 视频网格 */
.video-card { display: flex; flex-direction: column; }
.video-grid-dash { display: grid; gap: 8px; flex: 1; min-height: 0; }
.video-cell-dash { position: relative; border: 1px solid #0d4f8c; border-radius: 6px; overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
.video-cell-dash.alert { border-color: #ff4d4f; box-shadow: 0 0 8px rgba(255,77,79,0.4); }
.video-img { width: 100%; flex: 1; min-height: 0; object-fit: contain; background: #000; display: block; }
.video-label { position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.6); padding: 4px 8px; display: flex; justify-content: space-between; align-items: center; font-size: 12px; }

/* 概览数字 */
.overview-nums { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.num-item { text-align: center; padding: 3px 4px; background: rgba(0,40,80,0.5); border-radius: 6px; }
.num-val { font-size: 18px; font-weight: 700; line-height: 1.2; }
.num-label { font-size: 10px; color: #7ec8e3; margin-top: 1px; }

/* 告警列表 */
.alert-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #0d3a6e; font-size: 12px; }
.alert-time { color: #7ec8e3; width: 40px; flex-shrink: 0; }
.alert-info { display: flex; align-items: center; gap: 6px; flex: 1; }
.alert-cam { color: #b0d4f0; }
.alert-badge {
  font-size: 11px; color: #fff; padding: 1px 6px;
  border-radius: 3px; white-space: nowrap; flex-shrink: 0;
}
.no-data { color: #4a8fb5; font-size: 12px; text-align: center; padding: 16px 0; }
</style>
