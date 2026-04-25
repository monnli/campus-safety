<template>
  <div>
    <el-card shadow="never" style="margin-bottom:16px">
      <template #header>
        <span>今日巡逻任务</span>
        <el-button type="primary" size="small" style="float:right" @click="generateTasks" :loading="generating">
          AI 生成今日任务
        </el-button>
      </template>

      <el-empty v-if="!tasks.length" description="暂无巡逻任务，点击「AI 生成今日任务」自动规划">
        <el-button type="primary" @click="generateTasks" :loading="generating">AI 生成今日任务</el-button>
      </el-empty>

      <el-table v-else :data="tasks" stripe>
        <el-table-column label="时间" prop="time" width="80" />
        <el-table-column label="时段" prop="label" width="100" />
        <el-table-column label="巡逻区域" prop="area" width="120">
          <template #default="{ row }">
            <el-tag type="warning">{{ row.area }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="负责人" prop="guard" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'done' ? 'success' : 'info'">
              {{ row.status === 'done' ? '已完成' : '待执行' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button v-if="row.status !== 'done'" size="small" type="success" @click="completeTask(row)">
              签到完成
            </el-button>
            <span v-else style="color:#52c41a;font-size:13px">✓ 已签到</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 任务完成率 -->
    <el-card shadow="never" v-if="tasks.length">
      <template #header>今日完成情况</template>
      <el-row :gutter="24" style="text-align:center">
        <el-col :span="8">
          <div class="patrol-num" style="color:#1677ff">{{ tasks.length }}</div>
          <div class="patrol-label">计划任务</div>
        </el-col>
        <el-col :span="8">
          <div class="patrol-num" style="color:#52c41a">{{ doneCount }}</div>
          <div class="patrol-label">已完成</div>
        </el-col>
        <el-col :span="8">
          <div class="patrol-num" style="color:#fa8c16">{{ tasks.length - doneCount }}</div>
          <div class="patrol-label">待执行</div>
        </el-col>
      </el-row>
      <el-progress :percentage="Math.round(doneCount / tasks.length * 100)" style="margin-top:16px" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const tasks = ref([])
const generating = ref(false)

const doneCount = computed(() => tasks.value.filter(t => t.status === 'done').length)

async function loadTasks() {
  const { data } = await axios.get('/api/patrol')
  tasks.value = data
}

async function generateTasks() {
  generating.value = true
  try {
    const { data } = await axios.post('/api/patrol/generate')
    tasks.value = data
    ElMessage.success('AI 已根据风险分析生成今日巡逻任务')
  } finally {
    generating.value = false
  }
}

async function completeTask(task) {
  await axios.post(`/api/patrol/${task.id}/done`)
  task.status = 'done'
  ElMessage.success(`${task.time} ${task.area} 巡逻任务已完成`)
}

onMounted(loadTasks)
</script>

<style scoped>
.patrol-num { font-size: 32px; font-weight: 700; }
.patrol-label { font-size: 13px; color: #999; margin-top: 4px; }
</style>
