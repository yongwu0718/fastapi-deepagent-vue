<script setup lang="ts">
import type { FileEntry } from '@/api/files'

defineProps<{
  entry: FileEntry
}>()

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<template>
  <div class="dialog-overlay" @mousedown.self="emit('cancel')">
    <div class="dialog">
      <div class="dialog-header">
        <h4>确认删除</h4>
      </div>
      <div class="dialog-body">
        <p class="dialog-message">
          确定要删除 <strong>{{ entry.name }}</strong> 吗？
          <template v-if="entry.type === 'directory'">此操作将递归删除目录及其所有内容。</template>
          此操作不可撤销。
        </p>
      </div>
      <div class="dialog-footer">
        <button class="dialog-btn dialog-btn-cancel" @click="emit('cancel')">取消</button>
        <button class="dialog-btn dialog-btn-danger" @click="emit('confirm')">删除</button>
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
}

.dialog-message {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text, #6b6375);
}

.dialog-message strong {
  color: var(--text-h, #08060d);
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

.dialog-btn-danger {
  background: #ef4444;
  color: #fff;
  border-color: #ef4444;
}

.dialog-btn-danger:hover {
  background: #dc2626;
}
</style>
