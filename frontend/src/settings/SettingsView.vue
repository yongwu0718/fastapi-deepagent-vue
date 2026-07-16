<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import ConfigEditor from './ConfigEditor.vue'
import ModelConfigForm from './ModelConfigForm.vue'
import FileManager from './FileManager.vue'
import SkillManager from './SkillManager.vue'
import {
  readModelConfigEndpointSettingsModelConfigReadGet,
  writeModelConfigEndpointSettingsModelConfigWritePut,
  rebuildSettingsRebuildPost,
} from '@/api/client/sdk.gen'

const router = useRouter()

type TabKey = 'model' | 'prompts' | 'mcp' | 'memory' | 'skill-files' | 'skill-manage'

const tabs: { key: TabKey | 'rag'; label: string; icon: string }[] = [
  { key: 'model', label: '模型配置', icon: '⚙' },
  { key: 'prompts', label: '系统提示词', icon: '💬' },
  { key: 'mcp', label: 'MCP 服务', icon: '🔌' },
  { key: 'memory', label: '记忆库文件', icon: '📚' },
  { key: 'skill-files', label: '技能库文件', icon: '📁' },
  { key: 'skill-manage', label: '技能开关', icon: '🔘' },
]

const activeTab = ref<TabKey>('model')
const rebuilding = ref(false)
const rebuildMsg = ref('')

function backToChat() {
  router.push({ name: 'chat', params: { threadId: crypto.randomUUID() } })
}

/** 模型配置加载 */
async function loadModelConfig() {
  const res = await readModelConfigEndpointSettingsModelConfigReadGet({ query: { path: 'model' } })
  return (res.data as any)?.content ?? ''
}
async function saveModelConfig(content: string) {
  await writeModelConfigEndpointSettingsModelConfigWritePut({ body: { path: 'model', content } })
}

/** 提示词加载 */
async function loadPrompts() {
  const res = await readModelConfigEndpointSettingsModelConfigReadGet({ query: { path: 'prompt' } })
  return (res.data as any)?.content ?? ''
}
async function savePrompts(content: string) {
  await writeModelConfigEndpointSettingsModelConfigWritePut({ body: { path: 'prompt', content } })
}

/** MCP 配置加载 */
async function loadMcpServer() {
  const res = await readModelConfigEndpointSettingsModelConfigReadGet({ query: { path: 'mcp' } })
  return (res.data as any)?.content ?? ''
}
async function saveMcpServer(content: string) {
  await writeModelConfigEndpointSettingsModelConfigWritePut({ body: { path: 'mcp', content } })
}

async function handleRebuild() {
  rebuilding.value = true
  rebuildMsg.value = ''
  try {
    const res = await rebuildSettingsRebuildPost()
    rebuildMsg.value = (res.data as any)?.message ?? '配置已生效'
  } catch (e: any) {
    rebuildMsg.value = '重建失败: ' + (e?.body?.detail ?? e?.message ?? String(e))
  } finally {
    rebuilding.value = false
  }
}
</script>

<template>
  <div class="settings-page">
    <header class="settings-header">
      <button class="back-btn" @click="backToChat">← 返回聊天</button>
      <h1 class="settings-title">设置管理</h1>
      <div class="rebuild-area">
        <button
          class="rebuild-btn"
          :disabled="rebuilding"
          @click="handleRebuild"
        >
          {{ rebuilding ? '重建中...' : '保存并重建' }}
        </button>
        <span v-if="rebuildMsg" class="rebuild-msg">{{ rebuildMsg }}</span>
      </div>
    </header>

    <div class="settings-body">
      <aside class="sidebar">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="sidebar-item"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <span class="sidebar-icon">{{ tab.icon }}</span>
          <span class="sidebar-label">{{ tab.label }}</span>
        </button>
      </aside>

      <main class="content-area">
        <ModelConfigForm
          v-if="activeTab === 'model'"
          :load="loadModelConfig"
          :save="saveModelConfig"
        />
        <ConfigEditor
          v-else-if="activeTab === 'prompts'"
          :load="loadPrompts"
          :save="savePrompts"
          language="markdown"
          label="system_prompt.txt"
        />
        <ConfigEditor
          v-else-if="activeTab === 'mcp'"
          :load="loadMcpServer"
          :save="saveMcpServer"
          language="json"
          label="mcp_server.json"
        />
        <FileManager
          v-else-if="activeTab === 'memory'"
          type="memory"
          label="记忆库"
        />
        <FileManager
          v-else-if="activeTab === 'skill-files'"
          type="skills"
          label="技能库"
        />
        <SkillManager
          v-else-if="activeTab === 'skill-manage'"
        />
      </main>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  height: 100svh;
  background: #f8f9fa;
}

/* ── 顶部栏 ── */
.settings-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.settings-title {
  flex: 1;
  font-size: 17px;
  font-weight: 600;
  margin: 0;
}

.back-btn {
  padding: 5px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  color: #475569;
}
.back-btn:hover {
  background: #f1f5f9;
}

.rebuild-area {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rebuild-btn {
  padding: 5px 16px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
}
.rebuild-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.rebuild-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.rebuild-msg {
  font-size: 12px;
  color: #059669;
}

/* ── 主体：左侧栏 + 右侧内容 ── */
.settings-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* ── 左侧栏 ── */
.sidebar {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  background: #fff;
  border-right: 1px solid #e2e8f0;
  overflow-y: auto;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 11px 16px;
  border: none;
  background: none;
  font-size: 14px;
  color: #475569;
  cursor: pointer;
  text-align: left;
  border-left: 3px solid transparent;
  transition: all 0.15s;
}
.sidebar-item:hover {
  background: #f1f5f9;
  color: #1e293b;
}
.sidebar-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 500;
  border-left-color: #2563eb;
}

.sidebar-icon {
  font-size: 16px;
  width: 22px;
  text-align: center;
  flex-shrink: 0;
}

.sidebar-label {
  white-space: nowrap;
}

/* ── 右侧内容区 ── */
.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}
</style>
