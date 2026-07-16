<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useOutlineItems, type NavItem } from '@/chat/core/useContentNav'

const { outlineItems } = useOutlineItems()
const outlineCount = computed(() => outlineItems.value.length)
const activeOutlineId = ref<string | null>(null)

function scrollToOutline(item: NavItem) {
  const el = document.getElementById(item.anchorId)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

let outlineObserver: IntersectionObserver | null = null

function observeOutlines() {
  outlineObserver?.disconnect()
  outlineObserver = new IntersectionObserver(
    (entries) => {
      let topEntry: IntersectionObserverEntry | null = null
      for (const e of entries) {
        if (e.isIntersecting) {
          if (!topEntry || e.boundingClientRect.top < topEntry.boundingClientRect.top) {
            topEntry = e
          }
        }
      }
      if (topEntry) activeOutlineId.value = topEntry.target.id
    },
    { root: null, rootMargin: '-20% 0px -50% 0px', threshold: 0 },
  )
  for (const item of outlineItems.value) {
    const el = document.getElementById(item.anchorId)
    if (el) outlineObserver.observe(el)
  }
}

onMounted(() => {
  if (outlineItems.value.length > 0) nextTick(() => observeOutlines())
})

watch(outlineItems, () => nextTick(() => observeOutlines()), { deep: true })

onUnmounted(() => {
  outlineObserver?.disconnect()
  outlineObserver = null
})
</script>

<template>
  <div class="tab-content">
    <div v-if="outlineCount === 0" class="tab-empty">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.3">
        <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" />
        <line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
      </svg>
      <p>暂无用户消息</p>
    </div>
    <div v-else class="outline-list">
      <button
        v-for="item in outlineItems"
        :key="item.anchorId"
        :class="['outline-item', { 'outline-item--active': activeOutlineId === item.anchorId }]"
        @click="scrollToOutline(item)"
      >
        <span class="outline-dot" />
        <span class="outline-text">{{ item.preview }}</span>
      </button>
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

/* ── 大纲 Tab ── */
.outline-list {
  display: flex;
  flex-direction: column;
}

.outline-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: 12.5px;
  line-height: 1.4;
  color: var(--text, #6b6375);
  text-align: left;
  transition: background 0.12s, color 0.12s;
}

.outline-item:hover {
  background: var(--code-bg, #f4f3ec);
}

.outline-item--active {
  color: var(--accent, #aa3bff);
  background: rgba(170, 59, 255, 0.06);
  font-weight: 600;
}

.outline-item--active:hover {
  background: rgba(170, 59, 255, 0.1);
}

.outline-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
  opacity: 0.6;
  margin-top: 4px;
}

.outline-item--active .outline-dot {
  background: var(--accent, #aa3bff);
  opacity: 1;
}

.outline-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
