<script setup lang="ts">
import { reactive, watch } from 'vue'
import { RATING_FACES } from '../../constants'
import { usePlannerStore } from '../../composables/usePlannerStore'
import { useToast } from '../../composables/useToast'
import { useUiState } from '../../composables/useUiState'

const store = usePlannerStore()
const ui = useUiState()
const toast = useToast()

const form = reactive({
  highlights: '',
  problems: '',
  improvements: '',
  energy_rating: null as number | null,
})

// 切换日期时从 store 恢复当日复盘（表单本地编辑态不受重渲染影响）
watch(
  () => ui.selectedDate.value,
  (date) => {
    const r = store.state.reviews[date]
    form.highlights = r?.highlights || ''
    form.problems = r?.problems || ''
    form.improvements = r?.improvements || ''
    form.energy_rating = r?.energy_rating ?? null
  },
  { immediate: true },
)

const exists = () => !!store.state.reviews[ui.selectedDate.value]

function toggleRating(r: number) {
  form.energy_rating = form.energy_rating === r ? null : r
}

function onSave() {
  const hasContent = form.highlights.trim() || form.problems.trim() || form.improvements.trim()
  if (!hasContent && form.energy_rating == null) {
    toast.show('先写点什么，或选一个精力评分')
    return
  }
  store.saveReview(ui.selectedDate.value, {
    highlights: form.highlights.trim(),
    problems: form.problems.trim(),
    improvements: form.improvements.trim(),
    energy_rating: form.energy_rating,
  })
  toast.show('复盘已保存')
}

function onDelete() {
  if (!exists()) return
  if (!confirm('删除当日复盘？')) return
  store.deleteReview(ui.selectedDate.value)
  form.highlights = ''
  form.problems = ''
  form.improvements = ''
  form.energy_rating = null
  toast.show('复盘已删除')
}
</script>

<template>
  <section class="panel-section">
    <h3 class="section-title">
      📝 每日复盘
      <span v-if="exists()" class="saved-tag">已保存 · 可修改后再次保存</span>
    </h3>

    <form autocomplete="off" @submit.prevent="onSave">
      <label>今日亮点</label>
      <textarea v-model="form.highlights" class="field-textarea" placeholder="今天做得好的 1-3 件事" spellcheck="false"></textarea>

      <label>遇到的问题</label>
      <textarea v-model="form.problems" class="field-textarea" placeholder="卡点 / 分心源 / 精力低谷出现在哪" spellcheck="false"></textarea>

      <label>明日改进</label>
      <textarea v-model="form.improvements" class="field-textarea" placeholder="明天要调整的一件小事" spellcheck="false"></textarea>

      <label>精力状态</label>
      <div class="rating-row">
        <button
          v-for="r in 5"
          :key="r"
          type="button"
          class="rating-btn"
          :class="{ active: form.energy_rating === r }"
          :title="`${r} 分`"
          @click="toggleRating(r)"
        >{{ RATING_FACES[r] }}</button>
      </div>

      <div class="review-actions">
        <button class="btn primary" type="submit">保存复盘</button>
        <button v-if="exists()" class="btn danger" type="button" @click="onDelete">删除</button>
      </div>
    </form>
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
  gap: 8px;
  margin-bottom: 10px;
}
.saved-tag { font-size: 11px; color: #15803d; font-weight: 500; }

form label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  margin: 10px 0 5px;
}
form label:first-of-type { margin-top: 0; }

.rating-row { display: flex; gap: 8px; }
.rating-btn {
  width: 38px;
  height: 38px;
  font-size: 20px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: #fff;
  filter: grayscale(0.75);
  transition: all 0.15s;
}
.rating-btn:hover { filter: none; border-color: #c7d2fe; transform: scale(1.08); }
.rating-btn.active { filter: none; background: var(--accent-soft); border-color: var(--accent); }

.review-actions { display: flex; gap: 8px; margin-top: 14px; }
</style>
