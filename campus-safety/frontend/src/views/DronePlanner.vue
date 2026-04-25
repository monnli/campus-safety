<template>
  <div class="drone-planner">
    <el-row :gutter="16">
      <!-- 左侧地图 -->
      <el-col :span="17">
        <el-card shadow="never">
          <template #header>
            <span>无人机巡逻路径规划</span>
            <div style="float:right;display:flex;gap:8px;align-items:center">
              <el-radio-group v-model="drawMode" size="small">
                <el-radio-button value="">浏览</el-radio-button>
                <el-radio-button value="school">标记学校</el-radio-button>
                <el-radio-button value="building">标记建筑</el-radio-button>
                <el-radio-button value="route">画回家路线</el-radio-button>
              </el-radio-group>
              <el-button size="small" type="primary" @click="generateWaypoints" :loading="generating">自动生成航点</el-button>
              <el-button size="small" @click="exportKml">导出KML航线</el-button>
            </div>
          </template>
          <div id="amap-container" style="width:100%;height:calc(100vh - 200px)"></div>
        </el-card>
      </el-col>

      <!-- 右侧面板 -->
      <el-col :span="7" style="max-height:calc(100vh - 120px);overflow-y:auto">
        <!-- 学校信息 -->
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header>学校信息</template>
          <el-form label-width="80px" size="small">
            <el-form-item label="学校名称">
              <el-input v-model="plan.school.name" placeholder="输入学校名称搜索定位">
                <template #append><el-button @click="searchSchool">搜索</el-button></template>
              </el-input>
            </el-form-item>
            <el-form-item label="中心坐标">
              <span v-if="plan.school.center" style="font-size:12px;color:#666">
                {{ plan.school.center[0].toFixed(5) }}, {{ plan.school.center[1].toFixed(5) }}
              </span>
              <span v-else style="color:#999;font-size:12px">切换"标记学校"后点击地图设置</span>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 飞行参数 -->
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header>飞行参数</template>
          <el-form label-width="120px" size="small">
            <el-form-item label="基础飞行高度(m)">
              <el-input-number v-model="plan.settings.base_altitude" :min="10" :max="120" style="width:100%" />
            </el-form-item>
            <el-form-item label="建筑安全余量(m)">
              <el-input-number v-model="plan.settings.building_clearance" :min="5" :max="50" style="width:100%" />
            </el-form-item>
            <el-form-item label="飞行速度(m/s)">
              <el-input-number v-model="plan.settings.speed" :min="1" :max="15" style="width:100%" />
            </el-form-item>
            <el-form-item label="航点间距(m)">
              <el-input-number v-model="plan.settings.waypoint_interval" :min="50" :max="500" :step="50" style="width:100%" />
              <div style="font-size:11px;color:#999;margin-top:2px">沿路线每隔N米自动插入一个航点</div>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 建筑物 -->
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header>
            <span>建筑物（{{ plan.school.buildings.length }}）</span>
            <el-button size="small" text type="danger" style="float:right" @click="clearBuildings">清空</el-button>
          </template>
          <div v-if="!plan.school.buildings.length" style="color:#999;font-size:12px;text-align:center;padding:8px">
            切换到"标记建筑"模式，点击地图标记建筑物
          </div>
          <div v-for="(b, i) in plan.school.buildings" :key="i" class="list-item">
            <span style="flex:1">{{ b.name }}</span>
            <span style="color:#666;font-size:12px;margin-right:8px">{{ b.height }}m</span>
            <el-button size="small" text type="danger" @click="removeBuilding(i)">删除</el-button>
          </div>
        </el-card>

        <!-- 回家路线 -->
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header>
            <span>学生回家路线（{{ plan.home_routes.length }}）</span>
            <el-button size="small" text type="danger" style="float:right" @click="clearRoutes">清空</el-button>
          </template>
          <div v-if="drawMode === 'route' && pendingRoute.length > 0" style="margin-bottom:8px">
            <el-alert type="info" :closable="false" show-icon>
              <template #default>
                已标记 {{ pendingRoute.length }} 个点
                <el-button size="small" type="primary" style="margin-left:8px" @click="finishRoute">完成路线</el-button>
                <el-button size="small" style="margin-left:4px" @click="cancelRoute">取消</el-button>
              </template>
            </el-alert>
          </div>
          <div v-if="!plan.home_routes.length && drawMode !== 'route'" style="color:#999;font-size:12px;text-align:center;padding:8px">
            切换到"画回家路线"模式，点击绘制，点"完成路线"结束
          </div>
          <div v-for="(r, i) in plan.home_routes" :key="i" class="list-item">
            <span style="flex:1">{{ r.name }}</span>
            <span style="color:#666;font-size:12px;margin-right:8px">{{ r.path.length }}个点</span>
            <el-button size="small" text type="danger" @click="removeRoute(i)">删除</el-button>
          </div>
        </el-card>

        <!-- 航点列表 -->
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header>巡逻航点（{{ plan.waypoints.length }}）</template>
          <div v-if="!plan.waypoints.length" style="color:#999;font-size:12px;text-align:center;padding:8px">
            点击"自动生成航点"按钮
          </div>
          <div v-for="wp in plan.waypoints.slice(0,10)" :key="wp.id" class="list-item">
            <el-tag size="small" :type="wp.action==='takeoff'?'success':wp.action==='land'?'danger':'primary'">
              {{ wp.action==='takeoff'?'起飞':wp.action==='land'?'降落':'飞行' }}
            </el-tag>
            <span style="font-size:11px;flex:1;margin-left:6px">{{ wp.label }}</span>
            <span style="color:#666;font-size:11px">{{ wp.altitude }}m</span>
          </div>
          <div v-if="plan.waypoints.length > 10" style="font-size:12px;color:#999;text-align:center;padding:4px">
            ...共{{ plan.waypoints.length }}个航点
          </div>
        </el-card>

        <!-- 飞行信息 -->
        <el-card shadow="never" v-if="flightInfo.total_waypoints" style="margin-bottom:12px">
          <template #header>飞行信息</template>
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="航点数">{{ flightInfo.total_waypoints }}</el-descriptions-item>
            <el-descriptions-item label="路线数">{{ flightInfo.routes_count }}</el-descriptions-item>
            <el-descriptions-item label="总距离">{{ flightInfo.total_distance_km }} km</el-descriptions-item>
            <el-descriptions-item label="预计时间">
              <el-tag type="warning" size="small">{{ flightInfo.estimated_time_min }} 分钟</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <div style="margin-top:8px;font-size:12px;color:#fa8c16">
            ⚠️ 大疆 Mini 系列电池续航约 30 分钟，请确保飞行时间在电池容量范围内
          </div>
        </el-card>

        <!-- 巡逻时间段 -->
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header>巡逻时间段</template>
          <div v-for="s in droneSchedules" :key="s.label" class="list-item">
            <el-tag size="small" type="success">{{ s.label }}</el-tag>
            <span style="font-size:12px;margin-left:6px">{{ s.start }} ~ {{ s.end }}</span>
          </div>
          <el-button size="small" style="margin-top:8px" @click="$router.push('/settings')">在系统设置中修改</el-button>
        </el-card>

        <!-- 巡逻历史 -->
        <el-card shadow="never">
          <template #header>巡逻规划历史</template>
          <div v-if="!patrolHistory.length" style="color:#999;font-size:12px;text-align:center;padding:8px">暂无历史记录</div>
          <div v-for="(h, i) in patrolHistory.slice(0,5)" :key="i" class="list-item" style="flex-direction:column;align-items:flex-start;gap:2px">
            <div style="font-size:12px;color:#333">{{ h.time.slice(0,16).replace('T',' ') }}</div>
            <div style="font-size:11px;color:#999">
              {{ h.flight_info.total_waypoints }}个航点 · {{ h.flight_info.total_distance_km }}km · 约{{ h.flight_info.estimated_time_min }}分钟
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加建筑物对话框 -->
    <el-dialog v-model="buildingDialogVisible" title="添加建筑物" width="360px">
      <el-form :model="newBuilding" label-width="80px">
        <el-form-item label="建筑名称"><el-input v-model="newBuilding.name" placeholder="如：教学楼A" /></el-form-item>
        <el-form-item label="建筑高度(m)"><el-input-number v-model="newBuilding.height" :min="3" :max="200" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="buildingDialogVisible=false">取消</el-button>
        <el-button type="primary" @click="confirmBuilding">确认</el-button>
      </template>
    </el-dialog>

    <!-- 保存路线对话框 -->
    <el-dialog v-model="routeDialogVisible" title="保存回家路线" width="360px">
      <el-form label-width="80px">
        <el-form-item label="路线名称"><el-input v-model="newRouteName" placeholder="如：北门→居民区" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelRouteSave">取消</el-button>
        <el-button type="primary" @click="confirmRoute">保存路线</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import AMapLoader from '@amap/amap-jsapi-loader'

