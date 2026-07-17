<script setup lang="ts">
import { ref } from 'vue'
import type { FileEntry } from '@/api/files'

const props = defineProps<{
  entry: FileEntry
}>()

const emit = defineEmits<{
  confirm: [newName: string]
  cancel: []
}>()

const newName = ref(props.entry.name)

function handleConfirm() {
  const trimmed = newName.value.trim()
  if (!trimmed || trimmed === props.entry.name) return
  emit('confirm', trimmed)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') handleConfirm()
  if (e.key === 'Escape') emit('cancel')
}
</script>

<template>
  <div class="dialog-overlay" @mousedown.self="emit('cancel')">
    <div class="dialog">
      <div class="dialog-header">
        <h4>重命名</h4>
      </div>
      <div class="dialog-body">
        <label class="dialog-label">
          新名称
          <input
            v-model="newName"
            type="text"
            class="dialog-input"
            autofocus
            @keydown="onKeydown"
          />
        </label>
        <p class="dialog-hint">
          当前: {{ entry.path }}
        </p>
      </div>
      <div class="dialog-footer">
        <button class="dialog-btn dialog-btn-cancel" @click="emit('cancel')">取消</button>
        <button
          class="dialog-btn dialog-btn-confirm"
          @click="handleConfirm"
          :disabled="!newName.trim() || newName.trim() === entry.name"
        >
          确认
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.dialog {
  background: var(--bg, #fff);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  width: 380px;
  max-width: 90vw;
  overflow: hidden;
}

.dialog-header {
  padding: 16px 20px 0;
}

.dialog-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-h, #08060d);
}

.dialog-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dialog-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text, #6b6375);
}

.dialog-input {
  padding: 8px 10px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  outline: none;
  color: var(--text-h, #08060d);
  background: var(--bg, #fff);
}

.dialog-input:focus {
  border-color: var(--accent, #aa3bff);
  box-shadow: 0 0 0 2px rgba(170, 59, 255, 0.12);
}

.dialog-hint {
  margin: 0;
  font-size: 11px;
  color: var(--text-m, #9b8eaa);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid var(--border, #e5e4e7);
}

.dialog-btn {
  padding: 6px 16px;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.12s;
  background: var(--bg, #fff);
  color: var(--text, #6b6375);
}

.dialog-btn-cancel:hover {
  background: var(--bg-hover, #f5f3f7);
}

.dialog-btn-confirm {
  background: var(--accent, #aa3bff);
  color: #fff;
  border-color: var(--accent, #aa3bff);
}

.dialog-btn-confirm:hover {
  background: var(--accent-hover, #9333ea);
}

.dialog-btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
