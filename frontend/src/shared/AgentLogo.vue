<script setup lang="ts">
defineProps<{
  size?: number
}>()
</script>

<template>
  <svg
    :width="size ?? 32"
    :height="size ?? 32"
    viewBox="0 0 32 32"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    class="agent-logo"
  >
    <!-- 外圆 -->
    <circle cx="16" cy="16" r="14" stroke="var(--accent, #aa3bff)" stroke-width="2" />
    <!-- 内圆 / 核心 -->
    <circle cx="16" cy="16" r="6" fill="var(--accent, #aa3bff)" opacity="0.3" />
    <circle cx="16" cy="16" r="3" fill="var(--accent, #aa3bff)" />
    <!-- 轨道 -->
    <ellipse
      cx="16" cy="16"
      rx="11" ry="4"
      stroke="var(--accent, #aa3bff)"
      stroke-width="1.5"
      stroke-dasharray="4 3"
      transform="rotate(-30 16 16)"
      opacity="0.5"
    />
    <ellipse
      cx="16" cy="16"
      rx="11" ry="4"
      stroke="var(--accent, #aa3bff)"
      stroke-width="1.5"
      stroke-dasharray="4 3"
      transform="rotate(45 16 16)"
      opacity="0.5"
    />
  </svg>
</template>

<style scoped>
.agent-logo {
  flex-shrink: 0;
}
</style>
