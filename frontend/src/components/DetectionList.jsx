import { percent, prettyDefect } from '../lib/format.js'

export default function DetectionList({ detections, selectedId, onSelect }) {
  if (detections.length === 0) {
    return <p className="rounded-lg border border-dashed border-line p-6 text-center text-sm text-mute">No detections above the reporting threshold.</p>
  }
  return (
    <ul className="space-y-2">
      {detections.map((det) => {
        const active = det.id === selectedId
        const b = det.bounding_box
        return (
          <li key={det.id}>
            <button
              onClick={() => onSelect(active ? null : det.id)}
              aria-pressed={active}
              className={`w-full rounded-xl border p-4 text-left transition-colors ${
                active ? 'border-amber/60 bg-amber/5' : 'border-line bg-ink-900 hover:border-slate-soft/40'
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium">
                  <span className="mr-2 text-dim">#{det.id}</span>
                  {prettyDefect(det.defect)}
                </p>
                <p className="text-sm font-semibold">{percent(det.confidence)}</p>
              </div>
              <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-ink-700" aria-hidden="true">
                <div className="h-full rounded-full bg-cyan" style={{ width: `${det.confidence * 100}%` }} />
              </div>
              <p className="mt-2.5 text-xs text-mute">
                Bounding box (px): x1 {b.x1.toFixed(0)}, y1 {b.y1.toFixed(0)}, x2 {b.x2.toFixed(0)}, y2 {b.y2.toFixed(0)}
              </p>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
