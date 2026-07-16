<script setup lang="ts">
defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  click: []
}>()
</script>

<template>
  <Transition name="scroll-fade">
    <button
      v-if="visible"
      class="scroll-to-bottom"
      @click="emit('click')"
      title="滚动到底部"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="5" x2="12" y2="19" />
        <polyline points="19 12 12 19 5 12" />
      </svg>
    </button>
  </Transition>
</template>

<style scoped>
.scroll-to-bottom {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 12px;
  z-index: 10;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--border, #e5e4e7);
  background: var(--bg, #fff);
  color: var(--text, #6b6375);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: background 0.15s, color 0.15s;
}

.scroll-to-bottom:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
}

.scroll-fade-enter-active,
.scroll-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.scroll-fade-enter-from,
.scroll-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}
</style>
