import { useEffect, useState } from 'react'
import { api } from './api'
import type { NodeData } from './CustomNode'

export function RunDialog({ workflowId, workflowName, nodes, setNodes, onClose }: {
  workflowId: string
  workflowName: string
  nodes: any[]
  setNodes: React.Dispatch<React.SetStateAction<any[]>>
  onClose: () => void
}) {
  const inputNodes = nodes.filter((n) => n.data?.type === 'input')
  const [inputs, setInputs] = useState<Record<string, string>>(() => {
    const o: Record<string, string> = {}
    for (const n of inputNodes) {
      const key = n.data?.config?.key || n.id
      o[key] = n.data?.config?.default || ''
    }
    return o
  })
  const [running, setRunning] = useState(false)
  const [statusMap, setStatusMap] = useState<Record<string, string>>({})
  const [result, setResult] = useState<any>(null)
  const [activeKey, setActiveKey] = useState<string>('__default')

  const patchNode = (id: string, status: string, preview?: string) =>
    setNodes((ns) => ns.map((n) => {
      if (n.id !== id) return n
      const data = { ...(n.data as NodeData), status }
      if (preview !== undefined) data.preview = preview
      else if (status === 'idle') data.preview = undefined
      return { ...n, data }
    }))

  const run = () => {
    setRunning(true)
    setResult(null)
    setStatusMap({})
    // 重置画布状态
    setNodes((ns) => ns.map((n) => ({ ...n, data: { ...(n.data as NodeData), status: 'idle', preview: undefined } })))
    api.runStream(workflowId, inputs, (ev) => {
      if (ev.node === '__run__') {
        setRunning(false)
        setResult(ev.data)
        const outs = ev.data?.outputs || {}
        const keys = Object.keys(outs)
        if (keys.length) setActiveKey(keys[0])
        return
      }
      setStatusMap((s) => ({ ...s, [ev.node]: ev.status }))
      patchNode(ev.node, ev.status, ev.status === 'success' ? ev.data?.preview : ev.status === 'error' ? '❌ ' + (ev.data?.error || '') : undefined)
    })
  }

  useEffect(() => { return () => {} }, [])

  const outputs = result?.outputs || {}
  const outputKeys = Object.keys(outputs)

  return (
    <div className="modal-bg" onClick={running ? undefined : onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="mhead">
          <div className="title">运行：{workflowName}</div>
          <button className="btn ghost sm" onClick={onClose} disabled={running}>关闭</button>
        </div>
        <div className="mbody">
          {inputNodes.length > 0 && (
            <>
              <h3 style={{ margin: '0 0 10px', fontSize: 13 }}>输入参数</h3>
              {inputNodes.map((n) => {
                const key = n.data?.config?.key || n.id
                return (
                  <div className="field" key={n.id}>
                    <label>{n.data?.label || key}（{key}）</label>
                    <input value={inputs[key] ?? ''} disabled={running}
                      onChange={(e) => setInputs({ ...inputs, [key]: e.target.value })} />
                  </div>
                )
              })}
            </>
          )}

          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14 }}>
            <button className="btn" onClick={run} disabled={running}>
              {running ? '运行中…' : '▶ 开始运行'}
            </button>
            {running && <span style={{ color: '#f59e0b', fontSize: 12 }}>实时联网搜索 + 模型生成中…</span>}
          </div>

          {/* 进度 */}
          {Object.keys(statusMap).length > 0 && (
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 12, color: '#8b93a7', marginBottom: 6 }}>执行进度</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {nodes.map((n) => {
                  const s = statusMap[n.id]
                  if (!s) return null
                  return (
                    <span key={n.id} className={`pill ${s === 'idle' ? 'skipped' : s}`} style={{ fontSize: 11 }}>
                      {n.data?.label || n.id}: {{ running: '运行中', success: '✓', error: '✗', skipped: '跳' }[s] || s}
                    </span>
                  )
                })}
              </div>
            </div>
          )}

          {/* 结果 */}
          {result && (
            <>
              {result.error && <div style={{ color: '#ef4444', marginBottom: 10 }}>错误：{result.error}</div>}
              {outputKeys.length > 0 && (
                <>
                  {outputKeys.length > 1 && (
                    <div style={{ display: 'flex', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
                      {outputKeys.map((k) => (
                        <button key={k} className={`btn sm ${activeKey === k ? '' : 'ghost'}`} onClick={() => setActiveKey(k)}>{k}</button>
                      ))}
                    </div>
                  )}
                  <div className="output-box">{outputs[activeKey]}</div>
                  <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                    <button className="btn ghost sm" onClick={() => {
                      const blob = new Blob([outputs[activeKey]], { type: 'text/plain;charset=utf-8' })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement('a')
                      a.href = url; a.download = `${workflowName}-${activeKey}.txt`; a.click()
                      URL.revokeObjectURL(url)
                    }}>⬇ 下载</button>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
