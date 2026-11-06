// Centralised API layer: every request to the FastAPI backend goes through here.
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export const absoluteUrl = (path) => `${BASE_URL}${path}`

async function request(path, options = {}, timeoutMs = 120000) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  let response
  try {
    response = await fetch(absoluteUrl(path), { ...options, signal: controller.signal })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new ApiError('The request took too long. Please try again.', 0)
    }
    throw new ApiError(
      `Cannot reach the inspection server at ${BASE_URL}. Make sure the backend is running.`,
      0,
    )
  } finally {
    clearTimeout(timer)
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status}).`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join(' ')
    } catch {
      /* response had no JSON body */
    }
    throw new ApiError(detail, response.status)
  }
  return response
}

export async function inspectImage(file) {
  const form = new FormData()
  form.append('file', file, file.name)
  const response = await request('/inspect', { method: 'POST', body: form }, 180000)
  return response.json()
}

export async function listInspections(limit = 10, offset = 0) {
  const response = await request(`/inspections?limit=${limit}&offset=${offset}`)
  return response.json()
}

export async function getInspection(id) {
  const response = await request(`/inspections/${encodeURIComponent(id)}`)
  return response.json()
}

export async function deleteInspection(id) {
  const response = await request(`/inspections/${encodeURIComponent(id)}`, { method: 'DELETE' })
  return response.json()
}

// Download a file through fetch so errors can be shown and the filename is respected
// even though the backend is on a different origin.
export async function downloadFile(path, fallbackName) {
  const response = await request(path, {}, 60000)
  const blob = await response.blob()
  let filename = fallbackName
  const disposition = response.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
  if (match) filename = decodeURIComponent(match[1])

  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(objectUrl), 2000)
}
