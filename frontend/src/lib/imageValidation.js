// Browser-side validation. The backend validates again; this gives instant feedback.
export const MAX_BYTES = 10 * 1024 * 1024
export const ACCEPT = '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp'

// Check the real file signature (magic bytes), not only the file name.
async function detectFormat(file) {
  const head = new Uint8Array(await file.slice(0, 16).arrayBuffer())
  const ascii = (from, to) => String.fromCharCode(...head.slice(from, to))
  if (head[0] === 0xff && head[1] === 0xd8 && head[2] === 0xff) return 'JPEG'
  if (head[0] === 0x89 && ascii(1, 4) === 'PNG') return 'PNG'
  if (ascii(0, 4) === 'RIFF' && ascii(8, 12) === 'WEBP') return 'WEBP'
  return null
}

function decodeImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
      URL.revokeObjectURL(url)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('decode failed'))
    }
    img.src = url
  })
}

/** Returns { ok: true, info } or { ok: false, error }. */
export async function validateImageFile(file) {
  if (!file) return { ok: false, error: 'No file selected.' }
  if (file.size === 0) return { ok: false, error: 'This file is empty.' }
  if (file.size > MAX_BYTES) {
    return { ok: false, error: 'This image is larger than 10 MB. Please choose a smaller file.' }
  }
  const format = await detectFormat(file)
  if (!format) {
    return { ok: false, error: 'Unsupported file. Please choose a JPG, JPEG, PNG or WEBP image.' }
  }
  try {
    const { width, height } = await decodeImage(file)
    if (!width || !height) throw new Error('empty')
    return { ok: true, info: { width, height, format } }
  } catch {
    return { ok: false, error: 'This image looks corrupted and could not be opened.' }
  }
}
