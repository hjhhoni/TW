import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'

export type NodeData = {
  type: string
  label: string
  config: Record<string, any>
  color?: string
  status?: string // idle | running | success | error | skipped
  preview?: string
  [_: string]: any
}

const FALLBACK_COLORS: Record<string, string> = {
  input: '#3b82f6', search: '#10b981', fetch: '#14b8a6', llm: '#f59e0b',
  transform: '#8b5cf6', condition: '#ef4444', output: '#6366f1',
}

const STATUS_LABEL: Record<string, string> = {
  running: '运行中', success: '完成', error: '出错', skipped: '跳过', idle: '就绪',
}

function previewOf(type: string, cfg: Record<string, any>): string {
  const first = (s: any) => (s || '').toString().split('\n')[0].slice(0, 60)
  switch (type) {
    case 'input': return `${cfg.key || ''} = ${first(cfg.default)}`
    case 'llm': return cfg.model ? `🤖 ${cfg.model}` : '未选模型'
    case 'search': return first(cfg.query) || '（空查询）'
    case 'fetch': {
      const d = [cfg.date_from, cfg.date_to].filter(Boolean).join(' ~ ')
      return d ? `📅 ${d}` : first(cfg.urls) || '（来源 {{search.urls}}）'
    }
    case 'transform': return cfg.code ? '🐍 code' : first(cfg.template)
    case 'condition': return `if ${first(cfg.expr)}`
    case 'output': return first(cfg.value)
    default: return ''
  }
}

function CustomNodeInner({ data, selected }: NodeProps) {
  const d = data as NodeData
  const color = d.color || FALLBACK_COLORS[d.type] || '#64748b'
  const status = d.status || 'idle'
  const hasTarget = d.type !== 'input'
  const hasSource = d.type !== 'output'
  const livePreview = d.preview !== undefined ? d.preview : previewOf(d.type, d.config || {})

  return (
    <div className={`rf-node ${selected ? 'selected' : ''}`}>
      {hasTarget && (
        <Handle type="target" position={Position.Left} style={{ background: '#475569' }} />
      )}
      <div className="nhead">
        <span className="ndot" style={{ background: color }} />
        <span>{d.label || d.type}</span>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: '#8b93a7' }}>{d.type}</span>
      </div>
      <div className="nbody">
        <div className="preview">{livePreview || <span style={{ opacity: .5 }}>（无内容）</span>}</div>
      </div>
      <div className="nstatus">
        <span style={{ opacity: .6 }}>{d.type}</span>
        <span className={`pill ${status === 'idle' ? 'skipped' : status}`}>{STATUS_LABEL[status] || status}</span>
      </div>
      {hasSource && (
        <Handle type="source" position={Position.Right} style={{ background: color }} />
      )}
    </div>
  )
}

export const CustomNode = memo(CustomNodeInner)
