import { useState } from 'react'

// 仅用于收集运行输入参数；点「开始运行」后立即交给后台执行并关闭，不阻塞页面。
export function RunDialog({ workflowName, inputNodes, onClose, onStart }: {
  workflowName: string
  inputNodes: any[]
  onClose: () => void
  onStart: (inputs: Record<string, string>) => void
}) {
  const [inputs, setInputs] = useState<Record<string, string>>(() => {
    const o: Record<string, string> = {}
    for (const n of inputNodes) {
      const key = n.data?.config?.key || n.id
      o[key] = n.data?.config?.default || ''
    }
    return o
  })

  const start = () => {
    onStart(inputs)
    onClose()
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" style={{ width: 480 }} onClick={(e) => e.stopPropagation()}>
        <div className="mhead">
          <div className="title">运行：{workflowName}</div>
          <button className="btn ghost sm" onClick={onClose}>取消</button>
        </div>
        <div className="mbody">
          {inputNodes.length === 0 ? (
            <div className="hint">该工作流没有输入节点，直接开始即可。运行将在后台进行，期间可自由操作页面。</div>
          ) : (
            inputNodes.map((n) => {
              const key = n.data?.config?.key || n.id
              return (
                <div className="field" key={n.id}>
                  <label>{n.data?.label || key}（{key}）</label>
                  <input value={inputs[key] ?? ''} onChange={(e) => setInputs({ ...inputs, [key]: e.target.value })}
                    onKeyDown={(e) => { if (e.key === 'Enter') start() }} />
                </div>
              )
            })
          )}
        </div>
        <div className="mfoot">
          <button className="btn ghost" onClick={onClose}>取消</button>
          <button className="btn" onClick={start}>▶ 开始运行（后台）</button>
        </div>
      </div>
    </div>
  )
}
