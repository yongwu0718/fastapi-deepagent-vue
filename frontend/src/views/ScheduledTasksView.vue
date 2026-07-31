<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { client } from '@/api/client/client.gen'

interface ScheduledTask {
  id: string
  username: string
  title: string
  message: string
  execute_hour: number
  execute_minute: number
  is_active: boolean
  last_run_at: string | null
  created_at: string
}

const tasks = ref<ScheduledTask[]>([])
const loading = ref(false)
const error = ref('')
const showForm = ref(false)
const editingId = ref<string | null>(null)
const refreshingId = ref<string | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

// 表单数据
const formData = ref({
  title: '',
  message: '',
  execute_hour: 9,
  execute_minute: 0,
  is_active: true,
})

const timeOptions = computed(() => {
  const hours = Array.from({ length: 24 }, (_, i) => i)
  const minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
  return { hours, minutes }
})

function formatTime(hour: number, minute: number): string {
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
}

async function fetchTasks() {
  loading.value = true
  error.value = ''
  try {
    const res = await client.get({ url: '/scheduled-tasks' })
    tasks.value = (res.data as any) ?? []
  } catch (e: any) {
    error.value = e?.body?.detail ?? String(e)
  } finally {
    loading.value = false
  }
}

async function refreshTask(taskId: string) {
  refreshingId.value = taskId
  try {
    const res = await client.get({ url: '/scheduled-tasks' })
    const all: ScheduledTask[] = (res.data as any) ?? []
    const updated = all.find(t => t.id === taskId)
    if (updated) {
      const idx = tasks.value.findIndex(t => t.id === taskId)
      if (idx !== -1) tasks.value[idx] = updated
    }
  } catch {
    // 静默失败
  } finally {
    refreshingId.value = null
  }
}

function isRecentlyRun(task: ScheduledTask): boolean {
  if (!task.last_run_at) return false
  const runTime = new Date(task.last_run_at)
  const diff = Date.now() - runTime.getTime()
  return diff < 5 * 60 * 1000 // 5 分钟内算"刚执行"
}

function formatRunStatus(task: ScheduledTask): string {
  if (!task.last_run_at) return '未执行'
  const runTime = new Date(task.last_run_at)
  const now = new Date()
  const diff = now.getTime() - runTime.getTime()
  if (diff < 60 * 1000) return '刚刚执行'
  if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前执行`
  if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前执行`
  return task.last_run_at
}

function nextRunTime(task: ScheduledTask): string {
  if (!task.is_active) return '已禁用'
  const now = new Date()
  let target = new Date()
  target.setHours(task.execute_hour, task.execute_minute, 0, 0)
  if (target <= now) {
    target.setDate(target.getDate() + 1) // 明天
  }
  const hours = Math.floor((target.getTime() - now.getTime()) / 3600000)
  const mins = Math.floor(((target.getTime() - now.getTime()) % 3600000) / 60000)
  if (hours === 0) return `${mins} 分钟后`
  return `${hours} 小时 ${mins} 分钟后`
}

function openCreateForm() {
  editingId.value = null
  formData.value = { title: '', message: '', execute_hour: 9, execute_minute: 0, is_active: true }
  showForm.value = true
}

function openEditForm(task: ScheduledTask) {
  editingId.value = task.id
  formData.value = {
    title: task.title,
    message: task.message,
    execute_hour: task.execute_hour,
    execute_minute: task.execute_minute,
    is_active: task.is_active,
  }
  showForm.value = true
}

async function submitForm() {
  error.value = ''
  const body = {
    title: formData.value.title,
    message: formData.value.message,
    execute_hour: formData.value.execute_hour,
    execute_minute: formData.value.execute_minute,
    is_active: formData.value.is_active,
  }

  try {
    if (editingId.value) {
      await client.put({
        url: `/scheduled-tasks/${editingId.value}`,
        body,
      })
    } else {
      await client.post({ url: '/scheduled-tasks', body })
    }
    showForm.value = false
    await fetchTasks()
  } catch (e: any) {
    error.value = e?.body?.detail ?? String(e)
  }
}

async function deleteTask(id: string) {
  if (!confirm('确认删除此定时任务？')) return
  try {
    await client.delete({ url: `/scheduled-tasks/${id}` })
    await fetchTasks()
  } catch (e: any) {
    error.value = e?.body?.detail ?? String(e)
  }
}

async function toggleActive(task: ScheduledTask) {
  try {
    await client.put({
      url: `/scheduled-tasks/${task.id}`,
      body: { is_active: !task.is_active },
    })
    await fetchTasks()
  } catch (e: any) {
    error.value = e?.body?.detail ?? String(e)
  }
}

