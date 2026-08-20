<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useUiState } from '../../composables/useUiState'
import { useToast } from '../../composables/useToast'
import { todayStr } from '../../utils/date'

const store = usePlannerStore()
const ui = useUiState()
const toast = useToast()
const importFileRef = useTemplateRef<HTMLInputElement>('importFile')

const monthTitle = computed(() => `${ui.calYear.value}年${ui.calMonth.value + 1}月`)

const syncBadge = computed(() => {
  switch (store.sync.status.value) {
    case 'connecting':
      return { text: '⏳ 连接中…', cls: 'off', title: '正在连接数据服务' }
    case 'synced':
      return {
        text: '☁️ 已同步 · scripts/data',
        cls: 'on',
        title: '数据已保存到 scripts/data/task-planner-data.json（同时缓存于浏览器 localStorage）',
      }
    case 'error':
      return {
        text: '⚠️ 同步失败',
        cls: 'off',
        title: '服务器同步失败，数据仍保存在浏览器 localStorage',
      }
    default:
      return {
        text: '💾 仅本地存储',
        cls: 'off',
        title: '未连接数据服务，数据保存在浏览器 localStorage。用 node scripts/serve.js 启动后自动同步到 scripts/data',
      }
  }
})

function onExport() {
  const payload = store.exportPayload()
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `task-planner-${todayStr()}.json`
  a.click()
  URL.revokeObjectURL(a.href)
  toast.show('已导出 JSON')
}

function onImportFile(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  if (!f) return
  const r = new FileReader()
  r.onload = () => {
    try {
      const data = JSON.parse(String(r.result))
      const count = Array.isArray(data?.tasks) ? data.tasks.length : 0
      if (!confirm(`导入 ${count} 条任务并替换当前全部数据？`)) {
        input.value = ''
        return
      }
      if (store.importData(data)) {
        toast.show('导入成功')
      } else {
        toast.show('导入失败：JSON 格式不正确')
      }
    } catch {
      toast.show('导入失败：JSON 格式不正确')
    }
    input.value = ''
  }
  r.readAsText(f, 'utf-8')
}

function onClear() {
  if (!confirm('清空全部任务与复盘数据？建议先导出备份。')) return
  store.clearAll()
  toast.show('已清空')
}
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <div class="brand">
        <div class="brand-logo">📅</div>
        <div>
          <div class="brand-name">任务规划器</div>
          <div class="brand-sub">日历排期 · 任务复盘 · 每日复盘</div>
        </div>
      </div>

      <div class="month-nav">
        <button class="nav-btn" title="上个月" @click="ui.shiftMonth(-1)">‹</button>
        <div class="month-title">{{ monthTitle }}</div>
        <button class="nav-btn" title="下个月" @click="ui.shiftMonth(1)">›</button>
        <button class="btn small" @click="ui.goToday()">今天</button>
      </div>

      <div class="actions">
        <span class="sync-badge" :class="syncBadge.cls" :title="syncBadge.title">{{ syncBadge.text }}</span>
        <button class="btn small" @click="ui.openStats()">📊 统计</button>
        <button class="btn small" @click="onExport">📤 导出 JSON</button>
        <button class="btn small" @click="importFileRef?.click()">📥 导入 JSON</button>
        <input ref="importFile" type="file" accept=".json,application/json" hidden @change="onImportFile" />
        <button class="btn small danger" @click="onClear">🗑 清空</button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}

.header-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.brand { display: flex; align-items: center; gap: 10px; }

.brand-logo {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  flex: none;
  background: linear-gradient(135deg, #818cf8, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  box-shadow: 0 4px 10px rgba(99, 102, 241, 0.35);
}

.brand-name { font-size: 16px; font-weight: 700; }
.brand-sub { font-size: 12px; color: var(--text-3); }

.month-nav { display: flex; align-items: center; gap: 6px; margin-left: auto; }
.month-title { font-size: 16px; font-weight: 700; min-width: 110px; text-align: center; }

.actions { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }

.sync-badge {
  font-size: 12px;
  padding: 5px 11px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--text-3);
  background: #fff;
  white-space: nowrap;
}
.sync-badge.on { color: #15803d; background: #f0fdf4; border-color: #bbf7d0; }
.sync-badge.off { background: #f8fafc; }

@media (max-width: 640px) {
  .header-inner { padding: 10px 12px; }
  .month-nav { margin-left: 0; }
}
</style>
