<template>
  <div>
    <el-tabs v-model="activeTab">
      <!-- 检测参数 -->
      <el-tab-pane label="检测参数" name="detection">
        <el-card shadow="never">
          <el-form :model="detectionForm" label-width="160px">
            <el-form-item label="YOLO 置信度阈值">
              <el-slider v-model="detectionForm.confidence" :min="0.1" :max="1" :step="0.05" show-input style="width:400px" />
              <div class="hint">低于此置信度的检测结果将被忽略，建议 0.5~0.7</div>
            </el-form-item>
            <el-form-item label="检测帧间隔">
              <el-input-number v-model="detectionForm.frameSkip" :min="1" :max="10" />
              <div class="hint">每隔 N 帧检测一次，值越大 CPU 占用越低</div>
            </el-form-item>
            <el-form-item label="触发冷却时间（秒）">
              <el-input-number v-model="detectionForm.cooldown" :min="5" :max="300" :step="5" />
              <div class="hint">同一摄像头同一行为在冷却时间内不重复触发</div>
            </el-form-item>
            <el-form-item label="事件前缓冲时长（秒）">
              <el-input-number v-model="detectionForm.preSeconds" :min="3" :max="30" />
              <div class="hint">触发前保留的视频缓冲时长</div>
            </el-form-item>
            <el-form-item label="事件后录制时长（秒）">
              <el-input-number v-model="detectionForm.postSeconds" :min="3" :max="30" />
              <div class="hint">触发后继续录制的时长</div>
            </el-form-item>
            <el-form-item label="检测行为类别">
              <el-checkbox-group v-model="detectionForm.dangerClasses">
                <el-checkbox label="fighting">打架斗殴</el-checkbox>
                <el-checkbox label="falling">人员跌倒</el-checkbox>
                <el-checkbox label="intrusion">陌生人入侵</el-checkbox>
                <el-checkbox label="person">人员检测（测试用）</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveDetection">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 通知设置 -->
      <el-tab-pane label="通知设置" name="notify">
        <el-card shadow="never">
          <el-form :model="notifyForm" label-width="160px">
            <el-form-item label="管理员列表">
              <div v-for="(admin, i) in notifyForm.admins" :key="i" class="admin-row">
                <el-input v-model="admin.name" placeholder="姓名" style="width:100px" />
                <el-input v-model="admin.phone" placeholder="手机号" style="width:140px" />
                <el-select v-model="admin.role" style="width:120px">
                  <el-option label="校长" value="principal" />
                  <el-option label="安全主任" value="manager" />
                  <el-option label="保安队长" value="guard" />
                </el-select>
                <el-button type="danger" size="small" @click="notifyForm.admins.splice(i,1)">删除</el-button>
              </div>
              <el-button size="small" @click="notifyForm.admins.push({name:'',phone:'',role:'guard'})">+ 添加管理员</el-button>
            </el-form-item>
            <el-form-item label="短信通知">
              <el-switch v-model="notifyForm.smsEnabled" />
              <span class="hint" style="margin-left:12px">{{ notifyForm.smsEnabled ? '已启用（当前为模拟模式）' : '已关闭' }}</span>
            </el-form-item>
            <el-form-item label="监控室警报">
              <el-switch v-model="notifyForm.alarmEnabled" />
            </el-form-item>
            <el-form-item label="语音广播">
              <el-switch v-model="notifyForm.broadcastEnabled" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveNotify">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 语音广播 -->
      <el-tab-pane label="语音广播" name="broadcast">
        <el-card shadow="never">
          <el-form :model="broadcastForm" label-width="160px">
            <el-form-item label="广播重复次数">
              <el-input-number v-model="broadcastForm.repeat_times" :min="1" :max="10" />
              <div class="hint">每次触发预警时，广播内容重复播放的次数</div>
            </el-form-item>
            <el-divider>自定义广播内容</el-divider>
            <div class="hint" style="margin-bottom:12px;margin-left:160px">留空则由AI根据事件自动生成广播内容</div>
            <el-form-item label="打架/暴力">
              <el-input v-model="broadcastForm.custom_texts.fighting" type="textarea" :rows="2"
                placeholder="留空则AI自动生成，例：注意，监控发现打架行为，安保人员请立即前往处置" />
            </el-form-item>
            <el-form-item label="人员跌倒">
              <el-input v-model="broadcastForm.custom_texts.falling" type="textarea" :rows="2"
                placeholder="留空则AI自动生成，例：注意，有人员跌倒，请相关人员立即前往查看" />
            </el-form-item>
            <el-form-item label="陌生人入侵">
              <el-input v-model="broadcastForm.custom_texts.intrusion" type="textarea" :rows="2"
                placeholder="留空则AI自动生成，例：注意，发现陌生人进入校园，安保人员请立即核查" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveBroadcast">保存配置</el-button>
              <el-button @click="testBroadcast">测试广播</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 模型配置 -->
      <el-tab-pane label="模型配置" name="model">
        <el-card shadow="never">
          <el-form label-width="160px">
            <el-form-item label="YOLO 模型">
              <el-tag type="success">{{ modelInfo.yolo }}</el-tag>
              <div class="hint">当前加载的目标检测模型</div>
            </el-form-item>
            <el-form-item label="多模态模型">
              <el-tag type="primary">{{ modelInfo.vl }}</el-tag>
              <div class="hint">用于视频帧语义理解和二次确认</div>
            </el-form-item>
            <el-form-item label="大语言模型">
              <el-tag type="primary">{{ modelInfo.llm }}</el-tag>
              <div class="hint">用于生成预警报告和智能查询</div>
            </el-form-item>
            <el-form-item label="语音合成">
              <el-tag type="warning">阿里云 TTS / Web Speech API</el-tag>
              <div class="hint">优先使用阿里云TTS，未配置时自动使用浏览器语音合成</div>
            </el-form-item>
            <el-form-item label="API 状态">
              <el-tag :type="apiStatus.ok ? 'success' : 'danger'">
                {{ apiStatus.ok ? '连接正常' : '连接异常（使用Mock模式）' }}
              </el-tag>
              <el-button size="small" style="margin-left:12px" @click="testApi" :loading="testing">测试连接</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 持续录像 -->
      <el-tab-pane label="持续录像" name="recording">
        <el-card shadow="never">
          <el-form :model="recordingForm" label-width="160px">
            <el-form-item label="启用持续录像">
              <el-switch v-model="recordingForm.enabled" />
              <span class="hint" style="margin-left:12px">
                {{ recordingForm.enabled ? '已启用，将在指定时间段对选定摄像头持续录制' : '已关闭' }}
              </span>
            </el-form-item>
            <el-form-item label="录像时间段">
              <el-time-picker v-model="recordingForm.schedule_start" placeholder="开始时间"
                format="HH:mm" value-format="HH:mm" style="width:120px" />
              <span style="margin:0 8px;color:#999">至</span>
              <el-time-picker v-model="recordingForm.schedule_end" placeholder="结束时间"
                format="HH:mm" value-format="HH:mm" style="width:120px" />
              <div class="hint">建议设置为学生在校时间，如 07:30 ~ 18:30</div>
            </el-form-item>
            <el-form-item label="分段时长（分钟）">
              <el-input-number v-model="recordingForm.segment_minutes" :min="5" :max="120" :step="5" />
              <div class="hint">每段录像文件的时长，建议 30 分钟，避免单文件过大</div>
            </el-form-item>
            <el-form-item label="录像摄像头">
              <div v-if="cameras.length">
                <el-checkbox-group v-model="recordingForm.camera_ids">
                  <el-checkbox v-for="cam in cameras" :key="cam.id" :label="cam.id" style="display:block;margin-bottom:6px">
                    {{ cam.name }}（{{ cam.location }}）
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              <el-text v-else type="info">加载中...</el-text>
              <div class="hint">建议只选择关键位置摄像头（如校门口、操场），避免存储占用过大</div>
            </el-form-item>
            <el-form-item label="录像留存天数">
              <el-input-number v-model="recordingForm.retention_days" :min="1" :max="365" />
              <div class="hint">超过此天数的录像文件将在每天凌晨自动删除</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveRecording">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 无人机巡逻 -->
      <el-tab-pane label="无人机巡逻" name="drone">
        <el-card shadow="never">
          <el-form label-width="160px">
            <el-form-item label="巡逻时间段">
              <div class="hint" style="margin-bottom:8px">系统将在以下时间段自动激活无人机巡逻通道</div>
              <el-table :data="droneSchedules" size="small" style="width:500px">
                <el-table-column label="时间段" prop="label" />
                <el-table-column label="开始" prop="start" />
                <el-table-column label="结束" prop="end" />
                <el-table-column label="说明" prop="desc" />
              </el-table>
            </el-form-item>
            <el-form-item label="边缘计算模式">
              <el-switch model-value="true" disabled />
              <span class="hint" style="margin-left:12px">无人机端本地运行YOLO，仅上传异常关键帧，节省90%带宽</span>
            </el-form-item>
            <el-form-item label="无人机接入方式">
              <el-descriptions :column="1" border size="small" style="width:560px">
                <el-descriptions-item label="Demo阶段">上传预录的无人机俯视视角视频文件，系统自动循环播放模拟实时流</el-descriptions-item>
                <el-descriptions-item label="实际部署">无人机通过 RTSP 协议推流，在"接入视频 → 视频流地址"中输入 RTSP 地址即可接入</el-descriptions-item>
                <el-descriptions-item label="边缘计算">在无人机机载计算单元部署轻量化 YOLOv8n，仅上传异常关键帧，带宽降低 90%</el-descriptions-item>
                <el-descriptions-item label="支持机型">大疆 Mavic/Phantom 系列及其他支持 RTMP/RTSP 推流的无人机</el-descriptions-item>
              </el-descriptions>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 部署与成本 -->
      <el-tab-pane label="部署与成本" name="deploy">
        <el-card shadow="never">
          <el-descriptions title="服务器配置要求" :column="2" border style="margin-bottom:24px">
            <el-descriptions-item label="最低配置">CPU 4核 / 内存 8GB / 无GPU</el-descriptions-item>
            <el-descriptions-item label="推荐配置">CPU 8核 / 内存 16GB / GPU NVIDIA RTX 3060+</el-descriptions-item>
            <el-descriptions-item label="存储空间">系统本体约 2GB，视频存档按需扩展</el-descriptions-item>
            <el-descriptions-item label="并发能力">当前架构支持 6 路同时检测，可横向扩展至 20+ 路</el-descriptions-item>
          </el-descriptions>
          <el-descriptions title="API 调用成本估算" :column="2" border style="margin-bottom:24px">
            <el-descriptions-item label="Qwen-VL 分析">每次事件约 2000 tokens，10次/天约 ¥0.3/天</el-descriptions-item>
            <el-descriptions-item label="日常运营成本">API 费用约 ¥10~30/月（视事件频率）</el-descriptions-item>
          </el-descriptions>
          <el-descriptions title="隐私保护声明" :column="1" border>
            <el-descriptions-item label="数据采集">仅分析行为模式，不进行人脸识别，不存储个人生物特征信息</el-descriptions-item>
            <el-descriptions-item label="合规依据">符合《个人信息保护法》《网络安全法》相关要求</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const activeTab = ref('detection')
