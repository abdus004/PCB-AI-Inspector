import { Camera, Check, RotateCcw, SwitchCamera } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button, ErrorBanner, Spinner } from './ui.jsx'

function describeCameraError(error) {
  switch (error?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
      return 'Camera access was blocked. Allow camera permission in your browser settings, then try again.'
    case 'NotFoundError':
    case 'DevicesNotFoundError':
      return 'No camera was found on this device.'
    case 'NotReadableError':
    case 'TrackStartError':
      return 'The camera is being used by another application. Close it and try again.'
    case 'OverconstrainedError':
      return 'The requested camera settings are not supported by this device.'
    default:
      return 'The camera could not be started. You can upload an image instead.'
  }
}

const CAMERA_UNSUPPORTED =
  'Camera access is not available in this browser or on this connection. ' +
  'Browsers only allow the camera on https:// pages or on localhost. You can upload an image instead.'

export default function CameraCapture({ onUse, onCancel }) {
  const supported = Boolean(navigator.mediaDevices?.getUserMedia)
  const videoRef = useRef(null)
  const [status, setStatus] = useState(supported ? 'starting' : 'error') // starting | live | captured | error
  const [error, setError] = useState(supported ? '' : CAMERA_UNSUPPORTED)
  const [facing, setFacing] = useState('environment')   // rear camera first on phones
  const [attempt, setAttempt] = useState(0)
  const [canSwitch, setCanSwitch] = useState(false)
  const [captured, setCaptured] = useState(null)        // { blob, url }

  // Start the camera; always release it on cleanup.
  useEffect(() => {
    if (!supported) return undefined
    let cancelled = false
    let stream = null
    navigator.mediaDevices
      .getUserMedia({
        video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      })
      .then((s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return }
        stream = s
        const video = videoRef.current
        if (video) { video.srcObject = s; video.play().catch(() => {}) }
        setStatus('live')
        navigator.mediaDevices.enumerateDevices().then((list) => {
          if (!cancelled) setCanSwitch(list.filter((d) => d.kind === 'videoinput').length > 1)
        })
      })
      .catch((err) => {
        if (cancelled) return
        setError(describeCameraError(err))
        setStatus('error')
      })
    return () => { cancelled = true; stream?.getTracks().forEach((t) => t.stop()) }
  }, [facing, attempt, supported])

  // Free the captured preview URL when it changes or on unmount.
  useEffect(() => () => { if (captured) URL.revokeObjectURL(captured.url) }, [captured])

  const capture = () => {
    const video = videoRef.current
    if (!video || !video.videoWidth) return
    const canvas = document.createElement('canvas')
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    canvas.getContext('2d').drawImage(video, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (!blob) { setError('Could not capture the image. Please try again.'); return }
        setCaptured({ blob, url: URL.createObjectURL(blob) })
        setStatus('captured')
      },
      'image/jpeg',
      0.92,
    )
  }

  const retake = () => { setCaptured(null); setStatus('live') }

  const useCaptured = () => {
    if (!captured) return
    const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14)
    onUse(new File([captured.blob], `camera-capture-${stamp}.jpg`, { type: 'image/jpeg' }))
  }

  const switchCamera = () => {
    setStatus('starting')
    setFacing((f) => (f === 'environment' ? 'user' : 'environment'))
  }

  const retry = () => { setError(''); setStatus('starting'); setAttempt((n) => n + 1) }

  if (status === 'error') {
    return (
      <div className="space-y-4">
        <ErrorBanner message={error} />
        <div className="flex gap-2">
          {supported && <Button variant="secondary" onClick={retry}>Try again</Button>}
          <Button variant="ghost" onClick={onCancel}>Back to upload</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="relative overflow-hidden rounded-xl border border-line bg-black">
        <video
          ref={videoRef}
          playsInline
          muted
          className={`aspect-[4/3] w-full object-contain ${status === 'captured' ? 'hidden' : ''}`}
        />
        {status === 'captured' && captured && (
          <img src={captured.url} alt="Captured PCB" className="aspect-[4/3] w-full object-contain" />
        )}
        {status === 'starting' && (
          <div className="absolute inset-0 flex items-center justify-center gap-2 bg-ink-950/80 text-sm text-mute">
            <Spinner /> Starting camera…
          </div>
        )}
      </div>
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}
      <div className="flex flex-wrap gap-2">
        {status === 'captured' ? (
          <>
            <Button onClick={useCaptured}><Check className="h-4 w-4" /> Use captured image</Button>
            <Button variant="secondary" onClick={retake}><RotateCcw className="h-4 w-4" /> Retake</Button>
          </>
        ) : (
          <>
            <Button onClick={capture} disabled={status !== 'live'}><Camera className="h-4 w-4" /> Capture</Button>
            {canSwitch && (
              <Button variant="secondary" onClick={switchCamera} disabled={status !== 'live'}>
                <SwitchCamera className="h-4 w-4" /> Switch camera
              </Button>
            )}
          </>
        )}
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  )
}
