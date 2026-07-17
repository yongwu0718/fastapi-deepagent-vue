import { ref } from 'vue'
import {
  healthRagEndpointApiRagHealthGet,
  processRagEndpointApiRagProcessPost,
  processUploadEndpointApiRagProcessUploadPost,
  deleteRagEndpointApiRagDeletePost,
  getRagConfigEndpointApiRagConfigGet,
  updateRagConfigEndpointApiRagConfigPut,
  listCollectionsEndpointApiRagCollectionsGet,
  collectionStatsEndpointApiRagCollectionCollectionNameStatsGet,
  collectionDocumentsEndpointApiRagCollectionCollectionNameDocumentsGet,
  deleteCollectionDocsEndpointApiRagCollectionCollectionNameDeleteDocsPost,
  clearCollectionEndpointApiRagCollectionCollectionNameClearPost,
  deleteCollectionEndpointApiRagCollectionCollectionNameDelete,
} from '@/api/client/sdk.gen'
import type {
  RagHealthResponse,
  RagProcessResponse,
  RagDeleteResponse,
  RagFullConfigModel,
  CollectionListResponse,
  CollectionStatsResponse,
  CollectionDocumentsResponse,
  DeleteDocsResponse,
  ClearCollectionResponse,
  DeleteCollectionResponse,
} from '@/api/client/types.gen'
import { toast } from '@/shared/useToast'
import { createLogger } from '@/shared/useLogger'

const log = createLogger('[RAG]')

