<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useFileUpload, type ContentBlock } from '@/upload/useFileUpload'
import ContentBlocksPreview from '@/upload/ContentBlocksPreview.vue'

const props = defineProps<{
  loading: boolean
}>()

const emit = defineEmits<{
  send: [content: string, contentBlocks?: ContentBlock[], rawFiles?: File[], rubric?: string]
  cancel: []
}>()

const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const dragPathOver = ref(false)

// ── Loop 模式：rubric 完成条件 ──
const showRubric = ref(false)
const rubricText = ref('')

const {
  contentBlocks,
  rawFiles,
  dragOver,
  handleFileUpload,
  handlePaste,
  removeBlock,
  resetBlocks,
} = useFileUpload()

const canSend = computed(
  () => (inputText.value.trim().length > 0 || contentBlocks.value.length > 0) && !props.loading,
)

function autoResize() {
  nextTick(() => {
    const el = textareaRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  })
}

function handleSubmit() {
  const trimmed = inputText.value.trim()
  const hasBlocks = contentBlocks.value.length > 0
  if ((!trimmed && !hasBlocks) || props.loading) return

  const rubric = rubricText.value.trim() || undefined
  emit('send', trimmed, hasBlocks ? [...contentBlocks.value] : undefined, hasBlocks ? [...rawFiles.value] : undefined, rubric)
  inputText.value = ''
  rubricText.value = ''
  showRubric.value = false
  resetBlocks()
  nextTick(autoResize)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}

function onPaste(e: ClipboardEvent) {
  handlePaste(e)
}

function onFileInputChange(e: Event) {
  handleFileUpload(e)
}

// ── 拖入文件路径（从右侧文件浏览器拖拽） ──
function onPathDragOver(e: DragEvent) {
  if (e.dataTransfer?.types.includes('text/plain') && !e.dataTransfer.types.includes('Files')) {
    e.preventDefault()
    e.dataTransfer!.dropEffect = 'copy'
    dragPathOver.value = true
  }
}

function onPathDragLeave() {
  dragPathOver.value = false
}

function onPathDrop(e: DragEvent) {
  dragPathOver.value = false
  const path = e.dataTransfer?.getData('text/plain')
  if (!path) return
  e.preventDefault()
  // 在光标处插入路径
  const el = textareaRef.value
  if (el) {
    el.focus()
    const start = el.selectionStart
    const end = el.selectionEnd
    inputText.value =
      inputText.value.slice(0, start) + path + inputText.value.slice(end)
    nextTick(() => {
      el.selectionStart = el.selectionEnd = start + path.length
    })
  }
}
</script>

<template>
  <div
    class="chat-input"
    @dragover="onPathDragOver"
    @dragleave="onPathDragLeave"
    @drop="onPathDrop"
  >
    <div
      :class="[
        'input-card',
        { 'input-card--drag': dragOver, 'input-card--path-drag': dragPathOver },
      ]"
    >
      <form class="input-form" @submit.prevent="handleSubmit">
        <!-- 文件预览 -->
        <ContentBlocksPreview
          :blocks="contentBlocks"
          @remove="removeBlock"
        />

        <!-- 输入框 -->
        <textarea
          ref="textareaRef"
          v-model="inputText"
          class="input-textarea"
          :placeholder="loading ? 'AI 正在回复中.' : '输入你的问题.'"
          :disabled="loading"
          rows="1"
          @keydown="handleKeydown"
          @input="autoResize"
          @paste="onPaste"
        />

        <!-- Loop 模式：rubric 完成条件 -->
        <div v-if="showRubric" class="rubric-panel">
          <textarea
            v-model="rubricText"
            class="rubric-textarea"
            placeholder="完成条件（rubric）。Agent 自然停止后由独立评估器判断是否满足，未满足自动循环改进，最多 10 轮。例：回答必须包含可运行代码、时间复杂度说明和使用示例"
            rows="3"
            :disabled="loading"
          />
        </div>

        <!-- 拖拽遮罩 -->
        <div v-if="dragOver" class="drag-overlay">
          <span>释放以上传文件</span>
        </div>

        <!-- 底部操作栏 -->
        <div class="input-actions">
          <div class="actions-left">
            <!-- 文件上传 -->
            <label class="upload-btn" title="上传图片或 PDF">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              <span class="upload-text">上传图片或 PDF</span>
              <input
                type="file"
                class="file-input-hidden"
                multiple
                accept="image/jpeg,image/png,image/gif,image/webp,application/pdf,.docx"
                @change="onFileInputChange"
              />
            </label>

            <!-- Loop 模式开关 -->
            <button
              type="button"
              class="rubric-btn"
              :class="{ active: showRubric }"
              title="Loop 模式：设定完成条件，Agent 自动循环评估直到满足"
              @click="showRubric = !showRubric"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="17 1 21 5 17 9" />
                <path d="M3 11V9a4 4 0 0 1 4-4h14" />
                <polyline points="7 23 3 19 7 15" />
                <path d="M21 13v2a4 4 0 0 1-4 4H3" />
              </svg>
              <span class="rubric-btn-text">Loop</span>
            </button>
          </div>

          <div class="actions-right">
            <!-- 停止按钮（loading 时） -->
            <button
              v-if="loading"
              type="button"
              class="btn-cancel"
              @click="emit('cancel')"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="spinner-icon">
                <circle cx="12" cy="12" r="10" stroke-width="2" stroke-dasharray="31.4 31.4" />
              </svg>
              <span>停止</span>
            </button>

            <!-- 发送按钮 -->
            <button
              v-else
              type="submit"
              class="btn-send"
              :disabled="!canSend"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
              <span>发送</span>
            </button>
          </div>
        </div>
      </form>
    </div>
    <p class="input-hint">AI 助手可能会产生错误信息，请核实重要内容。</p>
  </div>
