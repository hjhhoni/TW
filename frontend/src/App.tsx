import { useEffect, useState } from 'react'
import { api, type NodeType } from './api'
import { FlowEditor } from './FlowEditor'
import { Runs } from './Runs'
import { Jobs } from './Jobs'
import { Settings } from './Settings'
import { Assets } from './Assets'
import { ImportModal } from './ImportModal'
import { RunPanel, type ActiveRun } from './RunPanel'

type View = 'editor' | 'runs' | 'assets' | 'jobs' | 'settings'

export default function App() {
  const [view, setView] = useState<View>('editor')
  const [workflows, setWorkflows] = useState<any[]>([])
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [nodeTypes, setNodeTypes] = useState<Record<string, NodeType>>({})
  const [providers, setProviders] = useState<any[]>([])
  const [models, setModels] = useState<any[]>([])
  const [dirty, setDirty] = useState(false)
  const [showImport, setShowImport] = useState(false)

  // 后台运行
  const [activeRuns, setActiveRuns] = useState<ActiveRun[]>([])
  const [toast, setToast] = useState<{ msg: string; kind: 'success' | 'error' } | null>(null)
  const [viewRun, setViewRun] = useState<ActiveRun | null>(null)

  const refreshWorkflows = () => api.listWorkflows().then((ws) => {
    setWorkflows(ws)
    if (ws.length && !currentId) setCurrentId(ws[0].id)
    else if (currentId && !ws.find((w: any) => w.id === currentId)) setCurrentId(ws[0]?.id || null)
  })

  const refreshAll = () => {
    api.nodeTypes().then(setNodeTypes)
    api.getProviders().then(setProviders)
    api.getModels().then((m) => setModels(m))
    refreshWorkflows()
  }
  useEffect(() => { refreshAll() }, []) // eslint-disable-line

  // 重连：刷新前正在后台跑的任务，重新订阅进度（刷新页面不丢运行）
  useEffect(() => {
    api.listRuns().then((runs) => {
      runs.filter((r: any) => r.status === 'running').forEach(async (r: any) => {
        let nodeLabels: Record<string, string> = {}
        try {
          const wf = await api.getWorkflow(r.workflow_id)
          nodeLabels = Object.fromEntries((wf.graph?.nodes || []).map((n: any) => [n.id, n.label || n.id]))
        } catch {}
        const entry: ActiveRun = {
          runId: r.id, workflowId: r.workflow_id, workflowName: r.workflow_name,
          status: 'running', nodeStatuses: {}, nodeLabels,
          startedAt: (r.started_at < 1e12 ? r.started_at * 1000 : r.started_at),
        }
        setActiveRuns((rs) => (rs.some((x) => x.runId === r.id) ? rs : [...rs, entry]))
        api.subscribeRunEvents(r.id, (ev) => {
          setActiveRuns((rs) => rs.map((x) => x.runId !== r.id ? x
            : ev.node === '__run__' ? { ...x, status: ev.status as ActiveRun['status'], result: ev.data }
            : { ...x, nodeStatuses: { ...x.nodeStatuses, [ev.node]: ev.status } }))
        })
      })
    })
  }, [])

  // 切到工作流视图时刷新供应商/模型
  useEffect(() => {
    if (view === 'editor') {
      api.getProviders().then(setProviders)
      api.getModels().then(setModels)
    }
  }, [view])

  const current = workflows.find((w) => w.id === currentId)

  // ---- 后台运行 ----
  const startRun = async (workflowId: string, workflowName: string,
                          inputs: Record<string, string>, nodeLabels: Record<string, string>) => {
    try {
      const rid = await api.startRun(workflowId, inputs)
      setActiveRuns((rs) => [...rs, {
        runId: rid, workflowId, workflowName, status: 'running',
        nodeStatuses: {}, nodeLabels, startedAt: Date.now(),
      }])
      api.subscribeRunEvents(rid, (ev) => {
        setActiveRuns((rs) => rs.map((r) => {
          if (r.runId !== rid) return r
          if (ev.node === '__run__') return { ...r, status: ev.status as ActiveRun['status'], result: ev.data }
          return { ...r, nodeStatuses: { ...r.nodeStatuses, [ev.node]: ev.status } }
        }))
      }, () => {
        setToast({ msg: `「${workflowName}」运行完成`, kind: 'success' })
        setTimeout(() => setToast(null), 4500)
      })
    } catch (e: any) {
      setToast({ msg: '启动运行失败: ' + e.message, kind: 'error' })
      setTimeout(() => setToast(null), 4500)
    }
  }

  const cancelRun = async (run: ActiveRun) => {
    await api.cancelRun(run.runId)
  }

  const createWorkflow = async () => {
    const name = prompt('工作流名称', '新工作流')
    if (!name) return
    const wf = await api.createWorkflow(name)
    await refreshWorkflows()
    setCurrentId(wf.id); setView('editor')
  }
  const duplicateCurrent = async () => {
    if (!currentId) return
    const wf = await api.duplicateWorkflow(currentId)
    await refreshWorkflows(); setCurrentId(wf.id)
  }
  const exportCurrent = async () => {
    if (!current) return
    const blob = new Blob([JSON.stringify({ name: current.name, description: current.description, graph: current.graph }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `${current.name}.json`; a.click()
    URL.revokeObjectURL(url)
  }
  const deleteCurrent = async () => {
    if (!current) return
    if (!confirm(`删除工作流「${current.name}」？此操作不可撤销。`)) return
    await api.deleteWorkflow(current.id)
    setDirty(false); await refreshWorkflows()
  }

  const viewCount = { 工作流: workflows.length }
  const modelCount = models.reduce((n, p) => n + (p.models?.filter((m: any) => !m.error).length || 0), 0)

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">TW <span>工作流平台</span></div>
        <nav>
          <button className={view === 'editor' ? 'active' : ''} onClick={() => setView('editor')}>工作流</button>
          <button className={view === 'assets' ? 'active' : ''} onClick={() => setView('assets')}>资产库</button>
          <button className={view === 'runs' ? 'active' : ''} onClick={() => setView('runs')}>运行历史</button>
          <button className={view === 'jobs' ? 'active' : ''} onClick={() => setView('jobs')}>定时任务</button>
          <button className={view === 'settings' ? 'active' : ''} onClick={() => setView('settings')}>设置</button>
        </nav>
        <div className="spacer" />
        <div className="meta">{providers.length} 供应商 · {modelCount} 模型</div>
      </div>

      <div className="body">
        {view === 'editor' ? (
          <>
            <div className="sidebar">
              <div className="pad" style={{ display: 'flex', gap: 6 }}>
                <button className="btn sm" style={{ flex: 1 }} onClick={createWorkflow}>+ 新建</button>
                <button className="btn ghost sm" style={{ flex: 1 }} onClick={() => setShowImport(true)}>导入</button>
              </div>
              <div className="section-title">工作流</div>
              <div className="list">
                {workflows.length === 0 && <div className="item" style={{ color: '#8b93a7' }}>暂无，点击「新建」或「导入」</div>}
                {workflows.map((w) => (
                  <div key={w.id} className={`item ${w.id === currentId ? 'active' : ''}`}
                    onClick={() => { if (dirty && w.id !== currentId && !confirm('当前未保存，切换将丢失改动，是否继续？')) return; setCurrentId(w.id) }}>
                    <span>{w.name}{w.id === currentId && dirty && <span className="dirty-dot" style={{ marginLeft: 6 }} />}</span>
                    <span className="sub">{w.graph?.nodes?.length || 0} 节点</span>
                  </div>
                ))}
              </div>
            </div>
            {current ? (
              <FlowEditor key={current.id} workflow={current} providers={providers} models={models}
                nodeTypes={nodeTypes} dirty={dirty} setDirty={setDirty}
                onSaved={refreshWorkflows}
                onExport={exportCurrent} onDuplicate={duplicateCurrent} onDelete={deleteCurrent}
                onStartRun={(inputs: Record<string, string>, nodeLabels: Record<string, string>) => startRun(current.id, current.name, inputs, nodeLabels)} />
            ) : (
              <div className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b93a7' }}>
                选择或新建一个工作流开始
              </div>
            )}
          </>
        ) : view === 'assets' ? <Assets /> : view === 'runs' ? <Runs /> : view === 'jobs' ? <Jobs /> : <Settings />}
      </div>

      <RunPanel runs={activeRuns} onCancel={cancelRun} onView={(r) => setViewRun(r)}
        onDismiss={(r) => setActiveRuns((rs) => rs.filter((x) => x.runId !== r.runId))} />

      {toast && <div className={`toast ${toast.kind}`}>{toast.msg}</div>}

      {showImport && <ImportModal onClose={() => setShowImport(false)} onImported={refreshWorkflows} />}

      {viewRun && (
        <div className="modal-bg" onClick={() => setViewRun(null)}>
          <div className="modal" style={{ width: 760 }} onClick={(e) => e.stopPropagation()}>
            <div className="mhead"><div className="title">运行结果：{viewRun.workflowName}</div>
              <button className="btn ghost sm" onClick={() => setViewRun(null)}>关闭</button></div>
            <div className="mbody">
              {viewRun.result?.error && <div style={{ color: 'var(--red)', marginBottom: 10 }}>{viewRun.result.error}</div>}
              {Object.entries(viewRun.result?.outputs || {}).map(([k, v]: any) => (
                <div key={k} style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 12, color: '#8b93a7', marginBottom: 4 }}>输出 · {k}</div>
                  <div className="output-box">{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
