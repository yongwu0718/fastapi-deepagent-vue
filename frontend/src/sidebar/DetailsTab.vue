<script setup lang="ts">
</script>

<template>
  <div class="tab-content">
    <div class="tab-empty">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.3">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
      <p>此处可展示附加信息</p>
    </div>
  </div>
</template>

<style scoped>
.tab-content {
  padding: 16px;
}

.tab-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: var(--text, #6b6375);
  opacity: 0.5;
  gap: 12px;
  font-size: 13px;
  text-align: center;
}
</style>
