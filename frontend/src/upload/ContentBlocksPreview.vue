<script setup lang="ts">
import type { ContentBlock } from './useFileUpload'

defineProps<{
  blocks: readonly ContentBlock[]
}>()

const emit = defineEmits<{
  remove: [index: number]
}>()

/** 图片类型生成 object URL 用于预览 */
function blockPreviewUrl(block: ContentBlock): string {
  if (block.type === 'image') {
    return `data:${block.mimeType};base64,${block.data}`
  }
  return ''
}

function blockLabel(block: ContentBlock): string {
  if (block.type === 'file') {
    return block.metadata.filename || 'PDF 文件'
  }
  return block.metadata.name || '图片'
}
</script>

<template>
  <div v-if="blocks.length" class="content-blocks">
    <div
      v-for="(block, idx) in blocks"
      :key="idx"
      class="content-block"
    >
      <!-- 图片预览 -->
      <template v-if="block.type === 'image'">
        <img
          :src="blockPreviewUrl(block)"
          :alt="blockLabel(block)"
          class="block-preview-img"
        />
      </template>
      <!-- 文件预览（PDF） -->
      <template v-else>
        <div class="block-preview-file">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          <span class="block-filename">{{ blockLabel(block) }}</span>
        </div>
      </template>
      <!-- 删除按钮 -->
      <button
        class="block-remove"
        title="移除"
        @click="emit('remove', idx)"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.content-blocks {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px 0;
}

.content-block {
  position: relative;
  display: flex;
  align-items: center;
  border-radius: 10px;
  border: 1px solid var(--border, #e5e4e7);
  overflow: hidden;
  background: var(--code-bg, #f4f3ec);
}

.block-preview-img {
  width: 56px;
  height: 56px;
  object-fit: cover;
}

.block-preview-file {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  color: var(--text, #6b6375);
}

.block-filename {
  font-size: 13px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.block-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s;
}

.content-block:hover .block-remove {
  opacity: 1;
}

.block-remove:hover {
  background: rgba(220, 38, 38, 0.8);
}
</style>
