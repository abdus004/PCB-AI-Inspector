// Small shared UI pieces.
import { LoaderCircle, CircleAlert, X } from 'lucide-react'
import { useEffect } from 'react'
import { STATUS_STYLES } from '../lib/status.js'

export function Button({ variant = 'primary', className = '', children, ...props }) {
  const styles = {
    primary: 'bg-cyan text-ink-950 hover:bg-cyan-deep font-semibold',
    secondary: 'border border-line bg-ink-800 text-fg hover:bg-ink-700 font-medium',
    ghost: 'text-mute hover:text-fg hover:bg-ink-800 font-medium',
    danger: 'border border-rose-400/30 text-rose-300 hover:bg-rose-400/10 font-medium',
  }
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function Spinner({ className = 'h-4 w-4' }) {
  return <LoaderCircle className={`${className} animate-spin`} aria-hidden="true" />
}

export function ErrorBanner({ message, onDismiss, action }) {
  if (!message) return null
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-rose-400/30 bg-rose-400/10 p-3.5 text-sm text-rose-200">
      <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <p className="flex-1 leading-relaxed">{message}</p>
      {action}
      {onDismiss && (
        <button onClick={onDismiss} aria-label="Dismiss error" className="rounded p-0.5 hover:bg-rose-400/20">
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}

export function StatusBadge({ status, label }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.inconclusive
  const Icon = style.icon
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${style.text} ${style.bg} ${style.border}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {label}
    </span>
  )
}

export function ConfirmDialog({ title, message, confirmLabel, busy, onConfirm, onCancel }) {
  useEffect(() => {
    const onKey = (event) => event.key === 'Escape' && !busy && onCancel()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, onCancel])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className="w-full max-w-sm rounded-xl border border-line bg-ink-850 p-6 shadow-2xl">
        <h2 id="confirm-title" className="text-lg font-semibold">{title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-mute">{message}</p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel} disabled={busy}>Cancel</Button>
          <Button variant="danger" onClick={onConfirm} disabled={busy}>
            {busy && <Spinner />}
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
