import { useEffect, useState } from 'react'
import { api } from './api'

export function Settings() {
  const [settings, setSettings] = useState<any>(null)
  const [msg, setMsg] = useState('')

  useEffect(() => { api.getSettings().then(setSettings) }, [])

  if (!settings) return <div className="page">加载中…</div>

  const setProviders = (p: any[]) => setSettings({ ...settings, providers: p })
  const setBrowser = (k: string, v: any) => setSettings({ ...settings, browser: { ...settings.browser, [k]: v } })

  const save = async () => {
    await api.saveSettings(settings)
    await api.reloadProviders()
    setMsg('✅ 已保存并重新加载供应商')
    setTimeout(() => setMsg(''), 3000)
  }

  return (
    <div className="page">
      <h2>设置</h2>

      <div className="card">
        <h3>模型供应商</h3>
        <div className="hint" style={{ marginBottom: 12 }}>
          支持 OpenAI 兼容接口（OpenAI / DeepSeek / Moonshot / 智谱 / 硅基流动 等，填对应 base_url 与 api_key）；
          本地模型选 type=ollama，base_url 默认 http://localhost:11434。保存后会自动重新加载模型列表。
        </div>
        {settings.providers.map((p: any, i: number) => (
          <div key={i} className="card" style={{ background: 'var(--bg-2)', marginBottom: 10 }}>
            <div className="row">
              <div className="field"><label>显示名称</label>
                <input value={p.name} onChange={(e) => { const a = [...settings.providers]; a[i] = { ...p, name: e.target.value }; setProviders(a) }} /></div>
              <div className="field"><label>类型</label>
                <select value={p.type} onChange={(e) => { const a = [...settings.providers]; a[i] = { ...p, type: e.target.value }; setProviders(a) }}>
                  <option value="openai_compat">openai_compat（兼容接口）</option>
                  <option value="ollama">ollama（本地）</option>
                </select></div>
            </div>
            <div className="field"><label>Base URL</label>
              <input value={p.base_url} onChange={(e) => { const a = [...settings.providers]; a[i] = { ...p, base_url: e.target.value }; setProviders(a) }} /></div>
            <div className="field"><label>API Key{p.type === 'ollama' && '（本地通常留空）'}</label>
              <input type="password" value={p.api_key || ''} placeholder={p.type === 'ollama' ? '留空' : 'sk-...'}
                onChange={(e) => { const a = [...settings.providers]; a[i] = { ...p, api_key: e.target.value }; setProviders(a) }} /></div>
            <button className="btn danger sm" onClick={() => setProviders(settings.providers.filter((_: any, j: number) => j !== i))}>删除</button>
          </div>
        ))}
        <button className="btn ghost sm" onClick={() => setProviders([...settings.providers, { type: 'openai_compat', name: '新供应商', base_url: '', api_key: '' }])}>+ 添加供应商</button>
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
