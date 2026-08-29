import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { showToast } from './ToastContainer'

const presetScenarios = [
  {
    id: 'sql-injection',
    label: 'SQL Injection',
    description: 'Classic user-controlled query construction',
    content: `import sqlite3

def get_user_by_username(username):
    conn = sqlite3.connect('app.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchone()

def authenticate(username, password):
    user = get_user_by_username(username)
    if user and user[2] == password:
        return True
    return False`
  },
  {
    id: 'memory',
    label: 'Performance Issue',
    description: 'Quadratic loop inside a hot path',
    content: `def find_duplicates(items):
    seen = []
    duplicates = []
    for item in items:
        for existing in seen:
            if existing == item:
                duplicates.append(item)
                break
        seen.append(item)
    return duplicates`
  },
  {
    id: 'logic',
    label: 'Logic Bug',
    description: 'Wrong branch condition and missing validation',
    content: `def process_order(total, shipping_cost):
    if total > 100:
        discount = 0.1
    else:
        discount = 0.05

    if shipping_cost is None:
        shipping_cost = 0

    final_total = total - (total * discount) + shipping_cost
    return final_total`
  }
]

export default function ReviewForm() {
  const [mode, setMode] = useState('diff')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    repo_url: '',
    pr_number: '',
    commit_sha: '',
    diff_content: '',
    local_path: '',
    branch: '',
    custom_rules: ''
  })
  const [configValid, setConfigValid] = useState(true)
  const [configErrors, setConfigErrors] = useState([])
  const [configDebug, setConfigDebug] = useState(null)
  const nav = useNavigate()

  useEffect(() => {
    axios.get('/config-status')
      .then(r => {
        setConfigValid(r.data.valid)
        setConfigErrors(r.data.errors || [])
        setConfigDebug(r.data.debug || null)
        if (!r.data.valid) {
          showToast('Server configuration error — check API key', 'error', 10000)
        }
      })
      .catch(() => {
        showToast('Cannot connect to backend — is it running on port 8000?', 'error', 10000)
      })
  }, [])

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const loadPreset = (scenario) => {
    setMode('diff')
    setForm(f => ({ ...f, diff_content: scenario.content, custom_rules: '' }))
    showToast(`Loaded sample: ${scenario.label}`, 'success', 2000)
  }

  const clearForm = () => {
    setForm({
      repo_url: '',
      pr_number: '',
      commit_sha: '',
      diff_content: '',
      local_path: '',
      branch: '',
      custom_rules: ''
    })
    setMode('diff')
  }

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload = {}
      if (form.repo_url.trim()) payload.repo_url = form.repo_url.trim()
      if (form.commit_sha.trim()) payload.commit_sha = form.commit_sha.trim()
      if (form.diff_content.trim()) payload.diff_content = form.diff_content.trim()
      if (form.local_path.trim()) payload.local_path = form.local_path.trim()
      if (form.branch.trim()) payload.branch = form.branch.trim()
      if (form.custom_rules.trim()) payload.custom_rules = form.custom_rules.trim()
      if (form.pr_number && form.pr_number !== '') {
        payload.pr_number = parseInt(form.pr_number)
      }

      const res = await axios.post('/api/v1/reviews/start', payload)
      showToast('Review started successfully', 'success', 3000)
      nav(`/review/${res.data.review_id}`)
    } catch (err) {
      console.error(err)
      const status = err.response?.status
      const data = err.response?.data

      if (status === 503 && data?.detail?.errors) {
        const errors = data.detail.errors.join('; ')
        showToast(`Config Error: ${errors}`, 'error', 10000)
      } else {
        const msg = data?.detail?.message || data?.detail || err.message || 'Failed to start review'
        showToast(msg, 'error')
      }
    } finally {
      setLoading(false)
    }
  }

  const modes = [
    { id: 'diff', label: 'Raw Diff', icon: '📝', desc: 'Paste a git diff or patch' },
    { id: 'pr', label: 'GitHub PR', icon: '🔀', desc: 'Review a pull request' },
    { id: 'commit', label: 'Commit', icon: '💾', desc: 'Review a specific commit' },
    { id: 'local', label: 'Local Repo', icon: '📁', desc: 'Review local changes' },
  ]

  return (
    <div>
      <div className="main-header">
        <h1>New Code Review</h1>
        <div className="status-indicator">
          <span className="status-dot" style={{ background: configValid ? 'var(--success)' : 'var(--danger)' }}></span>
          <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
            {configValid ? 'System Ready' : 'Config Error'}
          </span>
        </div>
      </div>

      <div className="page-content">
        {!configValid && (
          <div className="alert alert-error animate-fade-in">
            <div>
              <strong>Configuration Error</strong>
              <div style={{ marginTop: 4 }}>
                {configErrors.map((err, i) => (
                  <div key={i}>• {err}</div>
                ))}
              </div>
              {configDebug && (
                <div style={{ marginTop: 10, padding: 10, background: 'var(--bg)', borderRadius: 'var(--radius-md)', fontSize: 12 }}>
                  <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>Debug Info:</div>
                  <div>Key set: {configDebug.key_set ? 'Yes' : 'No'}</div>
                  <div>Key length: {configDebug.key_length} chars</div>
                  <div>Key prefix: {configDebug.key_prefix}</div>
                  <div>Model: {configDebug.model}</div>
                  <div>.env loaded from: {configDebug.env_loaded_from || 'NOT FOUND'}</div>
                </div>
              )}
              <div style={{ marginTop: 8, fontSize: 12, opacity: 0.8 }}>
                <strong>Fix:</strong> Create a file named <code>.env</code> inside the <code>backend/</code> folder with:<br/>
                <code style={{ background: 'var(--bg)', padding: '2px 6px', borderRadius: 4 }}>OPENROUTER_API_KEY=sk-or-v1-your-real-key</code>
              </div>
            </div>
          </div>
        )}

        <div className="card animate-fade-in">
          <div className="card-header">
            <div>
              <div className="card-title">Select Review Type</div>
              <div className="card-subtitle">Choose how you want to submit code for review</div>
            </div>
          </div>

          <div className="radio-group">
            {modes.map(m => (
              <div key={m.id} className="radio-option">
                <input 
                  type="radio" 
                  name="mode" 
                  id={`mode-${m.id}`}
                  checked={mode === m.id} 
                  onChange={() => setMode(m.id)} 
                />
                <label htmlFor={`mode-${m.id}`}>
                  <span style={{ fontSize: 16 }}>{m.icon}</span>
                  <div>
                    <div style={{ fontWeight: 600 }}>{m.label}</div>
                    <div style={{ fontSize: 11, opacity: 0.7, fontWeight: 400 }}>{m.desc}</div>
                  </div>
                </label>
              </div>
            ))}
          </div>
        </div>

        {mode === 'diff' && (
          <div className="card animate-fade-in stagger-1">
            <div className="card-header">
              <div>
                <div className="card-title">Quick Sample Scenarios</div>
                <div className="card-subtitle">Load a realistic example to test the review workflow</div>
              </div>
            </div>
            <div className="preset-grid">
              {presetScenarios.map((scenario) => (
                <button
                  key={scenario.id}
                  type="button"
                  className="preset-card"
                  onClick={() => loadPreset(scenario)}
                >
                  <div className="preset-title">{scenario.label}</div>
                  <div className="preset-desc">{scenario.description}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="card animate-fade-in stagger-1">
          <div className="card-header">
            <div>
              <div className="card-title">Review Details</div>
              <div className="card-subtitle">Provide the code or repository information</div>
            </div>
          </div>

          <form onSubmit={submit}>
            {mode === 'diff' && (
              <div className="form-group">
                <label className="form-label">Code Diff / Patch Content</label>
                <textarea
                  className="form-textarea"
                  placeholder="Paste your git diff, patch file content, or raw code here..."
                  value={form.diff_content}
                  onChange={e => update('diff_content', e.target.value)}
                  required
                  spellCheck={false}
                />
                <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  You can paste raw Python/JavaScript code — the system will detect and review it.
                </p>
              </div>
            )}

            {mode === 'pr' && (
              <>
                <div className="form-group">
                  <label className="form-label">Repository URL</label>
                  <input className="form-input" placeholder="https://github.com/owner/repo.git" value={form.repo_url} onChange={e => update('repo_url', e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Pull Request Number</label>
                  <input className="form-input" placeholder="42" type="number" value={form.pr_number} onChange={e => update('pr_number', e.target.value)} required />
                </div>
              </>
            )}

            {mode === 'commit' && (
              <>
                <div className="form-group">
                  <label className="form-label">Repository URL</label>
                  <input className="form-input" placeholder="https://github.com/owner/repo.git" value={form.repo_url} onChange={e => update('repo_url', e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Commit SHA</label>
                  <input className="form-input" placeholder="abc123..." value={form.commit_sha} onChange={e => update('commit_sha', e.target.value)} required />
                </div>
              </>
            )}

            {mode === 'local' && (
              <>
                <div className="form-group">
                  <label className="form-label">Local Repository Path</label>
                  <input className="form-input" placeholder="C:\\path\\to\\repo or /home/user/repo" value={form.local_path} onChange={e => update('local_path', e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Target Branch / Ref (optional)</label>
                  <input className="form-input" placeholder="HEAD" value={form.branch} onChange={e => update('branch', e.target.value)} />
                </div>
              </>
            )}

            <div className="form-group">
              <label className="form-label">Custom Rules / Standards (optional)</label>
              <textarea className="form-textarea" placeholder="Enter any repository-specific coding standards..." value={form.custom_rules} onChange={e => update('custom_rules', e.target.value)} style={{ minHeight: 80 }} />
            </div>

            <div className="action-row">
              <button type="submit" className="btn btn-primary" disabled={loading || !configValid}>
                {loading ? (
                  <><span className="status-dot" style={{ background: 'var(--accent)', marginRight: 6 }}></span>Starting...</>
                ) : (
                  <><span>🚀</span> Start Code Review</>
                )}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => nav('/history')}>
                View History
              </button>
              <button type="button" className="btn btn-ghost" onClick={clearForm}>
                Clear
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