const AMAP_KEY = '9850174b823993ae7aff55287b9843cd'

// 响应式数据
const plan = ref({
  school: { name: '', center: null, buildings: [] },
  home_routes: [],
  waypoints: [],
  settings: { base_altitude: 30, building_clearance: 10, speed: 5, patrol_radius: 1000, waypoint_interval: 100 }
})
const drawMode = ref('')
const generating = ref(false)
const buildingDialogVisible = ref(false)
const routeDialogVisible = ref(false)
const newBuilding = ref({ name: '', height: 20, point: null })
const newRouteName = ref('')
const pendingRoute = ref([])
const flightInfo = ref({})
const patrolHistory = ref([])

const droneSchedules = [
  { label: '上午课间', start: '10:00', end: '10:15' },
  { label: '午休时段', start: '12:00', end: '12:30' },
  { label: '下午课间', start: '14:00', end: '14:15' },
  { label: '下午放学', start: '16:30', end: '17:00' },
  { label: '晚放学',   start: '18:00', end: '18:30' },
]

// 地图相关（非响应式）
let map = null
let AMap = null
let drawingPolyline = null
let markers = []
let polylines = []
let waypointMarkers = []

// ── 地图初始化 ──────────────────────────────────────────────
async function initMap() {
  AMap = await AMapLoader.load({
    key: AMAP_KEY,
    version: '1.4.15',
    plugins: ['AMap.Geocoder', 'AMap.PlaceSearch', 'AMap.Circle'],
  })
  map = new AMap.Map('amap-container', {
    zoom: 16,
    center: [106.713478, 26.578343],
  })
  map.on('complete', () => {
    map.on('click', onMapClick)
    map.on('dblclick', onMapDblClick)
  })
  setTimeout(() => {
    map.on('click', onMapClick)
    map.on('dblclick', onMapDblClick)
  }, 1000)
  renderPlan()
}

