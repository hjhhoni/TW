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

  // 流式运行：返回取消函数；onEvent 接收每个 SSE 事件
  runStream: (
    wid: string, inputs: Record<string, any>,
    onEvent: (ev: { node: string; status: string; data?: any }) => void,
  ) => {
    const ctrl = new AbortController()
    ;(async () => {
      const r = await fetch(`${BASE}/workflows/${wid}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inputs, stream: true }),
        signal: ctrl.signal,
      })
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
          try { onEvent(JSON.parse(line.slice(6))) } catch {}
        }
      }
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
}
