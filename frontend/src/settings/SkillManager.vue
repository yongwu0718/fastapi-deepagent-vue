<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { client } from '@/api/client/client.gen'

interface SkillItem {
  name: string
  enabled: boolean
}

const skills = ref<SkillItem[]>([])
const loading = ref(false)
const saving = ref(false)
const status = ref('')

const enabledCount = computed(() => skills.value.filter((s) => s.enabled).length)
const totalCount = computed(() => skills.value.length)

async function loadSkills() {
  loading.value = true
  status.value = ''
  try {
    const res = await client.get({ url: '/settings/skills' })
    const data = res.data as any
    skills.value = data?.skills ?? []
  } catch (e: any) {
    status.value = '加载失败: ' + (e?.body?.detail ?? String(e))
  } finally {
    loading.value = false
  }
}

function toggleSkill(name: string) {
  const skill = skills.value.find((s) => s.name === name)
  if (skill) {
    skill.enabled = !skill.enabled
  }
}

async function saveSkills() {
  saving.value = true
  status.value = ''
  try {
    const enabled = skills.value.filter((s) => s.enabled).map((s) => s.name)
    const res = await client.put({
      url: '/settings/skills',
      body: { enabled },
      headers: { 'Content-Type': 'application/json' },
    })
    const data = res.data as any
    status.value = `已保存 ✓ (${data?.enabled?.length ?? enabled.length} 项已启用)`
  } catch (e: any) {
    status.value = '保存失败: ' + (e?.body?.detail ?? String(e))
  } finally {
    saving.value = false
  }
}

onMounted(() => loadSkills())
</script>

<template>
  <div class="skill-panel">
    <div class="skill-toolbar">
      <div class="skill-info">
        <span class="skill-label">技能开关管理</span>
        <span class="skill-stats">
          共 {{ totalCount }} 项，已启用 {{ enabledCount }} 项
        </span>
      </div>
      <div class="skill-actions">
        <span v-if="status" class="skill-status">{{ status }}</span>
        <button
          class="save-btn"
          :disabled="saving || loading"
          @click="saveSkills"
        >
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="skill-loading">加载中...</div>
    <div v-else-if="skills.length === 0" class="skill-empty">
      未找到任何技能，请确保 skills 目录中存在包含 SKILL.md 的子目录
    </div>
    <div v-else class="skill-list">
      <div
        v-for="skill in skills"
        :key="skill.name"
        class="skill-item"
        :class="{ enabled: skill.enabled }"
      >
        <div class="skill-name">{{ skill.name }}</div>
        <button
          class="toggle-btn"
          :class="{ active: skill.enabled }"
          @click="toggleSkill(skill.name)"
          :title="skill.enabled ? '禁用' : '启用'"
        >
          <span class="toggle-knob" />
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skill-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.skill-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.skill-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.skill-label {
  font-size: 13px;
  color: #64748b;
  font-family: monospace;
}

.skill-stats {
  font-size: 12px;
  color: #94a3b8;
}

.skill-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.skill-status {
  font-size: 12px;
  color: #059669;
}

.save-btn {
  padding: 5px 16px;
  border: none;
  border-radius: 5px;
  background: #16a34a;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.skill-loading,
.skill-empty {
  text-align: center;
  padding: 40px;
  color: #94a3b8;
  font-size: 14px;
}

.skill-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.skill-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #f1f5f9;
  transition: background 0.1s;
}
.skill-item:hover {
  background: #f8fafc;
}
.skill-item.enabled {
  background: #f0fdf4;
}

.skill-name {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
  font-family: monospace;
}

.toggle-btn {
  position: relative;
  width: 40px;
  height: 22px;
  border: none;
  border-radius: 11px;
  background: #cbd5e1;
  cursor: pointer;
  transition: background 0.2s;
  padding: 0;
}
.toggle-btn.active {
  background: #16a34a;
}

.toggle-knob {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}
.toggle-btn.active .toggle-knob {
  transform: translateX(18px);
}
</style>
