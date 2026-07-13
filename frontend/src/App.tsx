import { useEffect, useState } from 'react'
import { api, type NodeType } from './api'
import { FlowEditor } from './FlowEditor'
import { Runs } from './Runs'
import { Jobs } from './Jobs'
import { Settings } from './Settings'

type View = 'editor' | 'runs' | 'jobs' | 'settings'

export default function App() {
  const [view, setView] = useState<View>('editor')
  const [workflows, setWorkflows] = useState<any[]>([])
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [nodeTypes, setNodeTypes] = useState<Record<string, NodeType>>({})
  const [providers, setProviders] = useState<any[]>([])
  const [models, setModels] = useState<any[]>([])
  const [dirty, setDirty] = useState(false)
  const [creating, setCreating] = useState(false)

  const refreshAll = () => {
    api.nodeTypes().then(setNodeTypes)
    api.getProviders().then(setProviders)
    api.getModels().then((m) => setModels(m))
    api.listWorkflows().then((ws) => {
      setWorkflows(ws)
      if (ws.length && !currentId) setCurrentId(ws[0].id)
    })
  }
  useEffect(() => { refreshAll() }, []) // eslint-disable-line

  const current = workflows.find((w) => w.id === currentId)

  const createWorkflow = async () => {
    const name = prompt('工作流名称', '新工作流')
    if (!name) return
    setCreating(true)
    try {
      const wf = await api.createWorkflow(name)
      await api.listWorkflows().then(setWorkflows)
      setCurrentId(wf.id)
      setView('editor')
    } finally { setCreating(false) }
  }

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">TW <span>工作流平台</span></div>
        <nav>
          <button className={view === 'editor' ? 'active' : ''} onClick={() => setView('editor')}>工作流</button>
          <button className={view === 'runs' ? 'active' : ''} onClick={() => setView('runs')}>运行历史</button>
          <button className={view === 'jobs' ? 'active' : ''} onClick={() => setView('jobs')}>定时任务</button>
          <button className={view === 'settings' ? 'active' : ''} onClick={() => setView('settings')}>设置</button>
        </nav>
        <div className="spacer" />
        <div className="meta">{providers.length} 个供应商 · {models.reduce((n, p) => n + (p.models?.filter((m: any) => !m.error).length || 0), 0)} 个模型</div>
      </div>

      <div className="body">
        {view === 'editor' ? (
          <>
            <div className="sidebar">
              <div className="pad">
                <button className="btn" style={{ width: '100%' }} onClick={createWorkflow} disabled={creating}>+ 新建工作流</button>
              </div>
              <div className="section-title">工作流</div>
              <div className="list">
                {workflows.length === 0 && <div className="item" style={{ color: '#8b93a7' }}>暂无，点击上方新建</div>}
                {workflows.map((w) => (
                  <div key={w.id} className={`item ${w.id === currentId ? 'active' : ''}`} onClick={() => { if (dirty && !confirm('当前工作流未保存，切换将丢失改动，是否继续？')) return; setCurrentId(w.id) }}>
                    <span>{w.name}{w.id === currentId && dirty && <span className="dirty-dot" style={{ marginLeft: 6 }} />}</span>
                    <span className="sub">{(w.graph?.nodes?.length || 0)} 节点</span>
                  </div>
                ))}
              </div>
            </div>
            {current ? (
              <FlowEditor key={current.id} workflow={current} providers={providers} models={models}
                nodeTypes={nodeTypes} dirty={dirty} setDirty={setDirty}
                onSaved={() => api.listWorkflows().then(setWorkflows)} />
            ) : (
              <div className="page" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#8b93a7' }}>
                选择或新建一个工作流开始
              </div>
            )}
          </>
        ) : view === 'runs' ? <Runs /> : view === 'jobs' ? <Jobs /> : <Settings />}
      </div>
    </div>
  )
}