// ── 地图交互 ────────────────────────────────────────────────
function onMapClick(e) {
  const lng = e.lnglat.getLng ? e.lnglat.getLng() : e.lnglat.lng
  const lat = e.lnglat.getLat ? e.lnglat.getLat() : e.lnglat.lat

  if (drawMode.value === 'school') {
    plan.value.school.center = [lng, lat]
    renderPlan(); savePlan()
    ElMessage.success('学校中心已标记')
    drawMode.value = ''
  } else if (drawMode.value === 'building') {
    newBuilding.value.point = [lng, lat]
    newBuilding.value.name = `建筑物${plan.value.school.buildings.length + 1}`
    buildingDialogVisible.value = true
  } else if (drawMode.value === 'route') {
    pendingRoute.value.push([lng, lat])
    if (drawingPolyline) map.remove(drawingPolyline)
    if (pendingRoute.value.length > 1) {
      drawingPolyline = new AMap.Polyline({
        path: pendingRoute.value.map(p => new AMap.LngLat(p[0], p[1])),
        strokeColor: '#faad14', strokeWeight: 3, strokeStyle: 'dashed',
      })
      map.add(drawingPolyline)
    }
  }
}

function onMapDblClick() {
  if (drawMode.value === 'route' && pendingRoute.value.length >= 2) {
    finishRoute()
  }
}