</template>

<style scoped>
.chat-input {
  padding: 0 16px 16px;
  max-width: var(--chat-max-width, 48rem);
  margin: 0 auto;
  width: 100%;
}

.input-card {
  position: relative;
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 16px;
  background: var(--bg, #fff);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s, box-shadow 0.2s;
  overflow: hidden;
}

.input-card:focus-within {
  border-color: var(--accent, #aa3bff);
  box-shadow: 0 2px 16px rgba(170, 59, 255, 0.08);
}

.input-card--drag {
  border-color: var(--accent, #aa3bff);
  border-style: dashed;
  border-width: 2px;
}

.input-card--path-drag {
  border-color: #10b981;
  box-shadow: 0 2px 16px rgba(16, 185, 129, 0.12);
}

.input-form {
  display: flex;
  flex-direction: column;
}

.input-textarea {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font: inherit;
  font-size: 15px;
  line-height: 1.6;
  resize: none;
  padding: 14px 16px 0;
  color: var(--text-h, #08060d);
  min-height: 48px;
  max-height: 200px;
  field-sizing: content;
}

.input-textarea::placeholder {
  color: var(--text, #6b6375);
  opacity: 0.5;
}

.input-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ── 拖拽遮罩 ── */
.drag-overlay {
  position: absolute;
  inset: 0;
  background: rgba(170, 59, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 600;
  color: var(--accent, #aa3bff);
  pointer-events: none;
  z-index: 2;
}

/* ── 底部操作栏 ── */
.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 12px;
}

.actions-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

/* ── 文件上传按钮 ── */
.upload-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text, #6b6375);
  transition: background 0.15s, color 0.15s;
}

.upload-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--accent, #aa3bff);
}

.upload-text {
  font-size: 12px;
}

.file-input-hidden {
  display: none;
}

/* ── Loop 模式按钮 ── */
.rubric-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text, #6b6375);
  background: none;
  border: none;
  transition: background 0.15s, color 0.15s;
}

.rubric-btn:hover {
  background: var(--code-bg, #f4f3ec);
  color: var(--accent, #aa3bff);
}

.rubric-btn.active {
  color: var(--accent, #aa3bff);
  background: rgba(170, 59, 255, 0.08);
}

.rubric-btn-text {
  font-size: 12px;
}

/* ── rubric 输入面板 ── */
.rubric-panel {
  padding: 0 16px;
  border-top: 1px dashed var(--border, #e5e4e7);
}

.rubric-textarea {
  width: 100%;
  border: none;
  outline: none;
  background: rgba(170, 59, 255, 0.03);
  font: inherit;
  font-size: 13px;
  line-height: 1.5;
  resize: none;
  padding: 10px 0;
  color: var(--text-h, #08060d);
  min-height: 60px;
}

.rubric-textarea::placeholder {
  color: var(--text, #6b6375);
  opacity: 0.5;
}

.rubric-textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ── 按钮 ── */
.btn-send,
.btn-cancel {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.2s, background 0.2s, transform 0.15s;
}

.btn-send {
  background: var(--accent, #aa3bff);
  color: #fff;
}

.btn-send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn-send:not(:disabled):hover {
  opacity: 0.88;
}

.btn-send:not(:disabled):active {
  transform: scale(0.97);
}

.btn-cancel {
  background: var(--border, #e5e4e7);
  color: var(--text-h, #08060d);
}

.btn-cancel:hover {
  background: #d4d3d8;
}

.btn-cancel:active {
  transform: scale(0.97);
}

/* ── 旋转动画 ── */
.spinner-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── 底部提示 ── */
.input-hint {
  font-size: 11px;
  color: var(--text, #6b6375);
  opacity: 0.5;
  text-align: center;
  margin: 8px 0 0;
}
</style>