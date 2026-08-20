<script setup lang="ts">
import { useToast } from '../../composables/useToast'

const toast = useToast()
</script>

<template>
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="toast.visible.value" class="toast">{{ toast.message.value }}</div>
    </Transition>
  </Teleport>
</template>