function finishRoute() {
  if (pendingRoute.value.length < 2) return
  newRouteName.value = `路线${plan.value.home_routes.length + 1}`
  routeDialogVisible.value = true
}

function cancelRoute() {
  pendingRoute.value = []
  if (drawingPolyline) { map.remove(drawingPolyline); drawingPolyline = null }
}

function cancelRouteSave() {
  routeDialogVisible.value = false
  pendingRoute.value = []
  if (drawingPolyline) { map.remove(drawingPolyline); drawingPolyline = null }
}

function confirmRoute() {
  if (pendingRoute.value.length < 2) return
  plan.value.home_routes.push({
    name: newRouteName.value || `路线${plan.value.home_routes.length + 1}`,
    path: [...pendingRoute.value],
  })
  routeDialogVisible.value = false
  pendingRoute.value = []
  if (drawingPolyline) { map.remove(drawingPolyline); drawingPolyline = null }
  // 不重置 drawMode，让用户可以继续画下一条路线
  renderPlan(); savePlan()
  ElMessage.success('路线已保存，可继续绘制下一条路线')
}

function confirmBuilding() {
  if (!newBuilding.value.name || !newBuilding.value.point) return
  plan.value.school.buildings.push({
    name: newBuilding.value.name,
    height: newBuilding.value.height,
    polygon: [newBuilding.value.point],
  })
  buildingDialogVisible.value = false
  renderPlan(); savePlan()
}

function removeBuilding(i) { plan.value.school.buildings.splice(i, 1); renderPlan(); savePlan() }
function removeRoute(i) { plan.value.home_routes.splice(i, 1); renderPlan(); savePlan() }
function clearBuildings() { plan.value.school.buildings = []; renderPlan(); savePlan() }
function clearRoutes() { plan.value.home_routes = []; renderPlan(); savePlan() }

// ── 地图渲染 ────────────────────────────────────────────────
function renderPlan() {
  if (!map || !AMap) return
  markers.forEach(m => map.remove(m))
  polylines.forEach(p => map.remove(p))
  waypointMarkers.forEach(m => map.remove(m))
  markers = []; polylines = []; waypointMarkers = []

  // 学校中心
  const center = plan.value.school.center
  if (center) {
    const m = new AMap.Marker({
      position: new AMap.LngLat(center[0], center[1]),
      label: { content: `<div style="background:#1677ff;color:#fff;padding:2px 8px;border-radius:3px;font-size:12px">🏫 ${plan.value.school.name || '学校'}</div>`, offset: new AMap.Pixel(0, -35) }
    })
    map.add(m); markers.push(m)
    map.setCenter(new AMap.LngLat(center[0], center[1]))
  }

  // 建筑物
  plan.value.school.buildings.forEach(b => {
    if (b.polygon && b.polygon[0]) {
      const m = new AMap.Marker({
        position: new AMap.LngLat(b.polygon[0][0], b.polygon[0][1]),
        label: { content: `<div style="background:#ff4d4f;color:#fff;padding:2px 6px;border-radius:3px;font-size:11px">🏢${b.name}(${b.height}m)</div>`, offset: new AMap.Pixel(0, -30) }
      })
      map.add(m); markers.push(m)
    }
  })

  // 回家路线 + 巡逻半径缓冲区
  const routeColors = ['#1677ff', '#52c41a', '#722ed1', '#fa8c16', '#eb2f96']
  plan.value.home_routes.forEach((route, i) => {
    if (!route.path || route.path.length < 2) return
    const color = routeColors[i % routeColors.length]

    // 巡逻半径缓冲区：用粗线模拟（宽度对应巡逻范围）
    const bufferLine = new AMap.Polyline({
      path: route.path.map(p => new AMap.LngLat(p[0], p[1])),
      strokeColor: color,
      strokeOpacity: 0.25,
      strokeWeight: 40,  // 视觉上表示缓冲区宽度
      zIndex: 5,
      lineJoin: 'round',
      lineCap: 'round',
    })
    map.add(bufferLine); polylines.push(bufferLine)

    // 路线主线（在缓冲区上方）
    const pl = new AMap.Polyline({
      path: route.path.map(p => new AMap.LngLat(p[0], p[1])),
      strokeColor: color, strokeWeight: 4, strokeOpacity: 0.9, zIndex: 10,
    })
    map.add(pl); polylines.push(pl)

    // 路线标签
    const m = new AMap.Marker({
      position: new AMap.LngLat(route.path[0][0], route.path[0][1]),
      label: { content: `<div style="background:${color};color:#fff;padding:2px 6px;border-radius:3px;font-size:12px">${route.name}</div>`, offset: new AMap.Pixel(0, -30) }
    })
    map.add(m); markers.push(m)
  })

  // 航点
  plan.value.waypoints.forEach(wp => {
    const m = new AMap.Marker({
      position: new AMap.LngLat(wp.lng, wp.lat),
      title: `${wp.label} (${wp.altitude}m)`,
    })
    map.add(m); waypointMarkers.push(m)
  })

  // 航点连线
  if (plan.value.waypoints.length > 1) {
    const pl = new AMap.Polyline({
      path: plan.value.waypoints.map(wp => new AMap.LngLat(wp.lng, wp.lat)),
      strokeColor: '#ff4d4f', strokeWeight: 2, strokeStyle: 'dashed', zIndex: 20,
    })
    map.add(pl); polylines.push(pl)
  }
}

