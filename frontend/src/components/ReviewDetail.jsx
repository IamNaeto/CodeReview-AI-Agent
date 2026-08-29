import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'
import AgentActivity from './AgentActivity'
import { showToast } from './ToastContainer'

export default function ReviewDetail() {
  const { id } = useParams()
  const nav = useNavigate()
  const [review, setReview] = useState(null)
  const [status, setStatus] = useState(null)
  const [filter, setFilter] = useState({ severity: 'all', category: 'all' })
  const [expanded, setExpanded] = useState({})
  const [error, setError] = useState(null)

  const fetchData = async () => {
    try {
      const [r, s] = await Promise.all([
        axios.get(`/api/v1/reviews/${id}`),
        axios.get(`/api/v1/reviews/${id}/status`)
      ])
      setReview(r.data)
      setStatus(s.data)
      setError(null)
    } catch (err) {
      setError('Failed to load review')
      showToast('Failed to load review details', 'error')
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [id])

  const copySummary = async () => {
    if (!review?.summary) return
    try {
      await navigator.clipboard.writeText(review.summary)
      showToast('Review summary copied to clipboard', 'success', 2000)
    } catch {
      showToast('Unable to copy summary', 'error', 2000)
    }
  }

  const findings = review?.findings || []
  const filtered = useMemo(() => {
    return findings.filter(f => {
      if (filter.severity !== 'all' && f.severity !== filter.severity) return false
      if (filter.category !== 'all' && f.category !== filter.category) return false
      return true
    })
  }, [findings, filter])

  const categories = [...new Set(findings.map(f => f.category))].sort()
  const severities = ['critical', 'high', 'medium', 'low', 'optional']
  const sevCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0, optional: 0 }
    findings.forEach(f => {
      if (counts[f.severity] !== undefined) {
        counts[f.severity] += 1
      }
    })
    return counts
  }, [findings])
  const totalFindings = findings.length

  if (error) {
    return (
      <div>
        <div className="main-header">
          <h1>Error</h1>
        </div>
        <div className="page-content">
          <div className="alert alert-error">{error}</div>
          <button className="btn btn-primary" onClick={() => nav('/history')}>
            Back to History
          </button>
        </div>
      </div>
    )
  }

  if (!review) {
    return (
      <div>
        <div className="main-header"><h1>Loading...</h1></div>
        <div className="page-content">
          <div className="skeleton" style={{ height: 100, marginBottom: 12 }}></div>
          <div className="skeleton" style={{ height: 250 }}></div>
        </div>
      </div>
    )
  }

  const getRecClass = (r) => {
    if (r === 'BLOCK MERGE') return 'block'
    if (r === 'REQUEST CHANGES') return 'request'
    if (r === 'APPROVE WITH COMMENTS') return 'comment'
    return 'approve'
  }

  const getRecIcon = (r) => {
    if (r === 'BLOCK MERGE') return '🚫'
    if (r === 'REQUEST CHANGES') return '⚠️'
    if (r === 'APPROVE WITH COMMENTS') return '💬'
    return '✅'
  }

  const getRecText = (r) => {
    if (r === 'BLOCK MERGE') return 'Block Merge — Critical issues must be resolved'
    if (r === 'REQUEST CHANGES') return 'Request Changes — High priority issues found'
    if (r === 'APPROVE WITH COMMENTS') return 'Approve with Comments — Issues to address'
    return 'Approve — No significant issues found'
  }

  const totalBar = totalFindings || 1
  const sevColors = {
    critical: 'var(--critical)',
    high: 'var(--high)',
    medium: 'var(--medium)',
    low: 'var(--low)',
    optional: 'var(--optional)'
  }

  return (
    <div>
      <div className="main-header">
        <div>
          <h1>Review #{review.id}</h1>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
            {review.repo_url || review.commit_sha || 'Raw Diff'} · {new Date(review.created_at).toLocaleString()}
          </div>
        </div>
        <div className="action-row compact">
          <button className="btn btn-secondary btn-sm" onClick={() => nav('/history')}>
            ← Back
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => nav('/')}>
            ⚡ New Review
          </button>
          {review.summary && (
            <button className="btn btn-ghost btn-sm" onClick={copySummary}>
              Copy Summary
            </button>
          )}
        </div>
      </div>

      <div className="page-content">
        <div className="animate-fade-in">
          {review.status === 'running' && (
            <AgentActivity activities={review.agent_activities} progress={status?.progress} />
          )}

          {review.status === 'failed' && (
            <div className="alert alert-error" style={{ marginBottom: 16 }}>
              <span>❌</span> Review failed: {review.summary}
            </div>
          )}

          {review.overall_recommendation && (
            <div className={`recommendation-banner ${getRecClass(review.overall_recommendation)} animate-fade-in`}>
              <span className="recommendation-icon">{getRecIcon(review.overall_recommendation)}</span>
              <div>
                <div className="recommendation-text">{review.overall_recommendation}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                  {getRecText(review.overall_recommendation)}
                </div>
              </div>
            </div>
          )}
        </div>

        {totalFindings > 0 && (
          <div className="stats-grid animate-fade-in stagger-1">
            <div className="stat-card">
              <div className="stat-label">Total Findings</div>
              <div className="stat-value">{totalFindings}</div>
              <div className="severity-bar">
                {severities.map(s => sevCounts[s] > 0 && (
                  <div 
                    key={s} 
                    className="severity-bar-segment"
                    style={{ 
                      width: `${(sevCounts[s] / totalBar) * 100}%`, 
                      background: sevColors[s] 
                    }}
                  />
                ))}
              </div>
            </div>
            {severities.map(s => (
              <div key={s} className="stat-card" style={{ animationDelay: `${severities.indexOf(s) * 0.05}s` }}>
                <div className="stat-label" style={{ color: sevColors[s] }}>{s}</div>
                <div className="stat-value" style={{ color: sevColors[s], fontSize: 24 }}>{sevCounts[s] || 0}</div>
              </div>
            ))}
          </div>
        )}

        {review.summary && (
          <div className="card animate-fade-in stagger-2" style={{ marginBottom: 20 }}>
            <div className="card-header">
              <div className="card-title">📊 Review Summary</div>
            </div>
            <pre style={{ 
              whiteSpace: 'pre-wrap', 
              fontFamily: 'inherit', 
              fontSize: 13, 
              color: 'var(--text)',
              lineHeight: 1.7
            }}>
              {review.summary}
            </pre>
          </div>
        )}

        <div className="card animate-fade-in stagger-3">
          <div className="card-header">
            <div>
              <div className="card-title">🔍 Findings</div>
              <div className="card-subtitle">
                {filtered.length} of {totalFindings} finding{totalFindings !== 1 ? 's' : ''} shown
              </div>
            </div>
            <div className="action-row compact">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setExpanded((prev) => {
                  const next = {}
                  filtered.forEach((_, index) => next[index] = true)
                  return next
                })}
              >
                Expand All
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setExpanded({})}
              >
                Collapse All
              </button>
            </div>
          </div>

          <div className="filter-bar">
            <label>Severity</label>
            <select 
              className="form-select" 
              style={{ width: 'auto', minWidth: 130 }}
              value={filter.severity} 
              onChange={e => setFilter(f => ({ ...f, severity: e.target.value }))}
            >
              <option value="all">All Severities</option>
              {severities.map(s => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)} ({sevCounts[s] || 0})
                </option>
              ))}
            </select>

            <label style={{ marginLeft: 10 }}>Category</label>
            <select 
              className="form-select" 
              style={{ width: 'auto', minWidth: 150 }}
              value={filter.category} 
              onChange={e => setFilter(f => ({ ...f, category: e.target.value }))}
            >
              <option value="all">All Categories</option>
              {categories.map(c => (
                <option key={c} value={c}>
                  {c.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </option>
              ))}
            </select>

            {(filter.severity !== 'all' || filter.category !== 'all') && (
              <button 
                className="btn btn-ghost btn-sm" 
                onClick={() => setFilter({ severity: 'all', category: 'all' })}
              >
                Clear
              </button>
            )}
          </div>

          {filtered.length === 0 && totalFindings > 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">🔍</div>
              <div className="empty-state-title">No Matching Findings</div>
              <div className="empty-state-desc">Try adjusting your filters to see more results.</div>
            </div>
          )}

          {totalFindings === 0 && review.status === 'completed' && (
            <div className="empty-state">
              <div className="empty-state-icon">🎉</div>
              <div className="empty-state-title">No Issues Found</div>
              <div className="empty-state-desc">The specialist agents did not identify any issues in this review.</div>
            </div>
          )}

          {filtered.map((f, i) => {
            const isExpanded = expanded[i] ?? true

            return (
              <div 
                key={`${f.file_path}-${f.title}-${i}`} 
                className={`finding-card ${f.severity} animate-fade-in`}
                style={{ animationDelay: `${i * 0.03}s` }}
              >
                <div className="finding-header">
                  <div className="finding-title">{f.title}</div>
                  <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
                    <span className={`badge badge-${f.severity}`}>{f.severity}</span>
                    <span className="badge badge-status">{f.confidence} confidence</span>
                  </div>
                </div>

                <div className="finding-meta">
                  <div className="finding-meta-item">
                    <span>📄</span>
                    {f.file_path}{f.line_start ? `:${f.line_start}` : ''}
                  </div>
                  <div className="finding-meta-item">
                    <span>🏷️</span>
                    {f.category.replace(/_/g, ' ')}
                  </div>
                  <div className="finding-meta-item">
                    <span>🤖</span>
                    {f.agent_name}
                  </div>
                  {f.cross_validated && (
                    <div className="finding-meta-item" style={{ color: 'var(--success)' }}>
                      <span>✓</span>
                      Cross-validated
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  className="toggle-finding"
                  onClick={() => setExpanded(prev => ({ ...prev, [i]: !isExpanded }))}
                >
                  {isExpanded ? 'Hide Details' : 'Show Details'}
                </button>

                {isExpanded && (
                  <>
                    <div className="finding-section">
                      <div className="finding-section-title">Explanation</div>
                      <div className="finding-section-content">{f.explanation}</div>
                    </div>

                    <div className="finding-section">
                      <div className="finding-section-title">Impact</div>
                      <div className="finding-section-content">{f.impact}</div>
                    </div>

                    {f.recommended_fix && (
                      <div className="finding-section">
                        <div className="finding-section-title">Recommended Fix</div>
                        <div className="finding-fix">
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                            {f.recommended_fix}
                          </pre>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
