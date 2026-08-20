<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppHeader from './components/common/AppHeader.vue'
import CalendarGrid from './components/calendar/CalendarGrid.vue'
import DayPanel from './components/day/DayPanel.vue'
import TaskEditModal from './components/modals/TaskEditModal.vue'
import StatsModal from './components/modals/StatsModal.vue'
import ToastHost from './components/common/ToastHost.vue'
import { useUiState } from './composables/useUiState'

const ui = useUiState()

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    ui.closeTaskEditor()
    ui.closeStats()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <AppHeader />
  <main class="app-main">
    <CalendarGrid />
    <DayPanel />
  </main>
  <TaskEditModal />
  <StatsModal />
  <ToastHost />
</template>

<style scoped>
.app-main {
  max-width: 1440px;
  margin: 0 auto;
  padding: 18px 20px 40px;
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

@media (max-width: 1080px) {
  .app-main { flex-direction: column; }
}
@media (max-width: 640px) {
  .app-main { padding: 12px; }
}
</style>
