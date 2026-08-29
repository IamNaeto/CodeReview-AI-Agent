import { useState, useEffect } from 'react'
import Toast from './Toast'

let toastListeners = []
let toastId = 0

export function showToast(message, type = 'error', duration = 5000) {
  const id = ++toastId
  toastListeners.forEach(listener => listener({ id, message, type, duration }))
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    const addToast = (toast) => {
      setToasts(prev => [...prev, toast])
    }
    toastListeners.push(addToast)
    return () => {
      toastListeners = toastListeners.filter(l => l !== addToast)
    }
  }, [])

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  if (toasts.length === 0) return null

  return (
    <div className="toast-container">
      {toasts.map(t => (
        <Toast
          key={t.id}
          message={t.message}
          type={t.type}
          duration={t.duration}
          onClose={() => removeToast(t.id)}
        />
      ))}
    </div>
  )
}
