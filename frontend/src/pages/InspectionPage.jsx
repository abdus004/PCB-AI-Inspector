import { Camera, Replace, ScanSearch, Trash2, Upload } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { AppHeader } from '../components/Header.jsx'
import CameraCapture from '../components/CameraCapture.jsx'
import HistoryList from '../components/HistoryList.jsx'
import UploadZone from '../components/UploadZone.jsx'
import { Button, ConfirmDialog, ErrorBanner, Spinner } from '../components/ui.jsx'
import { ACCEPT, validateImageFile } from '../lib/imageValidation.js'
import { formatBytes } from '../lib/format.js'
import { navigate } from '../lib/router.js'
import { deleteInspection, inspectImage, listInspections } from '../services/api.js'

const HISTORY_LIMIT = 8

export default function InspectionPage() {
  const [mode, setMode] = useState('upload')           // 'upload' | 'camera'
  const [selected, setSelected] = useState(null)       // { file, previewUrl, info }
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const submittingRef = useRef(false)                  // blocks double submissions
  const replaceInput = useRef(null)

  const [history, setHistory] = useState({ loading: true, error: '', items: [], total: 0 })
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)

  // ---- history -----------------------------------------------------------
  const loadHistory = useCallback(() => {
    return listInspections(HISTORY_LIMIT)
      .then((data) => setHistory({ loading: false, error: '', items: data.items, total: data.total }))
      .catch((err) => setHistory({ loading: false, error: err.message, items: [], total: 0 }))
  }, [])

  useEffect(() => {
    let active = true
    listInspections(HISTORY_LIMIT)
      .then((data) => active && setHistory({ loading: false, error: '', items: data.items, total: data.total }))
      .catch((err) => active && setHistory({ loading: false, error: err.message, items: [], total: 0 }))
    return () => { active = false }
  }, [])

  const retryHistory = () => {
    setHistory((h) => ({ ...h, loading: true, error: '' }))
    loadHistory()
  }

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      await deleteInspection(toDelete.inspection_id)
      setToDelete(null)
      await loadHistory()
    } catch (err) {
      setToDelete(null)
      setError(err.message)
    } finally {
      setDeleting(false)
    }
  }

  // ---- image selection -----------------------------------------------------
  useEffect(() => {
    const url = selected?.previewUrl
    return () => { if (url) URL.revokeObjectURL(url) }
  }, [selected])

  const handleFile = async (file) => {
    setError('')
    const result = await validateImageFile(file)
    if (!result.ok) { setError(result.error); return }
    setSelected({ file, previewUrl: URL.createObjectURL(file), info: result.info })
    setMode('upload')
  }

  const removeImage = () => { setSelected(null); setError('') }

  // ---- run the inspection ------------------------------------------------------
  const runInspection = async () => {
    if (!selected || submittingRef.current) return
    submittingRef.current = true
    setSubmitting(true)
    setError('')
    try {
      const result = await inspectImage(selected.file)
      navigate(`/results/${result.inspection_id}`)
    } catch (err) {
      setError(err.message)
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-3xl px-5 py-10 sm:py-14">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Inspect Your PCB</h1>
        <p className="mt-3 text-mute">Add a clear, well-lit photo of the board. The AI will check it for the six supported defect types.</p>

        <div className="mt-8 space-y-4">
          <ErrorBanner message={error} onDismiss={() => setError('')} />

          <div className="relative rounded-2xl border border-line bg-ink-850 p-4 sm:p-6">
            {!selected && (
              <>
                <div className="mb-5 grid grid-cols-2 gap-1 rounded-lg bg-ink-900 p-1" role="tablist" aria-label="Image source">
                  {[
                    { id: 'upload', label: 'Upload Image', Icon: Upload },
                    { id: 'camera', label: 'Open Camera', Icon: Camera },
                  ].map(({ id, label, Icon }) => (
                    <button
                      key={id}
                      role="tab"
                      aria-selected={mode === id}
                      onClick={() => setMode(id)}
                      className={`flex items-center justify-center gap-2 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                        mode === id ? 'bg-ink-700 text-fg' : 'text-mute hover:text-fg'
                      }`}
                    >
                      <Icon className="h-4 w-4" aria-hidden="true" /> {label}
                    </button>
                  ))}
                </div>

                {mode === 'upload' ? (
                  <UploadZone
                    onFile={handleFile}
                    onMultiple={() => setError('Please add one image at a time.')}
                  />
                ) : (
                  <CameraCapture onUse={handleFile} onCancel={() => setMode('upload')} />
                )}
              </>
            )}

            {selected && (
              <div>
                <div className="overflow-hidden rounded-xl border border-line bg-black">
                  <img src={selected.previewUrl} alt="Selected PCB preview" className="mx-auto max-h-[28rem] w-full object-contain" />
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
                  <div className="col-span-2">
                    <dt className="text-xs text-dim">Filename</dt>
                    <dd className="truncate font-medium" title={selected.file.name}>{selected.file.name}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-dim">Dimensions</dt>
                    <dd>{selected.info.width} × {selected.info.height} px</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-dim">Size · Format</dt>
                    <dd>{formatBytes(selected.file.size)} · {selected.info.format}</dd>
                  </div>
                </dl>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => replaceInput.current?.click()} disabled={submitting}>
                    <Replace className="h-4 w-4" /> Replace
                  </Button>
                  <Button variant="ghost" onClick={removeImage} disabled={submitting}>
                    <Trash2 className="h-4 w-4" /> Remove
                  </Button>
                  <input
                    ref={replaceInput}
                    type="file"
                    accept={ACCEPT}
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      e.target.value = ''
                      if (file) handleFile(file)
                    }}
                  />
                </div>
                <Button onClick={runInspection} disabled={submitting} className="mt-6 w-full !py-3.5 text-base">
                  {submitting ? <><Spinner className="h-5 w-5" /> Analysing PCB…</> : <><ScanSearch className="h-5 w-5" /> Inspect PCB</>}
                </Button>
                {submitting && (
                  <p className="mt-3 text-center text-sm text-mute" role="status">
                    Running the YOLO model. This can take a few seconds, please keep this page open.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        <HistoryList state={history} onRetry={retryHistory} onDelete={setToDelete} />
      </main>

      {toDelete && (
        <ConfirmDialog
          title="Delete this inspection?"
          message={`${toDelete.filename} (${toDelete.inspection_id}) and its saved images will be permanently removed. This cannot be undone.`}
          confirmLabel="Delete"
          busy={deleting}
          onConfirm={confirmDelete}
          onCancel={() => setToDelete(null)}
        />
      )}
    </div>
  )
}