onMounted(() => {
  fetchTasks()
  // 每 30 秒自动刷新任务列表，追踪执行状态
  pollTimer = setInterval(fetchTasks, 30000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="tasks-page">
    <div class="tasks-header">
      <h1>定时任务</h1>
      <button class="btn-primary" @click="openCreateForm">+ 新建任务</button>
    </div>

    <div v-if="error" class="tasks-error">{{ error }}</div>

    <div v-if="loading" class="tasks-loading">加载中...</div>

    <div v-else-if="tasks.length === 0" class="tasks-empty">
      暂无定时任务，点击「新建任务」创建
    </div>

    <div v-else class="tasks-list">
      <div v-for="task in tasks" :key="task.id" class="task-card" :class="{ inactive: !task.is_active }">
        <div class="task-info">
          <div class="task-title-row">
            <span class="task-title">{{ task.title || '未命名任务' }}</span>
            <span v-if="isRecentlyRun(task)" class="task-badge task-badge-success">刚执行</span>
            <span v-else-if="!task.is_active" class="task-badge task-badge-muted">已禁用</span>
            <span v-else class="task-badge task-badge-pending">待执行</span>
          </div>
          <div class="task-message">{{ task.message }}</div>
          <div class="task-meta">
            <span class="task-time">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              {{ formatTime(task.execute_hour, task.execute_minute) }}
            </span>
            <span class="task-status">{{ formatRunStatus(task) }}</span>
            <span class="task-next" v-if="task.is_active">下次: {{ nextRunTime(task) }}</span>
          </div>
        </div>
        <div class="task-actions">
          <label class="task-toggle">
            <input type="checkbox" :checked="task.is_active" @change="toggleActive(task)" />
            <span>{{ task.is_active ? '启用' : '禁用' }}</span>
          </label>
          <button class="btn-icon" title="刷新状态" :disabled="refreshingId === task.id" @click="refreshTask(task.id)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ spinning: refreshingId === task.id }">
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
          </button>
          <button class="btn-icon" title="编辑" @click="openEditForm(task)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
          <button class="btn-icon btn-danger" title="删除" @click="deleteTask(task.id)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 新建/编辑表单弹窗 -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal-card">
        <div class="modal-header">
          <h2>{{ editingId ? '编辑任务' : '新建定时任务' }}</h2>
          <button class="btn-close" @click="showForm = false">×</button>
        </div>

        <form class="modal-form" @submit.prevent="submitForm">
          <div class="form-group">
            <label>任务名称（可选）</label>
            <input v-model="formData.title" type="text" placeholder="如：每日摘要" maxlength="100" />
          </div>

          <div class="form-group">
            <label>预设消息</label>
            <textarea v-model="formData.message" rows="4" placeholder="如：请总结今天的对话内容" required></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>执行时间（24小时制）</label>
              <div class="time-select">
                <select v-model.number="formData.execute_hour">
                  <option v-for="h in timeOptions.hours" :key="h" :value="h">
                    {{ String(h).padStart(2, '0') }}
                  </option>
                </select>
                <span>:</span>
                <select v-model.number="formData.execute_minute">
                  <option v-for="m in timeOptions.minutes" :key="m" :value="m">
                    {{ String(m).padStart(2, '0') }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>状态</label>
              <label class="task-toggle">
                <input type="checkbox" v-model="formData.is_active" />
                <span>{{ formData.is_active ? '启用' : '禁用' }}</span>
              </label>
            </div>
          </div>

          <div v-if="error" class="tasks-error">{{ error }}</div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="showForm = false">取消</button>
            <button type="submit" class="btn-primary">{{ editingId ? '保存' : '创建' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tasks-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 32px 24px;
}

.tasks-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.tasks-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-h);
}

.tasks-error {
  padding: 10px 14px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #ef4444;
  font-size: 13px;
  margin-bottom: 16px;
}

.tasks-loading, .tasks-empty {
  text-align: center;
  padding: 48px 0;
  color: var(--text);
  font-size: 14px;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: opacity 0.2s;
}

.task-card.inactive {
  opacity: 0.5;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.task-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-h);
}

.task-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.task-badge-success {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.task-badge-pending {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.task-badge-muted {
  background: rgba(107, 99, 117, 0.15);
  color: #6b6375;
}

.task-message {
  font-size: 13px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 6px;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text);
  opacity: 0.7;
}

.task-time {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  color: var(--accent);
  opacity: 1;
}

.task-status {
  color: #22c55e;
}

.task-next {
  color: var(--text);
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.task-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text);
}

.task-toggle input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.btn-primary {
  padding: 8px 16px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  color: var(--text-h);
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.btn-secondary:hover {
  background: var(--code-bg);
}

.btn-icon {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.btn-icon:hover {
  background: var(--code-bg);
  color: var(--text-h);
}

.btn-icon.btn-danger:hover {
  background: rgba(220, 38, 38, 0.1);
  color: #dc2626;
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 24px;
}

.modal-card {
  width: 100%;
  max-width: 500px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-h);
}

.btn-close {
  border: none;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
  color: var(--text);
  line-height: 1;
}

.modal-form {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-h);
}

.form-group input,
.form-group textarea {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text-h);
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group textarea:focus {
  border-color: var(--accent);
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
}

.time-select {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-select select {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text-h);
  font-size: 14px;
  cursor: pointer;
  outline: none;
}

.time-select span {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}
</style>
