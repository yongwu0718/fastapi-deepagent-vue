import { ref } from 'vue'
import type { useRagManager } from './useRagManager'

export function useRagConfig(rag: ReturnType<typeof useRagManager>) {
  const configForm = ref({
    embedding: { model: '', base_url: '' },
    rag: {
      splitter: {
        headers: ['#', '##', '###'],
        return_each_line: false,
        strip_headers: false,
        enable_char_split: true,
        chunk_size: 1000,
        chunk_overlap: 200,
      },
      hnsw: {
        space: 'cosine',
        ef_construction: 200,
        max_neighbors: 16,
        ef_search: 100,
        num_threads: 4,
        batch_size: 100,
        sync_threshold: 1000,
        resize_factor: 1.2,
      },
      processing: {
        preview_output_dir: '',
        enable_interactive: false,
      },
      collection: {
        name: '',
        persist_directory: '',
      },
    },
  })

  const configSaveMsg = ref('')

  function applyConfigToForm(raw: any) {
    const e = raw?.embedding ?? {}
    const s = raw?.rag?.splitter ?? {}
    const h = raw?.rag?.hnsw ?? {}
    const p = raw?.rag?.processing ?? {}
    const c = raw?.rag?.collection ?? {}
    configForm.value = {
      embedding: { model: e.model ?? '', base_url: e.base_url ?? '' },
      rag: {
        splitter: {
          headers: s.headers ?? ['#', '##', '###'],
          return_each_line: s.return_each_line ?? false,
          strip_headers: s.strip_headers ?? false,
          enable_char_split: s.enable_char_split ?? true,
          chunk_size: s.chunk_size ?? 1000,
          chunk_overlap: s.chunk_overlap ?? 200,
        },
        hnsw: {
          space: h.space ?? 'cosine',
          ef_construction: h.ef_construction ?? 200,
          max_neighbors: h.max_neighbors ?? 16,
          ef_search: h.ef_search ?? 100,
          num_threads: h.num_threads ?? 4,
          batch_size: h.batch_size ?? 100,
          sync_threshold: h.sync_threshold ?? 1000,
          resize_factor: h.resize_factor ?? 1.2,
        },
        processing: {
          preview_output_dir: p.preview_output_dir ?? '',
          enable_interactive: p.enable_interactive ?? false,
        },
        collection: {
          name: c.name ?? '',
          persist_directory: c.persist_directory ?? '',
        },
      },
    }
  }

  function buildConfigPayload(): any {
    return {
      embedding: {
        model: configForm.value.embedding.model || undefined,
        base_url: configForm.value.embedding.base_url || undefined,
      },
      rag: {
        splitter: { ...configForm.value.rag.splitter },
        hnsw: {
          ...configForm.value.rag.hnsw,
          resize_factor: Number(configForm.value.rag.hnsw.resize_factor),
        },
        processing: {
          preview_output_dir: configForm.value.rag.processing.preview_output_dir || undefined,
          enable_interactive: configForm.value.rag.processing.enable_interactive,
        },
        collection: {
          name: configForm.value.rag.collection.name || undefined,
          persist_directory: configForm.value.rag.collection.persist_directory || undefined,
        },
      },
    }
  }

  async function handleLoadConfig() {
    await rag.fetchConfig()
    if (rag.config.value) {
      applyConfigToForm(rag.config.value)
      configSaveMsg.value = ''
    }
  }

  async function handleSaveConfig() {
    configSaveMsg.value = ''
    const payload = buildConfigPayload()
    await rag.saveConfig(payload)
    if (rag.config.value) {
      configSaveMsg.value = '配置已保存，运行时已自动重载'
    }
  }

  return {
    configForm,
    configSaveMsg,
    applyConfigToForm,
    buildConfigPayload,
    handleLoadConfig,
    handleSaveConfig,
  }
}
