<script setup lang="ts">
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useRagManager } from './composables/useRagManager'
import { useRagTabs } from './composables/useRagTabs'
import { useRagConfig } from './composables/useRagConfig'
import { useRagProcess } from './composables/useRagProcess'
import { useRagBrowse } from './composables/useRagBrowse'
import { useRagHealth } from './composables/useRagHealth'
import { useRagUpload } from './composables/useRagUpload'
import HealthPanel from './components/HealthPanel.vue'
import ProcessTab from './components/ProcessTab.vue'
import ConfigTab from './components/ConfigTab.vue'
import BrowseTab from './components/BrowseTab.vue'

const router = useRouter()
const rag = useRagManager()

// ── 模块（upload → process 有依赖顺序） ──
const {
  uploadItems, dragOverDrop,
  handleFileInput, removeUploadItem,
  onDropZoneEnter, onDropZoneLeave, onDropZoneOver, onDropZone,
  clearUploadItems,
} = useRagUpload()

const {
  processFilesInput, previewDir, parsedFiles,
  isPreviewMode, expandedChunks, toggleChunks,
  handleProcess, handleConfirmSave, clearProcessForm,
} = useRagProcess(rag, uploadItems)

const {
  configForm, configSaveMsg,
  handleLoadConfig, handleSaveConfig,
} = useRagConfig(rag)

const { activeTab, switchTab, registerConfigLoader } = useRagTabs(rag)
registerConfigLoader(handleLoadConfig)

const {
  deleteConfirmDocId, showClearConfirm, showDeleteColConfirm,
  handleBrowseCollectionChange, handleBrowsePageChange,
  handleDeleteSingleDoc, confirmDeleteSingleDoc, cancelDeleteSingleDoc,
  handleClearCollection, confirmClearCollection,
  handleDeleteCollection, confirmDeleteCollection,
} = useRagBrowse(rag)

const { autoRefresh, stopAutoRefresh, toggleAutoRefresh } = useRagHealth(rag)

// ── 上传/路径互斥 ──
watch(processFilesInput, (val) => { if (val.trim()) uploadItems.value = [] })
watch(uploadItems, (items) => { if (items.length) processFilesInput.value = '' })

// ── 导航 ──
function backToChat() { stopAutoRefresh(); router.push({ name: 'chat', params: { threadId: crypto.randomUUID() } }) }
function goToSettings() { stopAutoRefresh(); router.push({ name: 'settings' }) }
</script>

<template>
  <div class="rag-page">
    <header class="rag-header">
      <button class="back-btn" @click="backToChat">← 返回聊天</button>
      <h1 class="rag-title">向量库管理 (RAG)</h1>
      <button class="settings-link" @click="goToSettings">设置管理</button>
    </header>

    <div class="rag-body">
      <HealthPanel
        :rag="rag"
        :auto-refresh="autoRefresh"
        @toggle-auto-refresh="toggleAutoRefresh"
        @refresh="rag.fetchHealth()"
      />

      <main class="operation-area">
        <nav class="tab-bar">
          <button class="tab-btn" :class="{ active: activeTab === 'process' }" @click="switchTab('process')">文件处理</button>
          <button class="tab-btn" :class="{ active: activeTab === 'config' }" @click="switchTab('config')">配置管理</button>
          <button class="tab-btn" :class="{ active: activeTab === 'browse' }" @click="switchTab('browse')">数据库浏览</button>
          <span class="tab-spacer" />
          <template v-if="activeTab === 'config'">
            <button class="tab-action-btn" :disabled="rag.configLoading.value || rag.configSaving.value" @click="handleLoadConfig">{{ rag.configLoading.value ? '读取中...' : '读取' }}</button>
            <button class="tab-action-btn" :disabled="rag.configSaving.value || rag.configLoading.value" @click="handleSaveConfig">{{ rag.configSaving.value ? '保存中...' : '保存' }}</button>
          </template>
        </nav>

        <ProcessTab
          v-if="activeTab === 'process'"
          :rag="rag"
          :process-files-input="processFilesInput"
          :preview-dir="previewDir"
          :parsed-files="parsedFiles"
          :is-preview-mode="isPreviewMode"
          :expanded-chunks="expandedChunks"
          :upload-items="uploadItems"
          :drag-over-drop="dragOverDrop"
          @update:process-files-input="processFilesInput = $event"
          @update:preview-dir="previewDir = $event"
          @process="handleProcess()"
          @confirm-save="handleConfirmSave()"
          @clear="clearProcessForm()"
          @toggle-chunks="toggleChunks"
          @file-input="handleFileInput"
          @remove-upload="removeUploadItem"
          @clear-upload="clearUploadItems"
          @drop-zone-enter="onDropZoneEnter"
          @drop-zone-leave="onDropZoneLeave"
          @drop-zone-over="onDropZoneOver"
          @drop-zone="onDropZone"
        />

        <ConfigTab
          v-if="activeTab === 'config'"
          :rag="rag"
          :config-form="configForm"
          :config-save-msg="configSaveMsg"
        />

        <BrowseTab
          v-if="activeTab === 'browse'"
          :rag="rag"
          :delete-confirm-doc-id="deleteConfirmDocId"
          :show-clear-confirm="showClearConfirm"
          :show-delete-col-confirm="showDeleteColConfirm"
          @select-collection="handleBrowseCollectionChange"
          @refresh-collections="rag.fetchCollections()"
          @page-change="handleBrowsePageChange"
          @delete-single-doc="handleDeleteSingleDoc"
          @confirm-delete-single-doc="confirmDeleteSingleDoc()"
          @cancel-delete-single-doc="cancelDeleteSingleDoc()"
          @clear-collection="handleClearCollection()"
          @confirm-clear="confirmClearCollection()"
          @cancel-clear="showClearConfirm = false"
          @delete-collection="handleDeleteCollection()"
          @confirm-delete-col="confirmDeleteCollection()"
          @cancel-delete-col="showDeleteColConfirm = false"
        />
      </main>
    </div>
  </div>
</template>

<style scoped>
/* ── 页面布局 ── */
.rag-page { display: flex; flex-direction: column; height: 100svh; background: #f8f9fa; }
.rag-header { display: flex; align-items: center; gap: 16px; padding: 10px 20px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; }
.rag-title { flex: 1; font-size: 17px; font-weight: 600; margin: 0; }
.back-btn, .settings-link {
  padding: 5px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; color: #475569;
}
.back-btn:hover, .settings-link:hover { background: #f1f5f9; }
.rag-body { display: flex; flex: 1; min-height: 0; }

/* ── 操作区 ── */
.operation-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; padding: 20px; }
.tab-bar { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; }
.tab-btn {
  padding: 8px 20px; border: none; background: none; font-size: 14px; color: #64748b;
  cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all .15s;
}
.tab-btn:hover { color: #334155; }
.tab-btn.active { color: #2563eb; font-weight: 600; border-bottom-color: #2563eb; }
.tab-spacer { flex: 1; }
.tab-action-btn {
  padding: 3px 12px; border: 1px solid #cbd5e1; border-radius: 4px; background: #fff;
  font-size: 12px; color: #475569; cursor: pointer; white-space: nowrap; margin-bottom: -2px; transition: all .15s;
}
.tab-action-btn:hover:not(:disabled) { background: #f1f5f9; color: #2563eb; }
.tab-action-btn:disabled { opacity: .5; cursor: not-allowed; }
</style>
