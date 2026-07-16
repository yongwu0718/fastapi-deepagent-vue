<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ActionRequest, ReviewConfig, HITLDecision, HITLResponse } from '@/api/chat'

const props = defineProps<{
  actionRequests: ActionRequest[]
  reviewConfigs: ReviewConfig[]
  loading: boolean
}>()

const emit = defineEmits<{
  respond: [response: HITLResponse]
  cancel: []
}>()

interface DecisionState {
  type: 'approve' | 'reject' | 'edit' | null
  message: string
  editedArgs: string // JSON 编辑字符串
}

const decisionsState = ref<DecisionState[]>([])

/** 初始化/重置每个 action 的决策状态 */
function initDecisions() {
  decisionsState.value = props.actionRequests.map(() => ({
    type: null,
    message: '',
    editedArgs: '',
  }))
}

watch(() => props.actionRequests.length, initDecisions, { immediate: true })

/** 某个 action 是否已做决定 */
const allDecided = computed(() =>
  decisionsState.value.every((d) => d.type !== null),
)

/** 获取某 action 允许的决策 */
function allowedDecisions(index: number): string[] {
  const config = props.reviewConfigs.find(
    (c) => c.action_name === props.actionRequests[index]?.name,
  )
  return config?.allowed_decisions ?? ['approve', 'reject']
}

/** 设置决策类型 */
function setDecision(index: number, type: DecisionState['type']) {
  decisionsState.value[index] = {
    type,
    message: '',
    editedArgs: props.actionRequests[index]
      ? JSON.stringify(props.actionRequests[index].args, null, 2)
      : '',
  }
}

/** 提交所有决策 */
function submitAll() {
  const decisions: HITLDecision[] = decisionsState.value.map((ds, i) => {
    const base = { type: ds.type! } as HITLDecision
    if (ds.type === 'reject' && ds.message) {
      base.message = ds.message
    }
    if (ds.type === 'edit') {
      try {
        base.edited_action = {
          name: props.actionRequests[i].name,
          args: JSON.parse(ds.editedArgs),
        }
      } catch {
        base.edited_action = {
          name: props.actionRequests[i].name,
          args: props.actionRequests[i].args,
        }
      }
    }
    return base
  })
  emit('respond', { decisions })
}

/** 快捷：全部批准 */
function approveAll() {
  decisionsState.value = props.actionRequests.map(() => ({
    type: 'approve' as const,
    message: '',
    editedArgs: '',
  }))
}

/** 格式化参数展示 */
function formatArgs(args: Record<string, unknown>): string {
  const entries = Object.entries(args)
  if (entries.length === 0) return '无参数'
  return entries
    .map(([k, v]) => {
      const val = typeof v === 'string' ? v : JSON.stringify(v)
      return `\`${k}\`: ${val.length > 60 ? val.slice(0, 60) + '…' : val}`
    })
    .join('\n')
}
</script>

