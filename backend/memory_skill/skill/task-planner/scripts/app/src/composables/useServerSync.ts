import { computed, shallowRef } from 'vue'
import type { PlannerData } from '../types'

export type SyncStatus = 'connecting' | 'synced' | 'local' | 'error'

export interface ServerSync {
  status: { readonly value: SyncStatus }
  online: { readonly value: boolean }
  pull: () => Promise<PlannerData | null>
  push: (data: PlannerData) => Promise<boolean>
  setStatus: (s: SyncStatus) => void
}

/** 与 scripts/serve.js 的 /api/data 通信（scripts/data/task-planner-data.json） */
export function createServerSync(): ServerSync {
  const status = shallowRef<SyncStatus>('connecting')
  const online = computed(() => status.value === 'synced')

  async function pull(): Promise<PlannerData | null> {
    try {
      const r = await fetch('/api/data')
      if (!r.ok) return null
      const data = await r.json()
      if (!data || !Array.isArray(data.tasks)) return null
      return {
        version: 1,
        tasks: data.tasks,
        reviews: data.reviews || {},
        days: data.days || {},
      }
    } catch {
      return null
    }
  }

  async function push(data: PlannerData): Promise<boolean> {
    try {
      const r = await fetch('/api/data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      return r.ok
    } catch {
      return false
    }
  }

  return { status, online, pull, push, setStatus: (s: SyncStatus) => (status.value = s) }
}
