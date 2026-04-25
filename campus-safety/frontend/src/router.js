import { createRouter, createWebHistory } from 'vue-router'
import Login from './views/Login.vue'
import Monitor from './views/Monitor.vue'
import Events from './views/Events.vue'
import Stats from './views/Stats.vue'
import Chat from './views/Chat.vue'
import Dashboard from './views/Dashboard.vue'
import Settings from './views/Settings.vue'
import Patrol from './views/Patrol.vue'
import Recordings from './views/Recordings.vue'
import DronePlanner from './views/DronePlanner.vue'

const routes = [
  { path: '/login', component: Login, meta: { public: true } },
  { path: '/', redirect: '/monitor' },
  { path: '/monitor', component: Monitor, meta: { title: '实时监控', permission: 'monitor' } },
  { path: '/events', component: Events, meta: { title: '事件记录', permission: 'events' } },
  { path: '/recordings', component: Recordings, meta: { title: '历史录像', permission: 'events' } },
  { path: '/stats', component: Stats, meta: { title: '数据统计', permission: 'stats' } },
  { path: '/chat', component: Chat, meta: { title: '智能查询', permission: 'chat' } },
  { path: '/patrol', component: Patrol, meta: { title: '巡逻任务', permission: 'events' } },
  { path: '/drone', component: DronePlanner, meta: { title: '无人机规划', permission: 'dashboard' } },
  { path: '/dashboard', component: Dashboard, meta: { title: '安全大屏', permission: 'dashboard', fullscreen: true } },
  { path: '/settings', component: Settings, meta: { title: '系统设置', permission: 'settings' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.public) return next()
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  if (!user) return next('/login')
  const perms = user.permissions || []
  if (to.meta.permission && !perms.includes(to.meta.permission)) {
    return next('/monitor')
  }
  next()
})

export default router
