import { History, ImageOff, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { absoluteUrl } from '../services/api.js'
import { formatShortDateTime, prettyDefect } from '../lib/format.js'
import Link from '../components/Link.jsx'
import { Button, ErrorBanner, Spinner, StatusBadge } from './ui.jsx'

function Thumbnail({ src }) {
  const [failed, setFailed] = useState(false)
  const size = 'h-14 w-14 shrink-0 rounded-lg border border-line bg-ink-900 sm:h-16 sm:w-16'
  if (failed) {
    return (
      <div className={`${size} flex items-center justify-center text-dim`} title="Image file missing">
        <ImageOff className="h-5 w-5" aria-hidden="true" />
      </div>
    )
  }
  return <img src={src} alt="" loading="lazy" onError={() => setFailed(true)} className={`${size} object-cover`} />
}

export default function HistoryList({ state, onRetry, onDelete }) {
  const { loading, error, items, total } = state
  return (
    <section aria-labelledby="history-title" className="mt-14">
      <div className="flex items-end justify-between">
        <h2 id="history-title" className="flex items-center gap-2 text-lg font-semibold">
          <History className="h-5 w-5 text-cyan" aria-hidden="true" />
          Recent Inspection History
        </h2>
        {!loading && !error && total > items.length && (
          <p className="text-xs text-dim">Showing latest {items.length} of {total}</p>
        )}
      </div>

      <div className="mt-4">
        {loading && (
          <div className="flex items-center gap-2 rounded-xl border border-line bg-ink-850 p-6 text-sm text-mute">
            <Spinner /> Loading history…
          </div>
        )}
        {!loading && error && (
          <ErrorBanner message={error} action={<Button variant="secondary" className="!py-1.5" onClick={onRetry}>Retry</Button>} />
        )}
        {!loading && !error && items.length === 0 && (
          <p className="rounded-xl border border-dashed border-line p-8 text-center text-sm text-mute">
            No inspections yet. Your completed inspections will appear here.
          </p>
        )}
        {!loading && !error && items.length > 0 && (
          <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-ink-850">
            {items.map((item) => (
              <li key={item.inspection_id} className="flex items-center gap-3 p-3 sm:gap-4 sm:p-4">
                <Link to={`/results/${item.inspection_id}`} className="flex min-w-0 flex-1 items-center gap-3 rounded-lg sm:gap-4" aria-label={`Open inspection ${item.inspection_id}`}>
                  <Thumbnail src={absoluteUrl(item.urls.thumbnail)} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{item.filename}</p>
                    <p className="mt-0.5 text-xs text-dim">
                      {item.inspection_id} · {formatShortDateTime(item.created_at)}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
                      <StatusBadge status={item.status} label={item.conclusion.label} />
                      {item.total_detections > 0 && (
                        <span className="text-xs text-mute">
                          {item.total_detections} detection{item.total_detections === 1 ? '' : 's'}: {item.defects.map(prettyDefect).join(', ')}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
                <button
                  onClick={() => onDelete(item)}
                  aria-label={`Delete inspection ${item.inspection_id}`}
                  className="rounded-lg p-2.5 text-dim transition-colors hover:bg-rose-400/10 hover:text-rose-300"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
