import { useEffect, useState } from 'react'
import { api } from './api'

function fmt(ts: number) {
  return new Date(ts < 1e12 ? ts * 1000 : ts).toLocaleString('zh-CN')
}

const STATUS_COLOR: Record<string, string> = {
  success: 'var(--green)', partial: 'var(--amber)', error: 'var(--red)', running: 'var(--amber)',
}

export function Runs() {
  const [runs, setRuns] = useState<any[]>([])
  const [detail, setDetail] = useState<any>(null)

  const refresh = () => api.listRuns().then(setRuns)
  useEffect(() => { refresh(); const t = setInterval(refresh, 4000); return () => clearInterval(t) }, [])

  return (
    <div className="page">
      <h2>运行历史</h2>
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>工作流</th><th>来源</th><th>状态</th><th>开始时间</th><th>耗时</th><th>查看</th></tr></thead>
          <tbody>
            {runs.length === 0 && <tr><td colSpan={6} style={{ color: '#8b93a7', textAlign: 'center' }}>暂无运行</td></tr>}
            {runs.map((r) => (
              <tr key={r.id}>
                <td>{r.workflow_name}</td>
                <td><span className="tag">{r.source}</span></td>
                <td><span style={{ color: STATUS_COLOR[r.status] || '#8b93a7' }}>{r.status}</span></td>
                <td style={{ fontSize: 12 }}>{fmt(r.started_at)}</td>
                <td style={{ fontSize: 12 }}>{r.finished_at ? `${Math.round((r.finished_at - r.started_at))}s` : '—'}</td>
                <td><button className="btn ghost sm" onClick={() => setDetail(r)}>详情</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="modal-bg" onClick={() => setDetail(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="mhead"><div className="title">运行详情：{detail.workflow_name}</div>
              <button className="btn ghost sm" onClick={() => setDetail(null)}>关闭</button></div>
            <div className="mbody">
              {detail.error && <div style={{ color: 'var(--red)', marginBottom: 10 }}>{detail.error}</div>}
              {Object.entries(detail.outputs || {}).map(([k, v]: any) => (
                <div key={k} style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: 12, color: '#8b93a7', marginBottom: 4 }}>输出 · {k}</div>
                  <div className="output-box">{v}</div>
                </div>
              ))}
              <details>
                <summary style={{ cursor: 'pointer', color: '#8b93a7', fontSize: 12 }}>节点级输出（调试用）</summary>
                <pre style={{ fontSize: 11, maxHeight: 300, overflow: 'auto', background: 'var(--bg)', padding: 10, borderRadius: 8 }}>
                  {JSON.stringify(detail.node_outputs, null, 2)}
                </pre>
              </details>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
