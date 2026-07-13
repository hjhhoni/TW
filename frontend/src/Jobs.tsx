import { useEffect, useState } from 'react'
import { api } from './api'

function fmt(ts: number | null) {
  if (!ts) return '—'
  return new Date(ts < 1e12 ? ts * 1000 : ts).toLocaleString('zh-CN')
}

export function Jobs() {
  const [jobs, setJobs] = useState<any[]>([])
  const [workflows, setWorkflows] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)

  const refresh = () => {
    api.listJobs().then(setJobs)
    api.listWorkflows().then(setWorkflows)
  }
  useEffect(() => { refresh() }, [])

  return (
    <div className="page">
      <h2>定时任务</h2>
      <button className="btn" onClick={() => setShowForm(true)} style={{ marginBottom: 16 }}>+ 新建定时任务</button>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead><tr><th>工作流</th><th>类型</th><th>调度配置</th><th>状态</th><th>上次运行</th><th>下次运行</th><th>操作</th></tr></thead>
          <tbody>
            {jobs.length === 0 && <tr><td colSpan={7} style={{ color: '#8b93a7', textAlign: 'center' }}>暂无定时任务</td></tr>}
            {jobs.map((j) => (
              <tr key={j.id}>
                <td>{j.workflow_name}</td>
                <td><span className="tag">{j.trigger_type}</span></td>
                <td style={{ fontSize: 12, color: '#8b93a7' }}>{j.trigger_config}</td>
                <td><span className={`tag ${j.enabled ? 'badge-on' : 'badge-off'}`}>{j.enabled ? '启用' : '停用'}</span></td>
                <td style={{ fontSize: 12 }}>{fmt(j.last_run_at)}</td>
                <td style={{ fontSize: 12 }}>{fmt(j.next_run_at)}</td>
                <td>
                  <button className="btn ghost sm" onClick={async () => { await api.toggleJob(j.id); refresh() }}>{j.enabled ? '停用' : '启用'}</button>
                  {' '}
                  <button className="btn danger sm" onClick={async () => { await api.deleteJob(j.id); refresh() }}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <JobForm workflows={workflows} onClose={refresh} onCancel={() => setShowForm(false)} />
      )}
    </div>
  )
}

function JobForm({ workflows, onClose, onCancel }: { workflows: any[]; onClose: () => void; onCancel: () => void }) {
  const [workflowId, setWorkflowId] = useState(workflows[0]?.id || '')
  const [type, setType] = useState<'cron' | 'interval'>('cron')
  const [monthDay, setMonthDay] = useState('1')
  const [hour, setHour] = useState('9')
  const [minute, setMinute] = useState('0')
  const [intervalHours, setIntervalHours] = useState('6')

  const create = async () => {
    let tc: any
    if (type === 'cron') tc = { day: monthDay || '*', hour, minute }
    else tc = { hours: intervalHours }
    await api.createJob({ workflow_id: workflowId, trigger_type: type, trigger_config: tc, inputs: {}, enabled: true })
    onCancel()
    onClose()
  }

  return (
    <div className="modal-bg" onClick={onCancel}>
      <div className="modal" style={{ width: 480 }} onClick={(e) => e.stopPropagation()}>
        <div className="mhead"><div className="title">新建定时任务</div></div>
        <div className="mbody">
          <div className="field"><label>工作流</label>
            <select value={workflowId} onChange={(e) => setWorkflowId(e.target.value)}>
              {workflows.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </select></div>
          <div className="field"><label>触发方式</label>
            <select value={type} onChange={(e) => setType(e.target.value as any)}>
              <option value="cron">定时（cron，按月/日/时/分）</option>
              <option value="interval">间隔（每 N 小时）</option>
            </select></div>
          {type === 'cron' ? (
            <div className="row">
              <div className="field"><label>每月几号（*为每天）</label><input value={monthDay} onChange={(e) => setMonthDay(e.target.value)} /></div>
              <div className="field"><label>时</label><input value={hour} onChange={(e) => setHour(e.target.value)} /></div>
              <div className="field"><label>分</label><input value={minute} onChange={(e) => setMinute(e.target.value)} /></div>
            </div>
          ) : (
            <div className="field"><label>间隔（小时）</label><input value={intervalHours} onChange={(e) => setIntervalHours(e.target.value)} /></div>
          )}
          <div className="hint">示例：每月 1 号 9:00 → day=1 hour=9 minute=0（月报常用）。运行时输入参数留空（按工作流默认值）。</div>
        </div>
        <div className="mfoot">
          <button className="btn ghost" onClick={onCancel}>取消</button>
          <button className="btn" onClick={create}>创建</button>
        </div>
      </div>
    </div>
  )
}
