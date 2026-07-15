import { useState } from 'react'
import { api } from './api'

export function ImportModal({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const [text, setText] = useState('')
  const [err, setErr] = useState('')

  const doImport = async (raw: string) => {
    setErr('')
    let doc: any
    try { doc = JSON.parse(raw) }
    catch { setErr('JSON 格式错误，请检查'); return }
    const graph = doc.graph || doc
    const name = doc.name || '导入的工作流'
    if (!graph.nodes || !graph.edges) { setErr('缺少 graph.nodes 或 graph.edges'); return }
    try {
      await api.importWorkflow({ name, description: doc.description || '', graph })
      onImported(); onClose()
    } catch (e: any) { setErr('导入失败: ' + e.message) }
  }

  const onFile = (f: File) => {
    const reader = new FileReader()
    reader.onload = () => { setText(String(reader.result || '')); doImport(String(reader.result || '')) }
    reader.readAsText(f)
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" style={{ width: 620 }} onClick={(e) => e.stopPropagation()}>
        <div className="mhead">
          <div className="title">导入工作流</div>
          <button className="btn ghost sm" onClick={onClose}>关闭</button>
        </div>
        <div className="mbody">
          <div className="hint" style={{ marginBottom: 10 }}>
            粘贴工作流 JSON（含 name / graph.nodes / graph.edges），或选择 .json 文件。可在「工作流」页用「导出」获得此格式。
          </div>
          <div className="field">
            <label>选择文件</label>
            <input type="file" accept=".json,application/json" onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])} />
          </div>
          <div className="field">
            <label>或粘贴 JSON</label>
            <textarea rows={10} value={text} onChange={(e) => setText(e.target.value)}
              placeholder='{\n  "name": "我的工作流",\n  "graph": { "nodes": [...], "edges": [...] }\n}'
              style={{ fontFamily: 'ui-monospace, Consolas, monospace', fontSize: 12 }} />
          </div>
          {err && <div style={{ color: 'var(--red)', fontSize: 12, marginBottom: 8 }}>{err}</div>}
        </div>
        <div className="mfoot">
          <button className="btn ghost" onClick={onClose}>取消</button>
          <button className="btn" onClick={() => doImport(text)} disabled={!text.trim()}>导入</button>
        </div>
      </div>
    </div>
  )
}
