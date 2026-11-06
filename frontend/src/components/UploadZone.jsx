import { ImagePlus } from 'lucide-react'
import { useRef, useState } from 'react'
import { ACCEPT } from '../lib/imageValidation.js'
import { Button } from './ui.jsx'

export default function UploadZone({ onFile, onMultiple, disabled }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const openPicker = () => inputRef.current?.click()

  const handleDrop = (event) => {
    event.preventDefault()
    setDragging(false)
    if (disabled) return
    const files = event.dataTransfer.files
    if (files.length > 1) onMultiple?.()
    else if (files.length === 1) onFile(files[0])
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload an image. Drag and drop here or press Enter to browse."
      onClick={openPicker}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), openPicker())}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-6 py-14 text-center transition-colors ${
        dragging ? 'border-cyan bg-cyan/5' : 'border-line bg-ink-900 hover:border-slate-soft/50'
      }`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-ink-700 text-cyan">
        <ImagePlus className="h-6 w-6" aria-hidden="true" />
      </div>
      <p className="mt-4 font-medium">Drag and drop a PCB image here</p>
      <p className="mt-1 text-sm text-mute">JPG, JPEG, PNG or WEBP, up to 10 MB</p>
      <Button
        type="button"
        variant="secondary"
        className="mt-5"
        onClick={(e) => { e.stopPropagation(); openPicker() }}
      >
        Browse files
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          e.target.value = ''           // allow choosing the same file again
          if (file) onFile(file)
        }}
      />
    </div>
  )
}