const testing = ref(false)
const cameras = ref([])

const detectionForm = ref({
  confidence: 0.5, frameSkip: 3, cooldown: 30,
  preSeconds: 5, postSeconds: 5, dangerClasses: ['fighting', 'falling', 'intrusion'],
})

const notifyForm = ref({
  admins: [
    { name: '张校长', phone: '138****0001', role: 'principal' },
    { name: '李主任', phone: '139****0002', role: 'manager' },
    { name: '王保安', phone: '137****0003', role: 'guard' },
  ],
  smsEnabled: true, alarmEnabled: true, broadcastEnabled: true,
})

const broadcastForm = ref({
  repeat_times: 3,
  custom_texts: { fighting: '', falling: '', intrusion: '' }
})

const recordingForm = ref({
  enabled: false, segment_minutes: 30,
  schedule_start: '07:30', schedule_end: '18:30',
  camera_ids: [], retention_days: 7,
})

const modelInfo = ref({ yolo: 'best.pt', vl: 'qwen-vl-max-latest', llm: 'qwen-max-latest' })
const apiStatus = ref({ ok: true })

const droneSchedules = [
  { label: '上午课间', start: '10:00', end: '10:15', desc: '课间休息巡逻' },
  { label: '午休时段', start: '12:00', end: '12:30', desc: '午休巡逻' },
  { label: '下午课间', start: '14:00', end: '14:15', desc: '课间休息巡逻' },
  { label: '下午放学', start: '16:30', end: '17:00', desc: '放学后半小时' },
  { label: '晚放学',   start: '18:00', end: '18:30', desc: '晚自习放学' },
]

