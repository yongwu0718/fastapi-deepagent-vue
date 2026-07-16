<script setup lang="ts">
defineProps<{
  items: { label: string; path: string }[]
}>()

const emit = defineEmits<{
  navigate: [path: string]
}>()
</script>

<template>
  <div class="breadcrumb">
    <template v-for="(item, idx) in items" :key="item.path">
      <span v-if="idx > 0" class="bc-sep">/</span>
      <button
        class="bc-item"
        :class="{ active: idx === items.length - 1 }"
        @click="emit('navigate', item.path)"
      >
        {{ item.label }}
      </button>
    </template>
  </div>
</template>

<style scoped>
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--border, #e5e4e7);
  overflow-x: auto;
  flex-shrink: 0;
  scrollbar-width: none;
}

.breadcrumb::-webkit-scrollbar {
  display: none;
}

.bc-sep {
  font-size: 12px;
  color: var(--text-m, #9b8eaa);
  flex-shrink: 0;
}

.bc-item {
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-m, #9b8eaa);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.12s;
  white-space: nowrap;
  flex-shrink: 0;
}

.bc-item:hover {
  color: var(--text-h, #08060d);
  background: var(--bg-hover, #f5f3f7);
}

.bc-item.active {
  color: var(--text-h, #08060d);
  font-weight: 600;
}
</style>
