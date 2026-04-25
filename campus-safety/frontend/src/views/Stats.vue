<template>
  <div class="stats-page">
    <!-- 时间筛选 -->
    <el-card shadow="never" style="margin-bottom:16px">
      <el-form inline>
        <el-form-item label="时间范围">
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至"
            start-placeholder="开始日期" end-placeholder="结束日期"
            value-format="YYYY-MM-DD" style="width:240px" />
        </el-form-item>
        <el-form-item label="趋势天数">
          <el-select v-model="trendDays" style="width:100px">
            <el-option label="近7天" :value="7" />
            <el-option label="近14天" :value="14" />
            <el-option label="近30天" :value="30" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadAll">查询</el-button>
          <el-button @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 概览卡片 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6" v-for="item in overview" :key="item.label">
        <el-card shadow="never" class="stat-card">
          <div class="stat-number" :style="{ color: item.color }">{{ item.value }}</div>
          <div class="stat-label">{{ item.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图 -->
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>事件趋势（近{{ trendDays }}天）</template>
          <v-chart :option="trendChartOption" style="height:220px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom:16px">
      <!-- 行为类型分布 -->
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>行为类型分布</template>
          <v-chart :option="behaviorChartOption" style="height:260px" autoresize />
        </el-card>
      </el-col>
      <!-- 各区域事件分布 -->
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>各区域事件分布</template>
          <v-chart :option="cameraChartOption" style="height:260px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 时段分布 -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>事件时段分布</template>
          <v-chart :option="hourlyChartOption" style="height:220px" autoresize />
        </el-card>
      </el-col>
      <!-- 热力图 -->
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>校园风险热力图</template>
          <div class="heatmap-wrap">
            <div class="heatmap-bg">校园平面图</div>
            <div v-for="cam in heatmapData" :key="cam.id" class="heat-dot"
              :style="{ left: cam.x + '%', top: cam.y + '%', '--size': Math.max(20, Math.min(60, cam.count * 4 + 20)) + 'px', '--opacity': Math.min(0.9, 0.2 + cam.count * 0.05) }">
              <div class="heat-circle" :class="heatLevel(cam.count)"></div>
              <div class="heat-label">{{ cam.name }}<br/>{{ cam.count }}次</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, LineChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'

use([CanvasRenderer, PieChart, BarChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent])

const stats = ref({ total: 0, by_behavior: {}, by_camera: {}, by_hour: {} })
const trendData = ref([])
const heatmapData = ref([])
const dateRange = ref([])
const trendDays = ref(7)

const behaviorCn = { person:'人员异常', fighting:'打架斗殴', bullying:'校园霸凌', falling:'人员跌倒', gathering:'异常聚集', intrusion:'陌生人入侵' }

const heatLevel = (count) => count >= 10 ? 'heat-high' : count >= 5 ? 'heat-mid' : 'heat-low'

const overview = computed(() => [
  { label: '事件总数', value: stats.value.total, color: '#1677ff' },
  { label: '打架/霸凌', value: (stats.value.by_behavior.fighting || 0) + (stats.value.by_behavior.bullying || 0), color: '#ff4d4f' },
  { label: '跌倒/聚集', value: (stats.value.by_behavior.falling || 0) + (stats.value.by_behavior.gathering || 0), color: '#fa8c16' },
  { label: '入侵事件', value: stats.value.by_behavior.intrusion || 0, color: '#722ed1' },
])

const trendChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['总事件', '打架/霸凌', '跌倒/聚集'], bottom: 0 },
  xAxis: { type: 'category', data: trendData.value.map(d => d.date.slice(5)) },
  yAxis: { type: 'value', minInterval: 1 },
  series: [
    { name: '总事件', type: 'line', smooth: true, data: trendData.value.map(d => d.total), itemStyle: { color: '#1677ff' }, areaStyle: { opacity: 0.1 } },
    { name: '打架/霸凌', type: 'line', smooth: true, data: trendData.value.map(d => (d.by_behavior.fighting || 0) + (d.by_behavior.bullying || 0)), itemStyle: { color: '#ff4d4f' } },
    { name: '跌倒/聚集', type: 'line', smooth: true, data: trendData.value.map(d => (d.by_behavior.falling || 0) + (d.by_behavior.gathering || 0)), itemStyle: { color: '#fa8c16' } },
  ]
}))

const behaviorChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [{
    type: 'pie', radius: ['40%', '70%'],
    data: Object.entries(stats.value.by_behavior).map(([k, v]) => ({ name: behaviorCn[k] || k, value: v })),
    emphasis: { itemStyle: { shadowBlur: 10 } }
  }]
}))

const cameraChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: Object.keys(stats.value.by_camera), axisLabel: { rotate: 30 } },
  yAxis: { type: 'value', minInterval: 1 },
  series: [{ type: 'bar', data: Object.values(stats.value.by_camera), itemStyle: { color: '#1677ff' } }]
}))

const hourlyChartOption = computed(() => {
  const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2,'0')}:00`)
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{ type: 'bar', data: hours.map(h => stats.value.by_hour[h] || 0), itemStyle: { color: '#52c41a' } }]
  }
})

async function loadAll() {
  const params = {}
  if (dateRange.value?.length === 2) {
    params.date_start = dateRange.value[0]
    params.date_end = dateRange.value[1]
  }
  const [s, t, h] = await Promise.allSettled([
    axios.get('/api/stats', { params }),
    axios.get('/api/trend', { params: { days: trendDays.value } }),
    axios.get('/api/heatmap'),
  ])
  if (s.status === 'fulfilled') stats.value = s.value.data
  if (t.status === 'fulfilled') trendData.value = t.value.data
  if (h.status === 'fulfilled') heatmapData.value = h.value.data
}

function resetFilter() {
  dateRange.value = []
  trendDays.value = 7
  loadAll()
}

onMounted(() => {
  loadAll()
  setInterval(loadAll, 15000)
})
</script>

<style scoped>
.stat-card { text-align: center; padding: 8px 0; }
.stat-number { font-size: 36px; font-weight: 700; }
.stat-label { font-size: 13px; color: #999; margin-top: 4px; }

.heatmap-wrap {
  position: relative;
  height: 180px;
  background: #e8f4fd;
  border-radius: 8px;
  border: 2px dashed #91caff;
  overflow: hidden;
}
.heatmap-bg {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  color: #bbb; font-size: 13px;
}
.heat-dot {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex; flex-direction: column; align-items: center;
  gap: 2px; cursor: default;
}
.heat-circle {
  width: var(--size); height: var(--size);
  border-radius: 50%;
  opacity: var(--opacity);
  transition: all 0.3s;
}
.heat-high { background: radial-gradient(circle, #ff4d4f, rgba(255,77,79,0.1)); }
.heat-mid  { background: radial-gradient(circle, #faad14, rgba(250,173,20,0.1)); }
.heat-low  { background: radial-gradient(circle, #52c41a, rgba(82,196,26,0.1)); }
.heat-label { font-size: 10px; color: #333; background: rgba(255,255,255,0.85); padding: 1px 4px; border-radius: 3px; text-align: center; white-space: nowrap; }
</style>
