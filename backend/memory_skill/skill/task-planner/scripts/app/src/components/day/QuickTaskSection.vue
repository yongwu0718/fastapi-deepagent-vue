<script setup lang="ts">
import { computed, reactive } from 'vue'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useToast } from '../../composables/useToast'
import { useUiState } from '../../composables/useUiState'
import { minText } from '../../utils/format'

const store = usePlannerStore()
const ui = useUiState()
const toast = useToast()

const form = reactive({ title: '', duration: 10 })

const quickTasks = computed(() =>
  store.tasksOf(ui.selectedDate.value).filter(t => t.is_quick),
)

function onSubmit() {
  if (!form.title.trim()) return
  store.addQuickTask(form.title, Number(form.duration) || 10, ui.selectedDate.value)
  form.title = ''
  toast.show('已加入随手池')
}

function onToggle(id: string) {
  store.toggleQuick(id)
}

function onDelete(id: string) {
  store.deleteTask(id)
  toast.show('已删除')
}
</script>

<template>
  <section class="panel-section">
    <h3 class="section-title">
      📥 随手池
      <span v-if="quickTasks.length" class="section-count">{{ quickTasks.length }} 条</span>
    </h3>

    <form class="quick-form" autocomplete="off" @submit.prevent="onSubmit">
      <input v-model="form.title" class="field-input" placeholder="微任务（<15分钟 + 单一动作 + 无依赖）" required />
      <select v-model.number="form.duration" class="field-select">
        <option :value="5">5分钟</option>
        <option :value="10">10分钟</option>
        <option :value="15">15分钟</option>
      </select>
      <button class="btn primary" type="submit">＋</button>
    </form>

    <div class="quick-list">
      <div
        v-for="q in quickTasks"
        :key="q.id"
        class="quick-row"
        :class="{ done: q.status === 'done' }"
      >
        <button
          class="quick-check"
          :class="{ done: q.status === 'done' }"
          title="切换完成"
          @click="onToggle(q.id)"
        >{{ q.status === 'done' ? '✓' : '' }}</button>
        <span class="q-title">{{ q.title }}</span>
        <span class="q-dur">{{ minText(q.duration_minutes) }}</span>
        <button class="icon-btn del" title="删除" @click="onDelete(q.id)">🗑</button>
      </div>
      <div v-if="!quickTasks.length" class="empty">
        随手池为空 · 微任务（&lt;15分钟）见缝插针完成，每日清空
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel-section { margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); }

.section-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-2);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.section-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-3);
  font-weight: 500;
  background: #f8fafc;
  border-radius: 999px;
  padding: 1px 8px;
}

.quick-form { display: flex; gap: 7px; margin-bottom: 10px; }
.quick-form .field-select { width: auto; flex: none; }

.quick-list { display: flex; flex-direction: column; gap: 5px; }

.quick-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 9px;
  background: #fafbfd;
  border: 1px dashed var(--border);
  border-radius: 8px;
}
.quick-row.done .q-title { text-decoration: line-through; color: var(--text-3); }
.q-title { flex: 1; font-size: 13px; }
.q-dur { font-size: 11px; color: var(--text-3); }

.quick-check {
  flex: none;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  border: 2px solid #cbd5e1;
  background: #fff;
  font-size: 11px;
  color: #fff;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.quick-check.done { border-color: var(--ok); background: var(--ok); }
</style>
