import { ref, onMounted, onUnmounted } from 'vue'

const MIN_WIDTH = 280
const MAX_INITIAL_WIDTH = 480

export function useSidebarResize() {
  const sidebarWidth = ref(MAX_INITIAL_WIDTH)
  const maxWidth = ref(560)
  const isResizing = ref(false)
  const rootRef = ref<HTMLElement | null>(null)

  let startX = 0
  let startWidth = 0
  let resizeObserver: ResizeObserver | null = null

  onMounted(() => {
    const parent = rootRef.value?.parentElement
    if (!parent) return
    resizeObserver = new ResizeObserver(([entry]) => {
      maxWidth.value = Math.floor(entry.contentRect.width * 0.8)
    })
    resizeObserver.observe(parent)
  })

  onUnmounted(() => {
    resizeObserver?.disconnect()
  })

  function onResizeStart(e: MouseEvent) {
    e.preventDefault()
    isResizing.value = true
    startX = e.clientX
    startWidth = sidebarWidth.value
    document.addEventListener('mousemove', onResizeMove)
    document.addEventListener('mouseup', onResizeEnd)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  function onResizeMove(e: MouseEvent) {
    if (!isResizing.value) return
    const delta = startX - e.clientX
    sidebarWidth.value = Math.min(maxWidth.value, Math.max(MIN_WIDTH, startWidth + delta))
  }

  function onResizeEnd() {
    isResizing.value = false
    document.removeEventListener('mousemove', onResizeMove)
    document.removeEventListener('mouseup', onResizeEnd)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  return {
    sidebarWidth,
    isResizing,
    rootRef,
    onResizeStart,
  }
}
