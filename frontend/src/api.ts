// 后端 API 客户端
const BASE = '/api'

async function jget(url: string) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}
async function jpost(url: string, body?: any) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!r.ok) throw new Error(`${url} -> ${r.status} ${await r.text()}`)
  return r.json()
}
async function jput(url: string, body: any) {
  const r = await fetch(url, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}
async function jdel(url: string) {
  const r = await fetch(url, { method: 'DELETE' })
  if (!r.ok) throw new Error(`${url} -> ${r.status}`)
  return r.json()
}

export type NodeType = {
  label: string; color: string; desc: string
  fields: { key: string; label: string; type: string; default: any }[]
}

export const api = {
  nodeTypes: () => jget(`${BASE}/node-types`).then((d: any) => d.types as Record<string, NodeType>),

  listWorkflows: () => jget(`${BASE}/workflows`).then((d: any) => d.workflows),
  getWorkflow: (id: string) => jget(`${BASE}/workflows/${id}`),
  createWorkflow: (name: string) =>
    jpost(`${BASE}/workflows`, { name, description: '', graph: { nodes: [], edges: [] } }),
  updateWorkflow: (id: string, patch: any) => jput(`${BASE}/workflows/${id}`, patch),
  deleteWorkflow: (id: string) => jdel(`${BASE}/workflows/${id}`),

  // 后台运行：立即返回 run_id，真正执行在服务端后台
  startRun: (wid: string, inputs: Record<string, any>) =>
    jpost(`${BASE}/workflows/${wid}/run`, { inputs }).then((d: any) => d.run_id as string),

  cancelRun: (rid: string) => jpost(`${BASE}/runs/${rid}/cancel`, {}),

  // 订阅某次运行的进度（SSE，可随时断开重连，不影响后台运行）。返回取消函数。
  subscribeRunEvents: (
    rid: string,
    onEvent: (ev: { node: string; status: string; data?: any }) => void,
    onDone?: () => void,
  ) => {
    const ctrl = new AbortController()
    ;(async () => {
      try {
        const r = await fetch(`${BASE}/runs/${rid}/events`, { signal: ctrl.signal })
        if (!r.body) return
        const reader = r.body.getReader()
        const dec = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += dec.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop() || ''
          for (const part of parts) {
            const line = part.split('\n').find((l) => l.startsWith('data: '))
            if (!line) continue
            let ev: any
            try { ev = JSON.parse(line.slice(6)) } catch { continue }
            onEvent(ev)
            if (ev.node === '__run__') { onDone?.(); return }
          }
        }
      } catch { /* aborted */ }
    })()
    return () => ctrl.abort()
  },

  listRuns: () => jget(`${BASE}/runs`).then((d: any) => d.runs),
  getRun: (id: string) => jget(`${BASE}/runs/${id}`),

  getProviders: () => jget(`${BASE}/providers`).then((d: any) => d.providers),
  getModels: () => jget(`${BASE}/providers/models`).then((d: any) => d.providers),
  reloadProviders: () => jpost(`${BASE}/providers/reload`),
  getSettings: () => jget(`${BASE}/settings`),
  saveSettings: (settings: any) => jput(`${BASE}/settings`, { settings }),
  testChat: (provider: string, model: string, message: string) =>
    jpost(`${BASE}/providers/chat`, { provider, model, message }),
  testProvider: (cfg: { type: string; base_url: string; api_key: string; model?: string }) =>
    jpost(`${BASE}/providers/test`, cfg),

  listJobs: () => jget(`${BASE}/jobs`).then((d: any) => d.jobs),
  createJob: (job: any) => jpost(`${BASE}/jobs`, job),
  toggleJob: (id: string) => jpost(`${BASE}/jobs/${id}/toggle`, {}),
  deleteJob: (id: string) => jdel(`${BASE}/jobs/${id}`),

  // 工作流导入/复制（导出直接用 getWorkflow 下载 JSON）
  importWorkflow: (doc: any) => jpost(`${BASE}/workflows/import`, doc),
  duplicateWorkflow: (id: string) => jpost(`${BASE}/workflows/${id}/duplicate`, {}),

  // 资产库
  listAssets: () => jget(`${BASE}/assets`).then((d: any) => d.assets),
  getAsset: (id: string) => jget(`${BASE}/assets/${id}`),
  deleteAsset: (id: string) => jdel(`${BASE}/assets/${id}`),
}