// ── 搜索 ────────────────────────────────────────────────────
function searchSchool() {
  if (!plan.value.school.name || !AMap) return
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  if (user?.token) axios.defaults.headers.common['Authorization'] = `Bearer ${user.token}`

  axios.get('/api/amap/search', { params: { keywords: plan.value.school.name } }).then(({ data }) => {
    console.log('[Search] 返回数据:', data)
    if (data.status === '1' && data.pois && data.pois.length > 0) {
      const [lng, lat] = data.pois[0].location.split(',').map(Number)
      plan.value.school.center = [lng, lat]
      map.setCenter(new AMap.LngLat(lng, lat)); map.setZoom(17)
      renderPlan(); savePlan()
      ElMessage.success(`已定位到：${data.pois[0].name}`)
    } else {
      console.log('[Search] 未找到结果, status:', data.status, 'count:', data.count)
      ElMessage.warning('未找到该学校，请手动在地图上标记')
    }
  }).catch(e => {
    console.error('[Search] 请求失败:', e.response?.status, e.message)
    ElMessage.error('搜索失败，请手动标记')
  })
}

// ── 航点生成 ────────────────────────────────────────────────
async function generateWaypoints() {
  generating.value = true
  try {
    const { data } = await axios.post('/api/drone/generate-waypoints', plan.value)
    plan.value.waypoints = data.waypoints
    flightInfo.value = data.flight_info || {}
    renderPlan(); loadHistory()
    ElMessage.success(`已生成 ${data.waypoints.length} 个航点，预计飞行 ${data.flight_info?.estimated_time_min} 分钟`)
  } finally { generating.value = false }
}

async function exportKml() {
  try {
    const { data } = await axios.get('/api/drone/export-kml', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a'); a.href = url; a.download = 'patrol_route.kml'
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('KML航线文件已下载')
  } catch (e) { ElMessage.error('导出失败：' + (e.response?.data?.error || e.message)) }
}

async function savePlan() {
  try { await axios.post('/api/drone/plan', plan.value) } catch {}
}

async function loadHistory() {
  try { const { data } = await axios.get('/api/drone/history'); patrolHistory.value = data } catch {}
}

// ── 生命周期 ────────────────────────────────────────────────
onMounted(async () => {
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  if (user?.token) axios.defaults.headers.common['Authorization'] = `Bearer ${user.token}`
  try {
    const { data } = await axios.get('/api/drone/plan')
    plan.value = data
    if (data.flight_info) flightInfo.value = data.flight_info
  } catch {}
  await initMap()
  loadHistory()
})

onUnmounted(() => { if (map) map.destroy() })
</script>

<style scoped>
.drone-planner {}
.list-item {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 13px;
}
.list-item:last-child { border-bottom: none; }
</style>
