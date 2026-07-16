/**
 * 文件管理相关类型定义
 * —— 与后端 /api/files/* 端点实际响应结构对应
 */

/** 后端 list_directory 返回的单条 */
export interface RawFileItem {
  name: string
  type: 'dir' | 'file'
  size: number | null
  modified: string
}

/** 后端 list_directory 返回值 */
export interface RawListResponse {
  path: string
  items: RawFileItem[]
}

/** 标准化后的文件/目录条目（前端使用） */
export interface FileEntry {
  name: string
  path: string
  type: 'file' | 'directory'
  size: number
  modified: string
  editable?: boolean
}

/** 后端 read_file_content 返回值 */
export interface RawReadResponse {
  path: string
  content: string
  content_type: string
  size: number
  editable: boolean
}

/** 标准化后的文件内容响应 */
export interface FileReadResponse {
  path: string
  content: string
  type: string
  editable: boolean
  size: number
}

// ── 二进制文件/URL 相关 ──

/** 可通过 <img> 直接预览的图片扩展名 */
const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico', 'avif'])

/** 可通过 <iframe> 直接预览的文档扩展名 */
const IFRAME_EXTENSIONS = new Set(['pdf'])

/** 二进制文件扩展名（不可用文本编辑器打开） */
const BINARY_EXTENSIONS = new Set([
  'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico', 'avif',
  'zip', 'gz', 'tar', 'rar', '7z',
  'mp3', 'wav', 'flac', 'ogg', 'mp4', 'avi', 'mov', 'mkv',
  'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
  'bin', 'exe', 'dll', 'so', 'dylib',
  'ttf', 'otf', 'woff', 'woff2',
  'db', 'sqlite',
])

/** 从文件名提取扩展名（小写、不含点） */
export function getFileExtension(name: string): string {
  const lastDot = name.lastIndexOf('.')
  if (lastDot === -1) return ''
  return name.slice(lastDot + 1).toLowerCase()
}

/** 判断文件是否为二进制（不可文本编辑） */
export function isBinaryFile(name: string): boolean {
  return BINARY_EXTENSIONS.has(getFileExtension(name))
}

/** 判断二进制文件是否可通过 <img> 预览 */
export function isPreviewableImage(name: string): boolean {
  return IMAGE_EXTENSIONS.has(getFileExtension(name))
}

/** 判断二进制文件是否可通过 <iframe> 预览（如 PDF） */
export function isIframePreviewable(name: string): boolean {
  return IFRAME_EXTENSIONS.has(getFileExtension(name))
}

/** 后端通用操作返回值 */
export interface RawOperationResult {
  success: boolean
  message: string
  path: string
}

/** 标准化后的操作结果 */
export interface FileOperationResponse {
  success: boolean
  message: string
  path: string
}

// ── 标准化转换函数 ──

/** 将后端条目转换为前端 FileEntry */
export function normalizeEntry(raw: RawFileItem, parentPath: string = ''): FileEntry {
  return {
    name: raw.name,
    path: parentPath ? `${parentPath}/${raw.name}` : raw.name,
    type: raw.type === 'dir' ? 'directory' : 'file',
    size: raw.size ?? 0,
    modified: raw.modified,
    editable: raw.type === 'file',
  }
}

/** 将后端列表响应转换为前端条目数组 */
export function normalizeListResponse(raw: RawListResponse): { path: string; entries: FileEntry[] } {
  return {
    path: raw.path,
    entries: (raw.items ?? []).map((item) => normalizeEntry(item, raw.path)),
  }
}

/** 将后端读文件响应转换为前端格式 */
export function normalizeReadResponse(raw: RawReadResponse): FileReadResponse {
  return {
    path: raw.path,
    content: raw.content,
    type: raw.content_type,
    editable: raw.editable,
    size: raw.size,
  }
}
