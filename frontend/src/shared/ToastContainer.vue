<script setup lang="ts">
/**
 * Toast 通知容器 — 在 App.vue 中挂载一次即可
 * 支持入场/退出动画和类型图标
 */
import { ref, onUnmounted } from 'vue'
import type { Toast } from './useToast'
import { subscribeToasts, dismissToast as dismiss } from './useToast'

const toasts = ref<Toast[]>([])

const unsub = subscribeToasts((newToasts) => {
  toasts.value = newToasts
})

onUnmounted(unsub)

function iconFor(toast: Toast): string {
  switch (toast.type) {
    case 'success': return '✓'
    case 'error': return '✕'
    case 'warning': return '⚠'
    default: return 'ℹ'
  }
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          :class="['toast', `toast--${t.type}`]"
          role="alert"
        >
          <span class="toast-icon">{{ iconFor(t) }}</span>
          <div class="toast-body">
            <div class="toast-title">{{ t.title }}</div>
            <div v-if="t.description" class="toast-desc">{{ t.description }}</div>
          </div>
          <button class="toast-close" @click="dismiss(t.id)">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 300px;
  max-width: 420px;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--bg, #fff);
  border: 1px solid var(--border, #e5e4e7);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  pointer-events: auto;
  font-size: 14px;
  line-height: 1.4;
}

.toast--success {
  border-left: 3px solid #10b981;
}
.toast--error {
  border-left: 3px solid #ef4444;
}
.toast--warning {
  border-left: 3px solid #f59e0b;
}
.toast--info {
  border-left: 3px solid var(--accent, #aa3bff);
}

.toast-icon {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
}

.toast--success .toast-icon { background: #10b981; }
.toast--error .toast-icon { background: #ef4444; }
.toast--warning .toast-icon { background: #f59e0b; }
.toast--info .toast-icon { background: var(--accent, #aa3bff); }

.toast-body {
  flex: 1;
  min-width: 0;
}

.toast-title {
  font-weight: 600;
  color: var(--text-h, #08060d);
  margin: 0 0 2px;
}

.toast-desc {
  font-size: 13px;
  color: var(--text, #6b6375);
  opacity: 0.8;
}

.toast-close {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text, #6b6375);
  opacity: 0.4;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  transition: opacity 0.15s;
}

.toast-close:hover {
  opacity: 1;
}

/* ── 动画 ── */
.toast-enter-active {
  transition: all 0.3s ease;
}
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}
</style>
