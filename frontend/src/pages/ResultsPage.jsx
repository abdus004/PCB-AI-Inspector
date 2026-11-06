import { ArrowLeft, FileText, Info } from 'lucide-react'
import { useEffect, useState } from 'react'
import { AppHeader } from '../components/Header.jsx'
import DetectionList from '../components/DetectionList.jsx'
import ImageViewer from '../components/ImageViewer.jsx'
import { Button, ErrorBanner, Spinner } from '../components/ui.jsx'
import { STATUS_STYLES } from '../lib/status.js'
import { formatBytes, formatDateTime, percent, prettyDefect } from '../lib/format.js'
import Link from '../components/Link.jsx'
import { downloadFile, getInspection } from '../services/api.js'

function InfoItem({ label, value }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-dim">{label}</dt>
      <dd className="mt-0.5 truncate text-sm font-medium" title={String(value)}>{value}</dd>
    </div>
  )
}

export default function ResultsPage({ inspectionId }) {
  const [state, setState] = useState({ loading: true, error: '', notFound: false, data: null })
  const [selectedId, setSelectedId] = useState(null)
  const [pdfBusy, setPdfBusy] = useState(false)
  const [pdfError, setPdfError] = useState('')

  useEffect(() => {
    let active = true
    getInspection(inspectionId)
      .then((data) => active && setState({ loading: false, error: '', notFound: false, data }))
      .catch((err) => active && setState({ loading: false, error: err.message, notFound: err.status === 404, data: null }))
    return () => { active = false }
  }, [inspectionId])

  const downloadPdf = async () => {
    setPdfBusy(true)
    setPdfError('')
    try {
      await downloadFile(state.data.urls.report, `PCB-Inspection-Report-${inspectionId}.pdf`)
    } catch (err) {
      setPdfError(err.message)
    } finally {
      setPdfBusy(false)
    }
  }

  const { loading, error, notFound, data } = state

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto max-w-6xl px-5 py-8 sm:py-10">
        {loading && (
          <div className="flex items-center justify-center gap-2 py-32 text-mute"><Spinner className="h-5 w-5" /> Loading results…</div>
        )}

        {!loading && error && (
          <div className="mx-auto max-w-lg space-y-5 py-16 text-center">
            <h1 className="text-2xl font-semibold">{notFound ? 'Inspection not found' : 'Could not load results'}</h1>
            <ErrorBanner message={notFound ? 'This inspection does not exist. It may have been deleted.' : error} />
            <Link to="/inspect" className="inline-flex items-center gap-2 rounded-lg border border-line bg-ink-800 px-4 py-2.5 text-sm font-medium hover:bg-ink-700">
              <ArrowLeft className="h-4 w-4" /> Back to Inspection
            </Link>
          </div>
        )}

        {data && (() => {
          const style = STATUS_STYLES[data.status] || STATUS_STYLES.inconclusive
          const ConclusionIcon = style.icon
          const selected = data.detections.find((d) => d.id === selectedId) || null
          return (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <Link to="/inspect" className="inline-flex items-center gap-2 rounded-lg border border-line bg-ink-800 px-4 py-2.5 text-sm font-medium transition-colors hover:bg-ink-700">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to Inspection
                </Link>
                <Button onClick={downloadPdf} disabled={pdfBusy}>
                  {pdfBusy ? <Spinner /> : <FileText className="h-4 w-4" />} Download PDF Report
                </Button>
              </div>
              {pdfError && <ErrorBanner message={pdfError} onDismiss={() => setPdfError('')} />}

              <div className={`flex items-start gap-4 rounded-2xl border p-5 sm:p-6 ${style.bg} ${style.border}`}>
                <ConclusionIcon className={`mt-1 h-6 w-6 shrink-0 ${style.text}`} aria-hidden="true" />
                <div>
                  <p className="text-sm text-mute">Inspection conclusion</p>
                  <h1 className={`mt-0.5 text-2xl font-semibold tracking-tight ${style.text}`}>{data.conclusion.label}</h1>
                  <p className="mt-2 max-w-2xl text-sm leading-relaxed text-fg/80">{data.conclusion.message}</p>
                </div>
              </div>

              <section aria-label="Inspection information" className="rounded-2xl border border-line bg-ink-850 p-5">
                <dl className="grid grid-cols-2 gap-x-6 gap-y-4 lg:grid-cols-5">
                  <InfoItem label="Inspection ID" value={data.inspection_id} />
                  <InfoItem label="Filename" value={data.filename} />
                  <InfoItem label="Date and time" value={formatDateTime(data.created_at)} />
                  <InfoItem label="Model" value={data.model.name} />
                  <InfoItem label="Image" value={`${data.image.width} × ${data.image.height} px · ${formatBytes(data.image.size_bytes)}`} />
                </dl>
              </section>

              <ImageViewer inspection={data} selected={selected} />

              <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
                <section aria-labelledby="summary-title" className="h-fit rounded-2xl border border-line bg-ink-850 p-5 sm:p-6">
                  <h2 id="summary-title" className="text-lg font-semibold">Detection summary</h2>
                  <dl className="mt-4 grid grid-cols-2 gap-3">
                    <div className="rounded-xl bg-ink-900 p-4">
                      <dt className="text-xs text-dim">Total detections</dt>
                      <dd className="mt-1 text-3xl font-semibold">{data.total_detections}</dd>
                    </div>
                    <div className="rounded-xl bg-ink-900 p-4">
                      <dt className="text-xs text-dim">Unique defect classes</dt>
                      <dd className="mt-1 text-3xl font-semibold">{data.unique_classes}</dd>
                    </div>
                  </dl>
                  {data.class_summary.length > 0 && (
                    <ul className="mt-4 divide-y divide-line">
                      {data.class_summary.map((c) => (
                        <li key={c.defect} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                          <span className="font-medium">{prettyDefect(c.defect)}</span>
                          <span className="text-mute">{c.count}× · up to {percent(c.max_confidence)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {data.low_confidence_candidates > 0 && (
                    <p className="mt-4 text-xs leading-relaxed text-dim">
                      {data.low_confidence_candidates} additional low-confidence candidate{data.low_confidence_candidates === 1 ? '' : 's'} fell below the {Math.round(data.model.confidence_threshold * 100)}% reporting threshold and {data.low_confidence_candidates === 1 ? 'is' : 'are'} not listed.
                    </p>
                  )}
                </section>

                <section aria-labelledby="details-title" className="rounded-2xl border border-line bg-ink-850 p-5 sm:p-6">
                  <h2 id="details-title" className="text-lg font-semibold">Individual detections</h2>
                  {data.detections.length > 0 && <p className="mt-1 mb-4 text-sm text-mute">Select a detection to highlight its bounding box on the images.</p>}
                  <div className={data.detections.length ? '' : 'mt-4'}>
                    <DetectionList detections={data.detections} selectedId={selectedId} onSelect={setSelectedId} />
                  </div>
                </section>
              </div>

              <div className="flex items-start gap-3 rounded-xl border border-line bg-ink-900 p-4 text-xs leading-relaxed text-mute">
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-dim" aria-hidden="true" />
                <p>
                  The model recognises six defect types only and was evaluated on a held-out test set of two PCB boards
                  (precision {percent(data.evaluation.precision)}, recall {percent(data.evaluation.recall)}, mAP@50 {percent(data.evaluation.map50)},
                  mAP@50–95 {percent(data.evaluation.map50_95)}). These are experimental figures, not a guarantee of real-world performance.
                  “No Visible Defect Detected” does not mean the board is defect-free. Confirm findings by manual inspection.
                </p>
              </div>
            </div>
          )
        })()}
      </main>
    </div>
  )
}
