import { computed, watch, type Ref, shallowRef } from 'vue'
import type { Message } from '@/api/chat'
import { getContentText } from '@/api/chat'

/** 导航条目 */
export interface NavItem {
  messageIndex: number
  preview: string
  anchorId: string
}

// ── 模块级共享状态（RightSidebar 可直接读取）──
const _outlineItems = shallowRef<readonly NavItem[]>([])

/** 供外部组件读取大纲数据（如 RightSidebar） */
export function useOutlineItems() {
  return { outlineItems: _outlineItems }
}

/**
 * 对话消息大纲导航（VS Code Outline 风格）
 * 提取所有用户消息，同步到模块级共享状态
 */
export function useContentNav(
  messages: Ref<readonly Message[]>,
  _streamingContent: Ref<string>,
) {
  const navItems = computed<NavItem[]>(() => {
    const items: NavItem[] = []
    const msgs = messages.value
    if (!msgs) return items

    msgs.forEach((msg, idx) => {
      const text = getContentText(msg.content)
      if (msg.role !== 'user' || !text) return
      items.push({
        messageIndex: idx,
        preview: text.length > 40 ? text.slice(0, 37) + '…' : text,
        anchorId: `msg-nav-${idx}`,
      })
    })
    return items
  })

  // 同步到共享状态
  watch(navItems, (items) => { _outlineItems.value = items }, { immediate: true })

  const hasContent = computed(() => navItems.value.length > 0)

  function scrollToNavItem(anchorId: string) {
    const el = document.getElementById(anchorId)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  return { hasContent, navItems, scrollToNavItem }
}
