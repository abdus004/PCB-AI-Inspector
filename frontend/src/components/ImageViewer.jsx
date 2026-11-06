import { Columns2, Download, ImageOff, Image as ImageIcon, RotateCcw, ScanSearch, ZoomIn, ZoomOut } from 'lucide-react'
import { useState } from 'react'
import { absoluteUrl, downloadFile } from '../services/api.js'
import { prettyDefect } from '../lib/format.js'
import { Button, ErrorBanner, Spinner } from './ui.jsx'

const MIN_ZOOM = 1
const MAX_ZOOM = 4
const MODES = [
  { id: 'side', label: 'Side by side', Icon: Columns2 },
  { id: 'original', label: 'Original', Icon: ImageIcon },
  { id: 'annotated', label: 'Annotated', Icon: ScanSearch },
]

function Panel({ title, src, alt, zoom, selected, image }) {
  const [failed, setFailed] = useState(false)
  const box = selected?.bounding_box
  return (
    <div className="min-w-0">
      <p className="mb-2 text-sm font-medium text-mute">{title}</p>
      <div className="max-h-[70vh] overflow-auto rounded-xl border border-line bg-black">
        {failed ? (
          <div className="flex aspect-[4/3] flex-col items-center justify-center gap-2 p-6 text-center text-sm text-mute" role="alert">
            <ImageOff className="h-6 w-6 text-dim" aria-hidden="true" />
            This image could not be loaded. The stored file may have been removed.
          </div>
        ) : (
        <div className="relative" style={{ width: `${zoom * 100}%` }}>
          <img src={src} alt={alt} className="block h-auto w-full" draggable={false} onError={() => setFailed(true)} />
          {box && (
            <svg
              className="pointer-events-none absolute inset-0 h-full w-full"
              viewBox={`0 0 ${image.width} ${image.height}`}
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <rect
                x={box.x1} y={box.y1} width={box.x2 - box.x1} height={box.y2 - box.y1}
                fill="rgb(242 176 76 / 0.12)" stroke="#f2b04c" strokeWidth="3" vectorEffect="non-scaling-stroke"
              />
            </svg>
          )}
        </div>
        )}
      </div>
    </div>
  )
}

export default function ImageViewer({ inspection, selected }) {
  const [mode, setMode] = useState('side')
  const [zoom, setZoom] = useState(1)
  const [downloading, setDownloading] = useState('')
  const [error, setError] = useState('')

  const id = inspection.inspection_id
  const original = absoluteUrl(inspection.urls.original)
  const annotated = absoluteUrl(inspection.urls.annotated)

  const download = async (kind) => {
    setDownloading(kind)
    setError('')
    try {
      await downloadFile(inspection.urls[kind], `${id}-${kind}.jpg`)
    } catch (err) {
      setError(err.message)
    } finally {
      setDownloading('')
    }
  }

  const zoomBy = (delta) => setZoom((z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, +(z + delta).toFixed(2))))

  return (
    <section aria-labelledby="compare-title" className="rounded-2xl border border-line bg-ink-850 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="compare-title" className="text-lg font-semibold">Image comparison</h2>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1 rounded-lg bg-ink-900 p-1" role="group" aria-label="View mode">
            {MODES.map(({ id: modeId, label, Icon }) => (
              <button
                key={modeId}
                onClick={() => setMode(modeId)}
                aria-pressed={mode === modeId}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${mode === modeId ? 'bg-ink-700 text-fg' : 'text-mute hover:text-fg'}`}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden="true" /> {label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1 rounded-lg bg-ink-900 p-1" role="group" aria-label="Zoom">
            <button onClick={() => zoomBy(-0.5)} disabled={zoom <= MIN_ZOOM} aria-label="Zoom out" className="rounded-md p-1.5 text-mute hover:text-fg disabled:opacity-40"><ZoomOut className="h-4 w-4" /></button>
            <span className="w-12 text-center text-xs text-mute" aria-live="polite">{Math.round(zoom * 100)}%</span>
            <button onClick={() => zoomBy(0.5)} disabled={zoom >= MAX_ZOOM} aria-label="Zoom in" className="rounded-md p-1.5 text-mute hover:text-fg disabled:opacity-40"><ZoomIn className="h-4 w-4" /></button>
            <button onClick={() => setZoom(1)} disabled={zoom === 1} aria-label="Reset zoom" className="rounded-md p-1.5 text-mute hover:text-fg disabled:opacity-40"><RotateCcw className="h-4 w-4" /></button>
          </div>
        </div>
      </div>

      <div className={`mt-4 grid gap-4 ${mode === 'side' ? 'lg:grid-cols-2' : ''}`}>
        {mode !== 'annotated' && (
          <Panel title="Original PCB image" src={original} alt="Original PCB" zoom={zoom} selected={selected} image={inspection.image} />
        )}
        {mode !== 'original' && (
          <Panel title="Annotated PCB image" src={annotated} alt="PCB with detected defects marked" zoom={zoom} selected={selected} image={inspection.image} />
        )}
      </div>

      {selected && (
        <p className="mt-3 text-xs text-amber">
          Highlighting detection {selected.id}: {prettyDefect(selected.defect)}
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => download('annotated')} disabled={Boolean(downloading)}>
          {downloading === 'annotated' ? <Spinner /> : <Download className="h-4 w-4" />} Download annotated image
        </Button>
        <Button variant="ghost" onClick={() => download('original')} disabled={Boolean(downloading)}>
          {downloading === 'original' ? <Spinner /> : <Download className="h-4 w-4" />} Original
        </Button>
      </div>
      {error && <div className="mt-3"><ErrorBanner message={error} onDismiss={() => setError('')} /></div>}
    </section>
  )
}