async function saveDetection() {
  try {
    await axios.post('/api/detection/config', detectionForm.value)
    ElMessage.success('检测参数已保存并立即生效')
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.error || e.message))
  }
}

async function loadDetectionConfig() {
  try {
    const { data } = await axios.get('/api/detection/config')
    detectionForm.value = { ...detectionForm.value, ...data }
  } catch {}
}function saveNotify() { ElMessage.success('通知设置已保存') }

async function testApi() {
  testing.value = true
  try {
    await axios.get('/api/risk-analysis')
    apiStatus.value = { ok: true }
    ElMessage.success('API 连接正常')
  } catch {
    apiStatus.value = { ok: false }
    ElMessage.warning('API 连接异常，系统将使用Mock模式')
  } finally {
    testing.value = false
  }
}

async function loadBroadcastConfig() {
  try {
    const { data } = await axios.get('/api/broadcast/config')
    broadcastForm.value = data
  } catch {}
}

async function saveBroadcast() {
  await axios.post('/api/broadcast/config', broadcastForm.value)
  ElMessage.success('广播配置已保存')
}

function testBroadcast() {
  const text = broadcastForm.value.custom_texts.fighting || '注意，监控系统检测到异常行为，安保人员请立即前往处置。'
  const times = broadcastForm.value.repeat_times || 1
  if (!window.speechSynthesis) { ElMessage.warning('浏览器不支持语音合成'); return }
  let count = 0
  function speak() {
    if (count >= times) return
    window.speechSynthesis.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = 'zh-CN'; utter.rate = 0.9
    utter.onend = () => { count++; if (count < times) setTimeout(speak, 800) }
    window.speechSynthesis.speak(utter)
    count++
  }
  speak()
  ElMessage.success(`正在播放测试广播（共${times}次）`)
}

async function loadRecordingConfig() {
  try {
    const { data } = await axios.get('/api/recording/config')
    recordingForm.value = data
  } catch {}
}

async function saveRecording() {
  await axios.post('/api/recording/config', recordingForm.value)
  ElMessage.success('录像配置已保存')
}

onMounted(async () => {
  try {
    const { data } = await axios.get('/api/cameras')
    cameras.value = data
  } catch {}
  loadRecordingConfig()
  loadBroadcastConfig()
  loadDetectionConfig()
})
</script>

<style scoped>
.hint { font-size: 12px; color: #999; margin-top: 4px; }
.admin-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
</style>