export function useRagManager() {
  // ── 健康状态 ──
  const health = ref<RagHealthResponse | null>(null)
  const healthLoading = ref(false)
  const healthError = ref('')

  // ── 处理状态 ──
  const processing = ref(false)
  const processResult = ref<RagProcessResponse | null>(null)

  // ── 删除状态 ──
  const deleting = ref(false)
  const deleteResult = ref<RagDeleteResponse | null>(null)

  // ── 配置状态 ──
  const config = ref<RagFullConfigModel | null>(null)
  const configLoading = ref(false)
  const configSaving = ref(false)
  const configLoaded = ref(false)

  // ── 数据库浏览状态 ──
  const collections = ref<CollectionListResponse | null>(null)
  const collectionsLoading = ref(false)
  const selectedCollection = ref('')
  const collectionStats = ref<CollectionStatsResponse | null>(null)
  const statsLoading = ref(false)
  const documents = ref<CollectionDocumentsResponse | null>(null)
  const docsLoading = ref(false)
  const browsePage = ref(1)
  const browsePageSize = ref(20)
  const browseActionLoading = ref(false)

  // ── 操作 ──

  /** 获取向量库健康状态 */
  async function fetchHealth() {
    healthLoading.value = true
    healthError.value = ''
    try {
      const res = await healthRagEndpointApiRagHealthGet()
      health.value = res.data as RagHealthResponse
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      healthError.value = msg
      toast.error('健康检查失败', msg)
    } finally {
      healthLoading.value = false
    }
  }

  /** 提交 .md 文件列表进行 RAG 处理 */
  async function processFiles(files: string[], previewDir?: string | null, previewOnly = false) {
    if (!files.length) {
      toast.warning('请至少提供一个文件路径')
      return
    }
    processing.value = true
    processResult.value = null
    try {
      const res = await processRagEndpointApiRagProcessPost({
        body: { files, preview_dir: previewDir ?? null, preview_only: previewOnly },
      })
      processResult.value = res.data as RagProcessResponse
      log.info('处理完成', processResult.value)
      if (previewOnly) {
        toast.success(
          `预览完成：${processResult.value.success_count}/${processResult.value.total_files} 成功，${processResult.value.total_chunks} 个分块`
        )
      } else {
        toast.success(
          `处理完成：${processResult.value.success_count}/${processResult.value.total_files} 成功，${processResult.value.total_chunks} 个分块入库`
        )
        fetchHealth()
      }
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('处理失败', e)
      toast.error('处理失败', msg)
    } finally {
      processing.value = false
    }
  }

  /** 按 ID 列表删除文档 */
  async function deleteByIds(ids: string[]) {
    if (!ids.length) {
      toast.warning('请至少提供一个文档 ID')
      return
    }
    deleting.value = true
    deleteResult.value = null
    try {
      const res = await deleteRagEndpointApiRagDeletePost({
        body: { ids },
      })
      deleteResult.value = res.data as RagDeleteResponse
      log.info('删除完成', deleteResult.value)
      toast.success(
        deleteResult.value.message ?? `已删除 ${deleteResult.value.deleted_count} 个文档`
      )
      fetchHealth()
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('删除失败', e)
      toast.error('删除失败', msg)
    } finally {
      deleting.value = false
    }
  }

  /** 读取 RAG 配置 */
  async function fetchConfig() {
    configLoading.value = true
    try {
      const res = await getRagConfigEndpointApiRagConfigGet()
      config.value = res.data as RagFullConfigModel
      configLoaded.value = true
      log.info('配置读取成功', config.value)
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('配置读取失败', e)
      toast.error('配置读取失败', msg)
    } finally {
      configLoading.value = false
    }
  }

  /** 上传文件并直接处理（multipart 模式，跳过文件路径） */
  async function processUploadedFiles(files: File[], _previewDir?: string | null, previewOnly = false) {
    if (!files.length) {
      toast.warning('请至少选择一个文件')
      return
    }
    processing.value = true
    processResult.value = null
    try {
      const res = await processUploadEndpointApiRagProcessUploadPost({
        body: { files },
        query: { preview_only: previewOnly },
      })
      processResult.value = res.data as RagProcessResponse
      log.info('上传处理完成', processResult.value)
      if (previewOnly) {
        toast.success(
          `预览完成：${processResult.value.success_count}/${processResult.value.total_files} 成功，${processResult.value.total_chunks} 个分块`
        )
      } else {
        toast.success(
          `处理完成：${processResult.value.success_count}/${processResult.value.total_files} 成功，${processResult.value.total_chunks} 个分块入库`
        )
        fetchHealth()
      }
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('上传处理失败', e)
      toast.error('上传处理失败', msg)
    } finally {
      processing.value = false
    }
  }

  /** 确认入库：已预览分块后，重新处理并保存到向量库 */
  async function confirmSave(pathFiles: string[], uploadFiles: File[], previewDir: string | null) {
    if (uploadFiles.length) {
      await processUploadedFiles(uploadFiles, previewDir, false)
    } else if (pathFiles.length) {
      await processFiles(pathFiles, previewDir, false)
    }
  }

  /** 保存 RAG 配置 */
  async function saveConfig(model: RagFullConfigModel) {
    configSaving.value = true
    try {
      await updateRagConfigEndpointApiRagConfigPut({ body: model })
      config.value = model
      log.info('配置保存成功')
      toast.success('配置已保存并生效')
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('配置保存失败', e)
      toast.error('配置保存失败', msg)
    } finally {
      configSaving.value = false
    }
  }

  // ── 数据库浏览方法 ──

  /** 获取所有集合列表 */
  async function fetchCollections() {
    collectionsLoading.value = true
    try {
      const res = await listCollectionsEndpointApiRagCollectionsGet()
      collections.value = res.data as CollectionListResponse
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('获取集合列表失败', e)
      toast.error('获取集合列表失败', msg)
    } finally {
      collectionsLoading.value = false
    }
  }

  /** 获取集合统计信息 */
  async function fetchCollectionStats(collectionName: string, sampleLimit = 5000) {
    statsLoading.value = true
    collectionStats.value = null
    try {
      const res = await collectionStatsEndpointApiRagCollectionCollectionNameStatsGet({
        path: { collection_name: collectionName },
        query: { sample_limit: sampleLimit },
      })
      collectionStats.value = res.data as CollectionStatsResponse
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('获取统计失败', e)
      toast.error('获取统计失败', msg)
    } finally {
      statsLoading.value = false
    }
  }

  /** 获取集合文档分页列表 */
  async function fetchDocuments(collectionName: string, page = 1, pageSize = 20) {
    docsLoading.value = true
    browsePage.value = page
    browsePageSize.value = pageSize
    try {
      const res = await collectionDocumentsEndpointApiRagCollectionCollectionNameDocumentsGet({
        path: { collection_name: collectionName },
        query: { page, page_size: pageSize },
      })
      documents.value = res.data as CollectionDocumentsResponse
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('获取文档列表失败', e)
      toast.error('获取文档列表失败', msg)
    } finally {
      docsLoading.value = false
    }
  }

  /** 选择集合并加载数据和统计 */
  async function selectCollection(name: string) {
    selectedCollection.value = name
    browsePage.value = 1
    await Promise.all([
      fetchCollectionStats(name),
      fetchDocuments(name, 1, browsePageSize.value),
    ])
  }

  /** 删除集合中指定文档 */
  async function deleteDocsFromCollection(collectionName: string, ids: string[]) {
    if (!ids.length) {
      toast.warning('请至少提供一个文档 ID')
      return
    }
    browseActionLoading.value = true
    try {
      const res = await deleteCollectionDocsEndpointApiRagCollectionCollectionNameDeleteDocsPost({
        path: { collection_name: collectionName },
        body: { ids },
      })
      const data = res.data as DeleteDocsResponse
      toast.success(data.message ?? `已删除 ${data.deleted_count} 个文档`)
      // 刷新数据
      await selectCollection(collectionName)
      fetchHealth()
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('删除文档失败', e)
      toast.error('删除文档失败', msg)
    } finally {
      browseActionLoading.value = false
    }
  }

  /** 清空集合 */
  async function clearCollectionAction(collectionName: string) {
    browseActionLoading.value = true
    try {
      const res = await clearCollectionEndpointApiRagCollectionCollectionNameClearPost({
        path: { collection_name: collectionName },
      })
      const data = res.data as ClearCollectionResponse
      toast.success(data.message ?? `集合已清空`)
      await selectCollection(collectionName)
      fetchHealth()
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('清空集合失败', e)
      toast.error('清空集合失败', msg)
    } finally {
      browseActionLoading.value = false
    }
  }

  /** 删除整个集合 */
  async function deleteCollectionAction(collectionName: string) {
    browseActionLoading.value = true
    try {
      const res = await deleteCollectionEndpointApiRagCollectionCollectionNameDelete({
        path: { collection_name: collectionName },
      })
      const data = res.data as DeleteCollectionResponse
      toast.success(data.message ?? `集合已删除`)
      selectedCollection.value = ''
      documents.value = null
      collectionStats.value = null
      await fetchCollections()
      fetchHealth()
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? String(e)
      log.error('删除集合失败', e)
      toast.error('删除集合失败', msg)
    } finally {
      browseActionLoading.value = false
    }
  }

  return {
    // 状态
    health,
    healthLoading,
    healthError,
    processing,
    processResult,
    deleting,
    deleteResult,
    config,
    configLoading,
    configSaving,
    configLoaded,
    // 方法
    fetchHealth,
    processFiles,
    processUploadedFiles,
    confirmSave,
    deleteByIds,
    fetchConfig,
    saveConfig,
    // 数据库浏览
    collections,
    collectionsLoading,
    selectedCollection,
    collectionStats,
    statsLoading,
    documents,
    docsLoading,
    browsePage,
    browsePageSize,
    browseActionLoading,
    fetchCollections,
    fetchCollectionStats,
    fetchDocuments,
    selectCollection,
    deleteDocsFromCollection,
    clearCollectionAction,
    deleteCollectionAction,
  }
}
