import { Routes, Route, Link, useLocation } from 'react-router-dom'
import ReviewForm from './components/ReviewForm'
import ReviewList from './components/ReviewList'
import ReviewDetail from './components/ReviewDetail'
import ToastContainer from './components/ToastContainer'

function Sidebar() {
  const loc = useLocation()

  const navItems = [
    { path: '/', label: 'New Review', icon: '⚡' },
    { path: '/history', label: 'Review History', icon: '📋' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon">🔍</div>
          <span>CodeReview AI</span>
        </div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map(item => (
          <Link
            key={item.path}
            to={item.path}
            className={`sidebar-nav-item ${loc.pathname === item.path ? 'active' : ''}`}
          >
            <span style={{ fontSize: 16 }}>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-footer">
        Agentic AI Code Review v1.0
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<ReviewForm />} />
          <Route path="/history" element={<ReviewList />} />
          <Route path="/review/:id" element={<ReviewDetail />} />
        </Routes>
      </main>
      <ToastContainer />
    </div>
  )
}
