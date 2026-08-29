export default function AgentActivity({ activities, progress }) {
  if (!activities || activities.length === 0) return null

  const statusConfig = {
    running: { icon: '⏳', label: 'Running', color: 'var(--accent)' },
    completed: { icon: '✅', label: 'Completed', color: 'var(--success)' },
    failed: { icon: '❌', label: 'Failed', color: 'var(--danger)' },
    pending: { icon: '⏸️', label: 'Pending', color: 'var(--text-muted)' }
  }

  const agentIcons = {
    'Correctness & Logic': '🧠',
    'Security': '🔒',
    'Architecture & Design': '🏗️',
    'Performance & Scalability': '⚡',
    'Code Quality & Maintainability': '✨',
    'Testing': '🧪'
  }

  return (
    <div className="card animate-fade-in" style={{ marginBottom: 20, borderColor: 'rgba(88, 166, 255, 0.2)' }}>
      <div className="card-header">
        <div>
          <div className="card-title">🤖 Agent Activity</div>
          <div className="card-subtitle">
            {activities.filter(a => a.status === 'completed').length} of {activities.length} agents completed
          </div>
        </div>
        {progress !== undefined && (
          <div style={{ 
            fontSize: 22, 
            fontWeight: 700, 
            color: 'var(--accent)',
            fontFamily: 'JetBrains Mono, monospace'
          }}>
            {Math.round(progress)}%
          </div>
        )}
      </div>

      <div className="progress-container" style={{ marginBottom: 16 }}>
        <div 
          className="progress-bar" 
          style={{ width: `${progress || 0}%` }}
        ></div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {activities.map(a => {
          const config = statusConfig[a.status] || statusConfig.pending
          return (
            <div key={a.id} className={`agent-activity-item ${a.status}`}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 18 }}>{agentIcons[a.agent_name] || '🔍'}</span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                    {a.agent_name}
                  </div>
                  <div style={{ fontSize: 11, color: config.color, fontWeight: 500, marginTop: 1 }}>
                    {config.icon} {config.label}
                    {a.findings_count > 0 && ` · ${a.findings_count} finding${a.findings_count !== 1 ? 's' : ''} found`}
                  </div>
                </div>
              </div>
              <div style={{ 
                width: 8, 
                height: 8, 
                borderRadius: '50%', 
                background: config.color,
                boxShadow: a.status === 'running' ? `0 0 6px ${config.color}` : 'none'
              }}></div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
