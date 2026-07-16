import { ref } from 'vue'

const DEFAULT_WIDTH = 480

export function useFilePanelResize(initialWidth?: number) {
  const panelWidth = ref(initialWidth ?? DEFAULT_WIDTH)
  const isResizing = ref(false)
  const rootRef = ref<HTMLElement | null>(null)

  let startX = 0
  let startWidth = 0

  function onResizeStart(e: MouseEvent) {
    e.preventDefault()
    isResizing.value = true
    startX = e.clientX
    startWidth = panelWidth.value
    document.addEventListener('mousemove', onResizeMoveRight)
    document.addEventListener('mouseup', onResizeEnd)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  function onResizeMoveRight(e: MouseEvent) {
    if (!isResizing.value) return
    const delta = e.clientX - startX
    const next = startWidth + delta
    if (next >= 0) panelWidth.value = next
  }

  function onResizeStartLeft(e: MouseEvent) {
    e.preventDefault()
    isResizing.value = true
    startX = e.clientX
    startWidth = panelWidth.value
    document.addEventListener('mousemove', onResizeMoveLeft)
    document.addEventListener('mouseup', onResizeEnd)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }

  function onResizeMoveLeft(e: MouseEvent) {
    if (!isResizing.value) return
    const delta = e.clientX - startX
    const next = startWidth - delta
    if (next >= 0) panelWidth.value = next
  }

  function onResizeEnd() {
    isResizing.value = false
    document.removeEventListener('mousemove', onResizeMoveRight)
    document.removeEventListener('mousemove', onResizeMoveLeft)
    document.removeEventListener('mouseup', onResizeEnd)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  return {
    panelWidth,
    isResizing,
    rootRef,
    onResizeStart,
    onResizeStartLeft,
  }
}
