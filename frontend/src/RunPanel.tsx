import { useState } from 'react'

export type ActiveRun = {
  runId: string
  workflowId: string
  workflowName: string
  status: 'running' | 'success' | 'error' | 'cancelled'
  nodeStatuses: Record<string, string>
  nodeLabels: Record<string, string>
  startedAt: number
  result?: any
}

const STATUS_TEXT: Record<string, string> = {
  running: '运行中', success: '完成', error: '出错', cancelled: '已取消',
}

function elapsed(ms: number) {
  const s = Math.round(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m${s % 60}s`
}

export function RunPanel({ runs, onCancel, onView, onDismiss }: {
  runs: ActiveRun[]
  onCancel: (run: ActiveRun) => void
  onView: (run: ActiveRun) => void
  onDismiss: (run: ActiveRun) => void
}) {
  const [collapsed, setCollapsed] = useState(false)
  if (runs.length === 0) return null
  const running = runs.filter((r) => r.status === 'running').length
  const done = runs.filter((r) => r.status !== 'running')

  return (
    <div style={{
      position: 'fixed', right: 16, bottom: 16, width: 360, zIndex: 40,
      background: 'var(--panel)', border: '1px solid var(--border)',
      borderRadius: 12, boxShadow: '0 8px 32px rgba(0,0,0,.4)', overflow: 'hidden',
    }}>
      <div onClick={() => setCollapsed((c) => !c)} style={{
        padding: '10px 14px', display: 'flex', alignItems: 'center', gap: 8,
        cursor: 'pointer', borderBottom: collapsed ? 'none' : '1px solid var(--border)',
        background: 'var(--bg-3)',
      }}>
        {running > 0 && <span className="spinner" />}
        <strong style={{ fontSize: 13 }}>{running > 0 ? `${running} 个运行中` : '运行记录'}</strong>
        <span style={{ marginLeft: 'auto', color: 'var(--text-dim)', fontSize: 12 }}>{collapsed ? '展开' : '收起'}</span>
      </div>
      {!collapsed && (
        <div style={{ maxHeight: 360, overflowY: 'auto' }}>
          {runs.map((r) => {
            const total = Object.keys(r.nodeLabels).length || 1
            const finished = Object.values(r.nodeStatuses).filter((s) => s === 'success' || s === 'error' || s === 'skipped').length
            return (
              <div key={r.runId} style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.workflowName}</span>
                  <span className={`pill ${r.status === 'running' ? 'running' : r.status === 'success' ? 'success' : r.status === 'error' ? 'error' : 'skipped'}`} style={{ fontSize: 11 }}>
                    {STATUS_TEXT[r.status]}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4, display: 'flex', gap: 8 }}>
                  <span>{r.status === 'running' ? elapsed(Date.now() - r.startedAt) : `${finished}/${total} 节点`}</span>
                  {r.status === 'running' && (
                    <>
                      <span style={{ flex: 1 }}>
                        <span style={{ display: 'inline-block', height: 4, background: 'var(--bg)', borderRadius: 2, width: '100%', verticalAlign: 'middle' }}>
                          <span style={{ display: 'inline-block', height: 4, background: 'var(--accent)', borderRadius: 2, width: `${(finished / total) * 100}%` }} />
                        </span>
                      </span>
                      <button className="btn danger sm" style={{ padding: '1px 8px' }} onClick={() => onCancel(r)}>取消</button>
                    </>
                  )}
                  {r.status !== 'running' && (
                    <>
                      <button className="btn ghost sm" style={{ padding: '1px 8px' }} onClick={() => onView(r)}>查看</button>
                      <button className="btn ghost sm" style={{ padding: '1px 8px' }} onClick={() => onDismiss(r)}>×</button>
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