<template>
  <div class="approval-overlay">
    <div class="approval-card">
      <div class="approval-header">
        <span class="approval-title">🔔 操作需要审批</span>
        <span class="approval-subtitle">{{ actionRequests.length }} 个待处理动作</span>
      </div>

      <div class="approval-body">
        <div
          v-for="(action, i) in actionRequests"
          :key="i"
          class="action-item"
          :class="{ 'action-item--decided': decisionsState[i]?.type }"
        >
          <!-- 动作信息 -->
          <div class="action-info">
            <div class="action-name">
              <span class="action-icon">⚡</span>
              <code>{{ action.name }}</code>
            </div>
            <div v-if="action.description" class="action-desc">
              {{ action.description }}
            </div>
            <pre class="action-args">{{ formatArgs(action.args) }}</pre>
          </div>

          <!-- 决策按钮 -->
          <div class="action-decisions">
            <span class="decision-label">决策：</span>
            <button
              v-for="opt in allowedDecisions(i)"
              :key="opt"
              class="decision-btn"
              :class="{
                'decision-btn--active': decisionsState[i]?.type === opt,
                'decision-btn--approve': opt === 'approve',
                'decision-btn--reject': opt === 'reject',
                'decision-btn--edit': opt === 'edit',
              }"
              @click="setDecision(i, opt as 'approve' | 'reject' | 'edit')"
            >
              {{ opt === 'approve' ? '✅ 批准' : opt === 'reject' ? '❌ 拒绝' : '✏️ 编辑' }}
            </button>
          </div>

          <!-- 拒绝原因 -->
          <div v-if="decisionsState[i]?.type === 'reject'" class="action-extra">
            <label class="extra-label">拒绝原因（可选）：</label>
            <input
              v-model="decisionsState[i].message"
              type="text"
              class="extra-input"
              placeholder="输入拒绝原因…"
            />
          </div>

          <!-- 编辑参数 -->
          <div v-if="decisionsState[i]?.type === 'edit'" class="action-extra">
            <label class="extra-label">编辑参数（JSON）：</label>
            <textarea
              v-model="decisionsState[i].editedArgs"
              class="extra-textarea"
              rows="4"
            />
          </div>
        </div>
      </div>

      <div class="approval-footer">
        <button class="footer-btn footer-btn--cancel" @click="emit('cancel')">
          取消
        </button>
        <button class="footer-btn footer-btn--all" @click="approveAll">
          全部批准
        </button>
        <button
          class="footer-btn footer-btn--submit"
          :disabled="!allDecided || loading"
          @click="submitAll"
        >
          {{ loading ? '提交中…' : '提交决策' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.approval-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(4px);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.approval-card {
  width: 480px;
  max-width: 90vw;
  max-height: 70vh;
  background: var(--bg, #fff);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.25s ease;
}

@keyframes slideUp {
  from { transform: translateY(24px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.approval-header {
  padding: 18px 24px 14px;
  border-bottom: 1px solid var(--border, #e5e4e7);
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.approval-title {
  font: 600 17px/1.3 var(--heading, system-ui);
  color: var(--text-h, #08060d);
}

.approval-subtitle {
  font-size: 12px;
  color: var(--text, #6b6375);
}

.approval-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-item {
  border: 1px solid var(--border, #e5e4e7);
  border-radius: 12px;
  padding: 14px;
  transition: border-color 0.2s;
}

.action-item--decided {
  border-color: var(--accent, #aa3bff);
  background: rgba(170, 59, 255, 0.03);
}

.action-info {
  margin-bottom: 12px;
}

.action-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-h, #08060d);
  margin-bottom: 4px;
}

.action-name code {
  background: var(--code-bg, #f4f3ec);
  padding: 1px 8px;
  border-radius: 5px;
  font-size: 13px;
}

.action-icon {
  font-size: 16px;
}

.action-desc {
  font-size: 12px;
  color: var(--text, #6b6375);
  margin-bottom: 6px;
  line-height: 1.4;
}

.action-args {
  background: var(--code-bg, #f4f3ec);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  color: var(--text-h, #08060d);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

.action-decisions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.decision-label {
  font-size: 12px;
  color: var(--text, #6b6375);
  opacity: 0.7;
}

.decision-btn {
  padding: 4px 12px;
  border-radius: 8px;
  border: 1.5px solid var(--border, #e5e4e7);
  background: var(--bg, #fff);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--text-h, #08060d);
}

.decision-btn:hover {
  background: var(--code-bg, #f4f3ec);
  border-color: var(--text, #6b6375);
}

.decision-btn--active.decision-btn--approve {
  background: rgba(34, 197, 94, 0.12);
  border-color: #22c55e;
  color: #15803d;
}

.decision-btn--active.decision-btn--reject {
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
  color: #dc2626;
}

.decision-btn--active.decision-btn--edit {
  background: rgba(59, 130, 246, 0.1);
  border-color: #3b82f6;
  color: #2563eb;
}

.action-extra {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.extra-label {
  font-size: 11px;
  color: var(--text, #6b6375);
  font-weight: 500;
}

.extra-input {
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border, #e5e4e7);
  font-size: 13px;
  background: var(--bg, #fff);
  color: var(--text-h, #08060d);
  outline: none;
  transition: border-color 0.15s;
}

.extra-input:focus {
  border-color: var(--accent, #aa3bff);
}

.extra-textarea {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border, #e5e4e7);
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}

.extra-textarea:focus {
  border-color: var(--accent, #aa3bff);
}

.approval-footer {
  padding: 14px 24px;
  border-top: 1px solid var(--border, #e5e4e7);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.footer-btn {
  padding: 8px 18px;
  border-radius: 10px;
  border: 1px solid var(--border, #e5e4e7);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.footer-btn--cancel {
  background: var(--bg, #fff);
  color: var(--text, #6b6375);
}

.footer-btn--cancel:hover {
  background: var(--code-bg, #f4f3ec);
}

.footer-btn--all {
  background: var(--code-bg, #f4f3ec);
  color: var(--text-h, #08060d);
}

.footer-btn--all:hover {
  background: var(--border, #e5e4e7);
}

.footer-btn--submit {
  background: var(--accent, #aa3bff);
  color: #fff;
  border-color: var(--accent, #aa3bff);
}

.footer-btn--submit:hover:not(:disabled) {
  opacity: 0.9;
}

.footer-btn--submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>