import { useEffect, useState } from 'react'
import { api } from './api'

let _uidSeq = 0
const uid = () => `p${Date.now().toString(36)}${_uidSeq++}`

export function Settings({ onSaved }: { onSaved?: () => void }) {
  const [settings, setSettings] = useState<any>(null)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.getSettings().then((s: any) => {
      s.providers = (s.providers || []).map((p: any) => ({ ...p, _uid: p._uid || uid() }))
      setSettings(s)
    })
  }, [])

  if (!settings) return <div className="page">加载中…</div>

  const patchProvider = (i: number, patch: any) => {
    const arr = settings.providers.map((p: any, j: number) => (j === i ? { ...p, ...patch } : p))
    setSettings({ ...settings, providers: arr })
  }
  const removeProvider = (i: number) =>
    setSettings({ ...settings, providers: settings.providers.filter((_: any, j: number) => j !== i) })
  const addProvider = () =>
    setSettings({
      ...settings,
      providers: settings.providers.concat({ _uid: uid(), type: 'openai_compat', name: '新供应商', base_url: '', api_key: '' }),
    })
  const setBrowser = (k: string, v: any) => setSettings({ ...settings, browser: { ...settings.browser, [k]: v } })

  const save = async () => {
    // 保存前剥掉前端的 _uid
    const toSave = {
      ...settings,
      providers: settings.providers.map(({ _uid, ...rest }: any) => rest),
    }
    await api.saveSettings(toSave)
    await api.reloadProviders()
    setMsg('已保存并重新加载供应商')
    setTimeout(() => setMsg(''), 3000)
    onSaved?.()
  }

  return (
    <div className="page">
      <h2>设置</h2>

      <div className="card">
        <h3>模型供应商</h3>
        <div className="hint" style={{ marginBottom: 12 }}>
          支持 OpenAI 兼容接口（OpenAI / DeepSeek / Moonshot / 智谱 / 硅基流动）、Anthropic（Claude）、本地 Ollama。
          填好 Base URL 和 API Key 后点「测试连接 / 拉取模型」可即时验证并拉取模型列表，再选模型做「测速」。保存后工作流的模型下拉会自动刷新。
        </div>
        {settings.providers.map((p: any, i: number) => (
          <ProviderCard key={p._uid} p={p}
            onChange={(patch) => patchProvider(i, patch)}
            onRemove={() => removeProvider(i)} />
        ))}
        <button className="btn ghost sm" onClick={addProvider}>+ 添加供应商</button>
      </div>

      <div className="card">
        <h3>浏览器（联网搜索）</h3>
        <div className="row">
          <div className="field"><label>无头模式</label>
            <select value={String(!!settings.browser.headless)} onChange={(e) => setBrowser('headless', e.target.value === 'true')}>
              <option value="true">true（后台运行，推荐）</option>
              <option value="false">false（显示浏览器窗口，便于调试）</option>
            </select></div>
          <div className="field"><label>默认搜索引擎</label>
            <select value={settings.browser.search_engine} onChange={(e) => setBrowser('search_engine', e.target.value)}>
              <option value="bing">bing</option>
              <option value="baidu">baidu</option>
              <option value="google">google</option>
            </select></div>
          <div className="field"><label>代理（可选）</label>
            <input value={settings.browser.proxy || ''} placeholder="http://127.0.0.1:7890" onChange={(e) => setBrowser('proxy', e.target.value)} /></div>
        </div>
        <div className="hint" style={{ marginTop: 8 }}>搜索引擎仅作为未指定时的默认值；工作流节点可单独指定。多引擎会并发并去重。</div>
      </div>

      <button className="btn" onClick={save}>💾 保存设置</button>
      {msg && <span style={{ marginLeft: 12, color: 'var(--green)' }}>{msg}</span>}
    </div>
  )
}

function ProviderCard({ p, onChange, onRemove }: {
  p: any
  onChange: (patch: any) => void
  onRemove: () => void
}) {
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [speedModel, setSpeedModel] = useState('')

  const placeholder =
    p.type === 'anthropic' ? 'https://api.anthropic.com' :
    p.type === 'ollama' ? 'http://localhost:11434' : 'https://api.openai.com/v1'

  const run = async (model?: string) => {
    setTesting(true)
    try {
      const r = await api.testProvider({ type: p.type, base_url: p.base_url, api_key: p.api_key, model })
      setResult(r)
      if (r.ok && r.models?.length && !speedModel) setSpeedModel(r.models[0].id)
    } catch (e: any) {
      setResult({ ok: false, error: e.message })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="card" style={{ background: 'var(--bg-2)', marginBottom: 10 }}>
      <div className="row">
        <div className="field"><label>显示名称</label>
          <input value={p.name ?? ''} onChange={(e) => onChange({ name: e.target.value })} /></div>
        <div className="field"><label>类型</label>
          <select value={p.type} onChange={(e) => onChange({ type: e.target.value })}>
            <option value="openai_compat">openai_compat（OpenAI 兼容）</option>
            <option value="anthropic">anthropic（Claude）</option>
            <option value="ollama">ollama（本地）</option>
          </select></div>
      </div>
      <div className="field"><label>Base URL</label>
        <input value={p.base_url ?? ''} placeholder={placeholder}
          onChange={(e) => onChange({ base_url: e.target.value })} /></div>
      <div className="field"><label>API Key{p.type === 'ollama' && '（本地通常留空）'}</label>
        <input type="password" value={p.api_key ?? ''} placeholder={p.type === 'ollama' ? '留空' : 'sk-...'}
          onChange={(e) => onChange({ api_key: e.target.value })} /></div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button className="btn ghost sm" disabled={testing || !p.base_url} onClick={() => run()}>
          {testing ? '测试中…' : '🔌 测试连接 / 拉取模型'}
        </button>
        {result?.ok && result.model_count > 0 && (
          <>
            <select value={speedModel} onChange={(e) => setSpeedModel(e.target.value)} style={{ maxWidth: 220 }}>
              {result.models.map((m: any) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <button className="btn ghost sm" disabled={testing || !speedModel} onClick={() => run(speedModel)}>⚡ 测速</button>
          </>
        )}
        <button className="btn danger sm" onClick={onRemove} style={{ marginLeft: 'auto' }}>删除</button>
      </div>

      {result && (
        <div className="hint" style={{ marginTop: 8 }}>
          {result.ok ? (
            <div>
              <span style={{ color: 'var(--green)' }}>✓ 连接成功 · 延迟 {result.connect_ms}ms</span>
              {result.model_count !== undefined && <> · 拉到 {result.model_count} 个模型</>}
              {result.has_error_models && <span style={{ color: 'var(--amber)' }}> · 部分模型获取异常（回退列表，检查 key）</span>}
              {result.chat_ms !== undefined && <> · <span style={{ color: 'var(--green)' }}>生成 {result.chat_ms}ms</span> 回复：{result.sample}</>}
              {result.chat_error && <span style={{ color: 'var(--red)' }}> · 生成失败：{result.chat_error}</span>}
              {result.ok && result.models?.length > 0 && (
                <details style={{ marginTop: 4 }}>
                  <summary>模型列表（{result.models.length}）</summary>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                    {result.models.map((m: any) => <span key={m.id} className="tag">{m.name}</span>)}
                  </div>
                </details>
              )}
            </div>
          ) : (
            <span style={{ color: 'var(--red)' }}>✗ {result.error}</span>
          )}
        </div>
      )}
    </div>
  )
}
