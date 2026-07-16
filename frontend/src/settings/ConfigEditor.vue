<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  load: () => Promise<string>
  save: (content: string) => Promise<void>
  language: 'yaml' | 'json' | 'markdown'
  label: string
}>()

const content = ref('')
const loading = ref(false)
const saving = ref(false)
const status = ref('')

onMounted(async () => {
  loading.value = true
  try {
    content.value = await props.load()
  } catch (e: any) {
    status.value = '加载失败: ' + (e?.body?.detail ?? String(e))
  } finally {
    loading.value = false
  }
})

async function handleSave() {
  saving.value = true
  status.value = ''
  try {
    await props.save(content.value)
    status.value = '已保存 ✓'
  } catch (e: any) {
    status.value = '保存失败: ' + (e?.body?.detail ?? String(e))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="editor-panel">
    <div class="editor-toolbar">
      <span class="editor-label">{{ label }}</span>
      <div class="editor-actions">
        <span v-if="status" class="editor-status">{{ status }}</span>
        <button
          class="save-btn"
          :disabled="saving || loading"
          @click="handleSave"
        >
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="editor-loading">加载中...</div>
    <textarea
      v-else
      v-model="content"
      class="editor-textarea"
      spellcheck="false"
    />
  </div>
</template>

<style scoped>
.editor-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.editor-label {
  font-size: 13px;
  color: #64748b;
  font-family: monospace;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.editor-status {
  font-size: 12px;
  color: #059669;
}

.save-btn {
  padding: 5px 16px;
  border: none;
  border-radius: 5px;
  background: #16a34a;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.editor-loading {
  padding: 40px;
  text-align: center;
  color: #94a3b8;
}

.editor-textarea {
  flex: 1;
  width: 100%;
  padding: 16px;
  border: none;
  resize: none;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
  font-size: 13px;
  line-height: 1.6;
  tab-size: 4;
  background: #fff;
  color: #1e293b;
  outline: none;
}
</style>
