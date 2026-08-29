import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { showToast } from './ToastContainer'

export default function ReviewList() {
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const nav = useNavigate()

  useEffect(() => {
    axios.get('/api/v1/reviews?limit=50')
      .then(r => setReviews(r.data))
      .catch(err => {
        showToast('Failed to load review history', 'error')
      })
      .finally(() => setLoading(false))
  }, [])

  const recStyle = (r) => {
    const map = {
      'BLOCK MERGE': { text: 'var(--critical)', bg: 'var(--critical-bg)', border: 'var(--critical-border)' },
      'REQUEST CHANGES': { text: 'var(--high)', bg: 'var(--high-bg)', border: 'var(--high-border)' },
      'APPROVE WITH COMMENTS': { text: 'var(--medium)', bg: 'var(--medium-bg)', border: 'var(--medium-border)' },
      'APPROVE': { text: 'var(--success)', bg: 'var(--success-bg)', border: 'rgba(63, 185, 80, 0.3)' }
    }
    return map[r] || map['APPROVE']
  }

  const statusIcon = (s) => {
    if (s === 'completed') return '✅'
    if (s === 'running') return '⏳'
    if (s === 'failed') return '❌'
    return '⏸️'
  }

  const totalFindings = reviews.reduce((sum, r) => sum + (r.findings?.length || 0), 0)
  const completedCount = reviews.filter(r => r.status === 'completed').length
  const runningCount = reviews.filter(r => r.status === 'running').length

  return (
    <div>
      <div className="main-header">
        <h1>Review History</h1>
        <button className="btn btn-primary btn-sm" onClick={() => nav('/')}>
          <span>⚡</span> New Review
        </button>
      </div>

      <div className="page-content">
        <div className="stats-grid animate-fade-in">
          <div className="stat-card">
            <div className="stat-label">Total Reviews</div>
            <div className="stat-value">{reviews.length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Completed</div>
            <div className="stat-value" style={{ color: 'var(--success)' }}>{completedCount}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">In Progress</div>
            <div className="stat-value" style={{ color: runningCount > 0 ? 'var(--accent)' : 'var(--text-primary)' }}>{runningCount}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Total Findings</div>
            <div className="stat-value" style={{ color: 'var(--accent)' }}>{totalFindings}</div>
          </div>
        </div>

        <div className="card animate-fade-in stagger-1">
          <div className="card-header">
            <div>
              <div className="card-title">All Reviews</div>
              <div className="card-subtitle">
                {reviews.length === 0 ? 'No reviews yet' : `${reviews.length} review${reviews.length !== 1 ? 's' : ''} found`}
              </div>
            </div>
          </div>

          {loading && (
            <div style={{ padding: 32, textAlign: 'center' }}>
              <div className="skeleton" style={{ height: 52, marginBottom: 10 }}></div>
              <div className="skeleton" style={{ height: 52, marginBottom: 10 }}></div>
              <div className="skeleton" style={{ height: 52 }}></div>
            </div>
          )}

          {!loading && reviews.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <div className="empty-state-title">No Reviews Yet</div>
              <div className="empty-state-desc">
                Start your first code review by clicking "New Review" in the sidebar.
              </div>
              <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => nav('/')}>
                Start First Review
              </button>
            </div>
          )}

          {reviews.map((rev, i) => {
            const style = recStyle(rev.overall_recommendation)
            const sevCounts = rev.severity_counts || {}
            const total = rev.findings?.length || 0

            return (
              <div 
                key={rev.id} 
                className="review-item animate-fade-in"
                style={{ animationDelay: `${i * 0.04}s` }}
                onClick={() => nav(`/review/${rev.id}`)}
              >
                <div className="review-item-left">
                  <div className="review-item-title">
                    {statusIcon(rev.status)} Review #{rev.id}
                    {rev.repo_url && (
                      <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 8 }}>
                        {rev.repo_url.split('/').slice(-2).join('/')}
                      </span>
                    )}
                    {rev.pr_number && (
                      <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> PR #{rev.pr_number}</span>
                    )}
                    {rev.commit_sha && (
                      <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> {rev.commit_sha.slice(0, 7)}</span>
                    )}
                    {!rev.repo_url && !rev.commit_sha && (
                      <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> Raw Diff</span>
                    )}
                  </div>
                  <div className="review-item-meta">
                    <span>{new Date(rev.created_at).toLocaleString()}</span>
                    {total > 0 && (
                      <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        {sevCounts.critical > 0 && <span className="badge badge-critical">{sevCounts.critical} Critical</span>}
                        {sevCounts.high > 0 && <span className="badge badge-high">{sevCounts.high} High</span>}
                        {sevCounts.medium > 0 && <span className="badge badge-medium">{sevCounts.medium} Medium</span>}
                        {sevCounts.low > 0 && <span className="badge badge-low">{sevCounts.low} Low</span>}
                        {total > 0 && sevCounts.critical === 0 && sevCounts.high === 0 && sevCounts.medium === 0 && sevCounts.low === 0 && (
                          <span className="badge badge-optional">{total} Finding{total !== 1 ? 's' : ''}</span>
                        )}
                      </span>
                    )}
                  </div>
                </div>
                <div className="review-item-right">
                  {rev.overall_recommendation ? (
                    <span className="badge" style={{ 
                      background: style.bg, 
                      color: style.text, 
                      borderColor: style.border 
                    }}>
                      {rev.overall_recommendation}
                    </span>
                  ) : (
                    <span className="badge badge-status">{rev.status}</span>
                  )}
                  <span style={{ color: 'var(--text-muted)', fontSize: 16 }}>→</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
