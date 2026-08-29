import { useEffect } from 'react'

export default function Toast({ message, type = 'error', onClose, duration = 5000 }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose()
    }, duration)
    return () => clearTimeout(timer)
  }, [duration, onClose])

  const icons = {
    error: '⚠️',
    success: '✅',
    info: 'ℹ️'
  }

  return (
    <div className={`toast toast-${type}`} onClick={onClose}>
      <span>{icons[type]}</span>
      <span style={{ flex: 1 }}>{message}</span>
      <span style={{ opacity: 0.5, fontSize: 11 }}>×</span>
    </div>
  )
}
