// A tiny History-API router (no extra dependency). Routes:
//   /            landing page
//   /inspect     inspection page
//   /results/ID  results page
import { useEffect, useState } from 'react'

function currentLocation() {
  return window.location.pathname + window.location.hash
}

export function navigate(to, { replace = false } = {}) {
  if (replace) window.history.replaceState({}, '', to)
  else window.history.pushState({}, '', to)
  window.dispatchEvent(new PopStateEvent('popstate'))
  const hash = to.includes('#') ? to.split('#')[1] : ''
  // Let the new page render, then scroll to the anchor (or to the top).
  window.setTimeout(() => {
    const target = hash ? document.getElementById(hash) : null
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    else window.scrollTo({ top: 0 })
  }, 30)
}

export function useRoute() {
  const [location, setLocation] = useState(currentLocation)
  useEffect(() => {
    const onChange = () => setLocation(currentLocation())
    window.addEventListener('popstate', onChange)
    return () => window.removeEventListener('popstate', onChange)
  }, [])
  const path = location.split('#')[0]
  const resultsMatch = path.match(/^\/results\/([A-Za-z0-9-]+)\/?$/)
  if (resultsMatch) return { name: 'results', inspectionId: resultsMatch[1] }
  if (path === '/inspect' || path === '/inspect/') return { name: 'inspect' }
  return { name: 'landing' }
}
