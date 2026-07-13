import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ReactFlow, ReactFlowProvider, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge, useReactFlow,
  type Connection, type Edge, type Node, MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { api, type NodeType } from './api'
import { CustomNode, type NodeData } from './CustomNode'
import { RunDialog } from './RunDialog'

const nodeTypesMap = { custom: CustomNode }

function makeDefaultConfig(type: string, nt: Record<string, NodeType>): Record<string, any> {
  const out: Record<string, any> = {}
  for (const f of nt[type]?.fields || []) out[f.key] = f.default
  return out
}

let _seq = 0
function newId(type: string) {
  _seq += 1
  return `${type}_${Date.now().toString(36)}${_seq}`
}

function FlowInner({
  workflow, providers, models, nodeTypes, dirty, setDirty, onSaved,
}: {
  workflow: any
  providers: any[]
  models: any[]
  nodeTypes: Record<string, NodeType>
  dirty: boolean
  setDirty: (v: boolean) => void
  onSaved: () => void
}) {
  const wfId = workflow.id
  const rf = useReactFlow()
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<NodeData>>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [showRun, setShowRun] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  // 加载工作流图 → React Flow
  useEffect(() => {
    const g = workflow.graph || { nodes: [], edges: [] }
    const ns: Node<NodeData>[] = (g.nodes || []).map((n: any) => ({
      id: n.id, position: n.position || { x: 0, y: 0 },
      data: { type: n.type, label: n.label || '', config: n.config || {}, color: nodeTypes[n.type]?.color, status: 'idle' },
      type: 'custom',
    }))
    const es: Edge[] = (g.edges || []).map((e: any) => ({
      id: e.id, source: e.source, target: e.target,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#8b93a7' },
    }))
    setNodes(ns)
    setEdges(es)
    setSelectedId(null)
    setDirty(false)
  }, [workflow.id]) // eslint-disable-line

  const onConnect = useCallback((c: Connection) => {
    setEdges((eds) => addEdge({ ...c, markerEnd: { type: MarkerType.ArrowClosed, color: '#8b93a7' } }, eds))
    setDirty(true)
  }, [setEdges])

  // 拖拽添加节点
  const onDragStart = (e: React.DragEvent, type: string) => {
    e.dataTransfer.setData('application/tw-node', type)
    e.dataTransfer.effectAllowed = 'move'
  }
  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move' }
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const type = e.dataTransfer.getData('application/tw-node')
    if (!type || !nodeTypes[type]) return
    const pos = rf.screenToFlowPosition({ x: e.clientX, y: e.clientY })
    const id = newId(type)
    const node: Node<NodeData> = {
      id, type: 'custom', position: pos,
      data: { type, label: nodeTypes[type].label, config: makeDefaultConfig(type, nodeTypes), color: nodeTypes[type].color, status: 'idle' },
    }
    setNodes((ns) => ns.concat(node))
    setSelectedId(id)
    setDirty(true)
  }
  // 点击 palette 也可添加（居中）
  const addAtCenter = (type: string) => {
    const center = rf.screenToFlowPosition({ x: window.innerWidth / 2, y: window.innerHeight / 2 })
    const id = newId(type)
    setNodes((ns) => ns.concat({
      id, type: 'custom', position: { x: center.x - 100 + (ns.length % 5) * 30, y: center.y - 40 + (ns.length % 5) * 30 },
      data: { type, label: nodeTypes[type].label, config: makeDefaultConfig(type, nodeTypes), color: nodeTypes[type].color, status: 'idle' },
    } as Node<NodeData>))
    setDirty(true)
  }

  const selected = useMemo(
    () => nodes.find((n) => n.id === selectedId) as Node<NodeData> | undefined,
    [nodes, selectedId],
  )

  const updateConfig = (key: string, val: any) => {
    if (!selected) return
    setNodes((ns) => ns.map((n) => n.id === selected.id
      ? { ...n, data: { ...n.data, config: { ...n.data.config, [key]: val } } } : n))
    setDirty(true)
  }
  const updateLabel = (val: string) => {
    if (!selected) return
    setNodes((ns) => ns.map((n) => n.id === selected.id ? { ...n, data: { ...n.data, label: val } } : n))
    setDirty(true)
  }
  const deleteSelected = () => {
    if (!selectedId) return
    setNodes((ns) => ns.filter((n) => n.id !== selectedId))
    setEdges((es) => es.filter((e) => e.source !== selectedId && e.target !== selectedId))
    setSelectedId(null)
    setDirty(true)
  }

  // 保存
  const save = async () => {
    setSaving(true)
    const graph = {
      nodes: nodes.map((n) => {
        const d = n.data as NodeData
        const cfg = { ...d.config }
        const out: any = { id: n.id, type: d.type, label: d.label || '', position: n.position, config: cfg }
        return out
      }),
      edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target })),
    }
    try {
      await api.updateWorkflow(wfId, { graph })
      setDirty(false)
      onSaved()
    } catch (e: any) {
      alert('保存失败: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  // 删除键
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === 'Delete' || e.key === 'Backspace') && selectedId) {
        const tag = (e.target as HTMLElement)?.tagName
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
        deleteSelected()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selectedId]) // eslint-disable-line

  return (
    <div className="canvas-wrap">
      {/* 节点面板 */}
      <div className="palette">
        <div className="ptitle">节点</div>
        {Object.entries(nodeTypes).map(([k, v]) => (
          <div key={k} className="pnode"
            draggable onDragStart={(e) => onDragStart(e, k)}
            onDoubleClick={() => addAtCenter(k)}
            title={`${v.label}：${v.desc}（双击添加）`}>
            <span className="dot" style={{ background: v.color }} />
            {v.label}
          </div>
        ))}
        <div className="hint" style={{ marginTop: 8 }}>拖拽到画布，或双击添加。提示：在节点配置里用 <code>{'{{节点ID}}'}</code> 引用上游输出。</div>
      </div>

      {/* 画布 */}
      <div className="flow" ref={wrapperRef} onDrop={onDrop} onDragOver={onDragOver}>
        <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 5, display: 'flex', gap: 8 }}>
          <button className="btn ghost sm" onClick={save} disabled={saving || !dirty}>
            {saving ? '保存中…' : dirty ? '💾 保存 *' : '💾 已保存'}
          </button>
          <button className="btn sm" onClick={() => setShowRun(true)} disabled={dirty}>
            {dirty ? '请先保存' : '▶ 运行'}
          </button>
        </div>
        <ReactFlow
          nodes={nodes} edges={edges}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, n) => setSelectedId(n.id)}
          onPaneClick={() => setSelectedId(null)}
          nodeTypes={nodeTypesMap}
          fitView
          defaultEdgeOptions={{ markerEnd: { type: MarkerType.ArrowClosed, color: '#8b93a7' } }}
        >
          <Background color="#2a3142" gap={20} />
          <Controls />
          <MiniMap pannable zoomable nodeColor={(n) => (n.data as NodeData)?.color || '#475569'} />
        </ReactFlow>
      </div>

      {/* 属性面板 */}
      <div className="props">
        <div className="pheader">
          <strong>{selected ? '节点属性' : '属性'}</strong>
          {selected && <button className="btn danger sm" style={{ marginLeft: 'auto' }} onClick={deleteSelected}>删除</button>}
        </div>
        <div className="pbody">
          {!selected ? (
            <div className="empty">从画布选择一个节点来编辑参数。<br /><br />数据流：在 LLM/转换/输出节点的文本框里写 <code>{'{{节点ID}}'}</code> 或 <code>{'{{节点ID.字段}}'}</code> 引用上游节点的输出。</div>
          ) : (
            <>
              <div className="field">
                <label>名称</label>
                <input value={selected.data.label || ''} onChange={(e) => updateLabel(e.target.value)} />
              </div>
              <div style={{ fontSize: 11, color: '#8b93a7', marginBottom: 12 }}>ID: <code>{selected.id}</code></div>
              {(nodeTypes[selected.data.type]?.fields || []).map((f) => (
                <FieldEditor key={f.key} field={f} value={selected.data.config?.[f.key]}
                  onChange={(v) => updateConfig(f.key, v)}
                  providers={providers} models={models} provider={selected.data.config?.provider} />
              ))}
              <div className="field">
                <label>运行条件 run_if（可选）</label>
                <input placeholder="留空则总是运行，如 {{cond.pass}}" value={selected.data.config?._run_if || ''}
                  onChange={(e) => updateConfig('_run_if', e.target.value)} />
                <div className="hint">解析为假(空/0/false)时跳过本节点。</div>
              </div>
            </>
          )}
        </div>
      </div>

      {showRun && (
        <RunDialog workflowId={wfId} workflowName={workflow.name}
          nodes={nodes} setNodes={setNodes}
          onClose={() => setShowRun(false)} />
      )}
    </div>
  )
}

