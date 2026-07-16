<script setup lang="ts">
import { ref } from 'vue'
import { getFileManager } from './useFileManager'
import FileList from './FileList.vue'
import FileTabs from './FileTabs.vue'
import FilePreview from './FilePreview.vue'
import SplitPane from 'split-pane-v3'

const fm = getFileManager()

// ── 拖拽：FileBrowser 中的 dragSourcePath 仍然由父组件管理，这里透传 ──
const dragSourcePath = ref('')

// ── FilePreview 引用 ──
const leftPreviewRef = ref<InstanceType<typeof FilePreview> | null>(null)
const rightPreviewRef = ref<InstanceType<typeof FilePreview> | null>(null)

defineExpose({ leftPreviewRef, rightPreviewRef })

const emit = defineEmits<{
  rename: [entry: Parameters<typeof fm.selectEntry>[0]]
  delete: [entry: Parameters<typeof fm.selectEntry>[0]]
}>()

// ── 左窗格操作 ──
function onLeftTabActivate() {
  fm.activePane.value = 'left'
}

function onLeftTabSwitch(tabId: string) {
  fm.switchTab(tabId)
  fm.activePane.value = 'left'
}

function onLeftEntryClick(entry: Parameters<typeof fm.selectEntry>[0]) {
  fm.activePane.value = 'left'
  fm.selectEntry(entry)
}

// ── 右窗格操作 ──
function onRightTabActivate() {
  fm.activePane.value = 'right'
}

function onRightTabSwitch(tabId: string) {
  fm.switchTab(tabId)
  fm.activePane.value = 'right'
}

// ── 移动文件 ──
async function onMoveLeft(params: { sourcePath: string; targetDir: string }) {
  await fm.moveEntry(params.sourcePath, params.targetDir)
  dragSourcePath.value = ''
}

async function onMoveRight(params: { sourcePath: string; targetDir: string }) {
  await fm.moveEntry(params.sourcePath, params.targetDir)
  dragSourcePath.value = ''
}

/** 跨窗格移动标签 */
function onMoveTab(tabId: string, targetPane: 'left' | 'right') {
  fm.moveTabToPane(tabId, targetPane)
}
</script>

<template>
  <div class="sv">
    <!-- 双标签栏 -->
    <div class="sv-tabs">
      <FileTabs
        :tabs="fm.leftTabs.value"
        :active-tab-id="fm.leftActiveTabId.value"
        :focused="fm.activePane.value === 'left'"
        pane="left"
        empty-text="无已打开文件"
        @switch-tab="onLeftTabSwitch"
        @close-tab="fm.closeTab"
        @activate="onLeftTabActivate"
        @move-tab="onMoveTab"
      />
      <div class="sv-tabs-sep">│</div>
      <FileTabs
        :tabs="fm.rightTabs.value"
        :active-tab-id="fm.rightActiveTabId.value"
        :focused="fm.activePane.value === 'right'"
        pane="right"
        empty-text="无已打开文件"
        @switch-tab="onRightTabSwitch"
        @close-tab="fm.closeTab"
        @activate="onRightTabActivate"
        @move-tab="onMoveTab"
      />
    </div>

    <!-- 分屏内容 -->
    <div class="sv-content">
      <SplitPane split="vertical" :minPercent="20" :defaultPercent="50" class-name="sv-divider">
        <template #paneL>
          <div
            class="sv-pane"
            :class="{ 'sv-pane--focused': fm.activePane.value === 'left' }"
            @mousedown="fm.activePane.value = 'left'"
          >
            <FileList
              v-if="!fm.leftActiveTab.value"
              :entries="fm.filteredEntries.value"
              :loading="fm.loading.value"
              :search-query="fm.searchQuery.value"
              :search-loading="fm.searchLoading.value"
              :parent-path="fm.parentPath.value"
              :drag-source-path="dragSourcePath"
              :is-file-open="fm.isFileOpen"
              @entry-click="onLeftEntryClick"
              @go-up="fm.goUp()"
              @rename="(e: Parameters<typeof fm.selectEntry>[0]) => emit('rename', e)"
              @delete="(e: Parameters<typeof fm.selectEntry>[0]) => emit('delete', e)"
              @move-entry="onMoveLeft"
              @update:drag-source-path="dragSourcePath = $event"
            />
            <FilePreview
              v-if="fm.leftActiveTab.value"
              ref="leftPreviewRef"
              :key="fm.leftActiveTabId.value"
              :entry="fm.leftActiveTab.value.entry"
              :content="fm.leftActiveTab.value.content"
              :content-type="fm.leftActiveTab.value.contentType"
              :file-url="fm.leftActiveTab.value.fileUrl"
              :loading="fm.leftActiveTab.value.contentLoading"
              @save="(c: string) => fm.leftActiveTab.value && fm.saveFile(fm.leftActiveTab.value.entry.path, c)"
            />
          </div>
        </template>
        <template #paneR>
          <div
            class="sv-pane"
            :class="{ 'sv-pane--focused': fm.activePane.value === 'right' }"
            @mousedown="fm.activePane.value = 'right'"
          >
            <FileList
              v-if="!fm.rightActiveTab.value"
              :entries="fm.filteredEntries.value"
              :loading="fm.loading.value"
              :search-query="fm.searchQuery.value"
              :search-loading="fm.searchLoading.value"
              :parent-path="fm.parentPath.value"
              :drag-source-path="dragSourcePath"
              :is-file-open="fm.isFileOpen"
              @entry-click="(e: Parameters<typeof fm.selectEntry>[0]) => { fm.activePane.value = 'right'; fm.selectEntry(e) }"
              @go-up="fm.goUp()"
              @rename="(e: Parameters<typeof fm.selectEntry>[0]) => emit('rename', e)"
              @delete="(e: Parameters<typeof fm.selectEntry>[0]) => emit('delete', e)"
              @move-entry="onMoveRight"
              @update:drag-source-path="dragSourcePath = $event"
            />
            <FilePreview
              v-if="fm.rightActiveTab.value"
              ref="rightPreviewRef"
              :key="fm.rightActiveTabId.value"
              :entry="fm.rightActiveTab.value.entry"
              :content="fm.rightActiveTab.value.content"
              :content-type="fm.rightActiveTab.value.contentType"
              :file-url="fm.rightActiveTab.value.fileUrl"
              :loading="fm.rightActiveTab.value.contentLoading"
              @save="(c: string) => fm.rightActiveTab.value && fm.saveFile(fm.rightActiveTab.value.entry.path, c)"
            />
          </div>
        </template>
      </SplitPane>
    </div>
  </div>
</template>

<style scoped>
.sv {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.sv-tabs {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  border-bottom: 1px solid var(--border, #e5e4e7);
  background: var(--bg-subtle, #faf8fc);
  overflow: hidden;
}

.sv-tabs-sep {
  font-size: 14px;
  color: var(--border, #e5e4e7);
  user-select: none;
  pointer-events: none;
  padding: 0 2px;
}

.sv-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

/* SplitPane fills the container */
.sv-content :deep(> *) {
  width: 100%;
  height: 100%;
}

.sv-pane {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  outline: none;
}

.sv-pane--focused {
  background: var(--bg, #fff);
}

/* ── split-pane-v3 分隔条 ── */
:deep(.sv-divider) {
  background: var(--border, #e5e4e7) !important;
  transition: background 0.15s;
  width: 4px !important;
  cursor: col-resize;
  position: relative;
}

:deep(.sv-divider:hover),
:deep(.sv-divider:active) {
  background: var(--accent, #aa3bff) !important;
}
</style>
