<script setup lang="ts">
import { computed, nextTick, reactive, useTemplateRef, watch } from 'vue'
import { ENERGY, STATUS } from '../../constants'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useToast } from '../../composables/useToast'
import { useUiState } from '../../composables/useUiState'
import type { EnergyType, TaskStatus } from '../../types'

const store = usePlannerStore()
const ui = useUiState()
const toast = useToast()

const task = computed(() => {
  const id = ui.editingTaskId.value
  return id ? store.findTask(id) : undefined
})

const draft = reactive({
  title: '',
  date: '',
  start_time: '',
  duration_minutes: 60 as number,
  energy: 'deep' as EnergyType,
  status: 'planned' as TaskStatus,
  block: '',
  notes: '',
  actual_minutes: '' as string | number,
  reflection: '',
})

const titleRef = useTemplateRef<HTMLInputElement>('titleRef')
const reflectionRef = useTemplateRef<HTMLTextAreaElement>('reflectionRef')

watch(
  () => ui.editingTaskId.value,
  async (id) => {
    if (!id) return
    const t = store.findTask(id)
    if (!t) return
    Object.assign(draft, {
      title: t.title,
      date: t.date,
      start_time: t.start_time || '',
      duration_minutes: t.duration_minutes ?? 60,
      energy: t.energy,
      status: t.status,
      block: t.block || '',
      notes: t.notes || '',
      actual_minutes: t.actual_minutes ?? '',
      reflection: t.reflection || '',
    })
    await nextTick()
    if (ui.modalFocus.value === 'review') {
      reflectionRef.value?.focus()
    } else {
      titleRef.value?.focus()
    }
  },
  { immediate: true },
)

function close() {
  ui.closeTaskEditor()
}

function onSubmit() {
  if (!task.value || !draft.title.trim()) return
  store.updateTask(task.value.id, {
    title: draft.title.trim(),
    date: draft.date,
    start_time: draft.start_time || null,
    duration_minutes: Number(draft.duration_minutes) || null,
    energy: draft.energy,
    status: draft.status,
    block: draft.block.trim() || null,
    notes: draft.notes.trim() || null,
    reflection: draft.reflection.trim() || null,
    actual_minutes: draft.actual_minutes === '' ? null : Number(draft.actual_minutes) || 0,
  })
  ui.selectDate(draft.date) // 若改了日期，选中便于查看
  close()
  toast.show('任务已更新')
}

function onDelete() {
  if (!task.value) return
  if (!confirm(`删除任务「${task.value.title}」？`)) return
  store.deleteTask(task.value.id)
  close()
  toast.show('已删除')
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="task" class="modal-backdrop" @mousedown.self="close">
        <div class="modal">
          <div class="modal-head">
            <h3>✏️ 编辑任务</h3>
            <button class="modal-close" title="关闭" @click="close">×</button>
          </div>

          <form @submit.prevent="onSubmit">
            <label>标题</label>
            <input ref="titleRef" v-model="draft.title" class="field-input" required spellcheck="false" />

            <div class="form-row3">
              <div>
                <label>日期</label>
                <input v-model="draft.date" class="field-input" type="date" required />
              </div>
              <div>
                <label>开始时间</label>
                <input v-model="draft.start_time" class="field-input" type="time" />
              </div>
              <div>
                <label>时长（分钟）</label>
                <input v-model.number="draft.duration_minutes" class="field-input" type="number" min="5" step="5" />
              </div>
            </div>

            <div class="form-row3">
              <div>
                <label>精力类型</label>
                <select v-model="draft.energy" class="field-select">
                  <option v-for="(meta, key) in ENERGY" :key="key" :value="key">{{ meta.icon }} {{ meta.label }}</option>
                </select>
              </div>
              <div>
                <label>状态</label>
                <select v-model="draft.status" class="field-select">
                  <option v-for="(meta, key) in STATUS" :key="key" :value="key">{{ meta.icon }} {{ meta.label }}</option>
                </select>
              </div>
              <div>
                <label>实际耗时（分钟）</label>
                <input v-model="draft.actual_minutes" class="field-input" type="number" placeholder="完成后填写" />
              </div>
            </div>

            <div class="form-row">
              <div>
                <label>所属时间块</label>
                <input v-model="draft.block" class="field-input" placeholder="如：上午深度块" spellcheck="false" />
              </div>
              <div>
                <label>备注</label>
                <input v-model="draft.notes" class="field-input" placeholder="依赖 / 产出定义等" spellcheck="false" />
              </div>
            </div>

            <hr />
            <h4>📝 任务复盘（可选）</h4>
            <label>完成质量 / 卡点 / 改进</label>
            <textarea ref="reflectionRef" v-model="draft.reflection" class="field-textarea" placeholder="做得如何？卡在哪？下次怎么改？" spellcheck="false"></textarea>

            <div class="modal-actions">
              <span class="stat-sub">保存后日历与统计自动更新</span>
              <div class="spacer"></div>
              <button class="btn danger" type="button" @click="onDelete">🗑 删除</button>
              <button class="btn primary" type="submit">保存</button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