function FieldEditor({ field, value, onChange, providers, models, provider }: {
  field: { key: string; label: string; type: string }
  value: any
  onChange: (v: any) => void
  providers: any[]
  models: any[]
  provider?: string
}) {
  if (field.type === 'provider') {
    return (
      <div className="field">
        <label>{field.label}</label>
        <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
          <option value="">— 选择供应商 —</option>
          {providers.map((p) => <option key={p.name} value={p.name}>{p.name}（{p.type}）</option>)}
        </select>
      </div>
    )
  }
  if (field.type === 'model') {
    const opts = (models.find((p) => p.provider === provider)?.models || []).filter((m: any) => !m.error)
    return (
      <div className="field">
        <label>{field.label}</label>
        <select value={value || ''} onChange={(e) => onChange(e.target.value)}>
          <option value="">— 选择模型 —</option>
          {opts.map((m: any) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        {opts.length === 0 && <div className="hint">该供应商暂无可用模型（检查 API Key / Ollama 是否运行）</div>}
      </div>
    )
  }
  if (field.type === 'textarea') {
    return (
      <div className="field">
        <label>{field.label}</label>
        <textarea value={value ?? ''} onChange={(e) => onChange(e.target.value)} rows={5} />
      </div>
    )
  }
  if (field.type === 'code') {
    return (
      <div className="field">
        <label>{field.label}</label>
        <textarea value={value ?? ''} onChange={(e) => onChange(e.target.value)} rows={6}
          style={{ fontFamily: 'ui-monospace, Consolas, monospace', fontSize: 12 }} />
      </div>
    )
  }
  if (field.type === 'number') {
    return (
      <div className="field">
        <label>{field.label}</label>
        <input type="number" value={value ?? 0} onChange={(e) => onChange(parseFloat(e.target.value))} />
      </div>
    )
  }
  return (
    <div className="field">
      <label>{field.label}</label>
      <input value={value ?? ''} onChange={(e) => onChange(e.target.value)} />
    </div>
  )
}

export function FlowEditor(props: any) {
  return (
    <ReactFlowProvider>
      <FlowInner {...props} />
    </ReactFlowProvider>
  )
}
