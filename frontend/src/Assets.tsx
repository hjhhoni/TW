import { useEffect, useState } from 'react'
import { api } from './api'

function fmt(ts: number) { return new Date(ts < 1e12 ? ts * 1000 : ts).toLocaleString('zh-CN') }

export function Assets() {
  const [assets, setAssets] = useState<any[]>([])
  const [detail, setDetail] = useState<any>(null)
  const [detailContent, setDetailContent] = useState('')

  const refresh = () => api.listAssets().then(setAssets)
  useEffect(() => { refresh() }, [])

  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => alert('已复制到剪贴板')).catch(() => alert('复制失败'))
  }
  const download = (a: any, text: string) => {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const el = document.createElement('a')
    el.href = url; el.download = `${a.title}.txt`; el.click()
    URL.revokeObjectURL(url)
  }
  const remove = async (a: any) => {
    if (!confirm(`删除资产「${a.title}」？`)) return
    await api.deleteAsset(a.id); refresh()
  }
  const open = async (a: any) => {
    const full = await api.getAsset(a.id)
    setDetail(a); setDetailContent(full.content || '')
  }

  return (
    <div className="page">
      <h2>资产库</h2>
      <div className="hint" style={{ marginBottom: 16 }}>工作流每次运行的输出会自动保存到这里，可随时复制 / 下载 / 删除。</div>
      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>标题</th><th>来源工作流</th><th>大小</th><th>时间</th><th>操作</th></tr></thead>
          <tbody>
            {assets.length === 0 && <tr><td colSpan={5} style={{ color: '#8b93a7', textAlign: 'center' }}>暂无资产，运行工作流后会自动生成</td></tr>}
            {assets.map((a) => (
              <tr key={a.id}>
                <td style={{ cursor: 'pointer', color: 'var(--accent-2)' }} onClick={() => open(a)}>{a.title}</td>
                <td style={{ fontSize: 12 }}>{a.workflow_name}</td>
                <td style={{ fontSize: 12 }}>{a.size} 字符</td>
                <td style={{ fontSize: 12 }}>{fmt(a.created_at)}</td>
                <td>
                  <button className="btn ghost sm" onClick={() => open(a)}>预览</button>{' '}
                  <button className="btn ghost sm" onClick={() => api.getAsset(a.id).then((f) => copy(f.content))}>复制</button>{' '}
                  <button className="btn ghost sm" onClick={() => api.getAsset(a.id).then((f) => download(a, f.content))}>下载</button>{' '}
                  <button className="btn danger sm" onClick={() => remove(a)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="modal-bg" onClick={() => setDetail(null)}>
          <div className="modal" style={{ width: 780 }} onClick={(e) => e.stopPropagation()}>
            <div className="mhead">
              <div className="title">{detail.title}</div>
              <button className="btn ghost sm" onClick={() => setDetail(null)}>关闭</button>
            </div>
            <div className="mbody">
              <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
                <button className="btn ghost sm" onClick={() => copy(detailContent)}>📋 复制全部</button>
                <button className="btn ghost sm" onClick={() => download(detail, detailContent)}>⬇ 下载</button>
                <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-dim)' }}>{fmt(detail.created_at)} · {detail.workflow_name}</span>
              </div>
              <div className="output-box" style={{ maxHeight: '60vh' }}>{detailContent}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
