import { useCallback } from 'react'
import { navigate } from '../lib/router.js'

export default function Link({ to, children, onClick, ...props }) {
  const handle = useCallback(
    (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return
      event.preventDefault()
      onClick?.(event)
      navigate(to)
    },
    [to, onClick],
  )
  return (
    <a href={to} onClick={handle} {...props}>
      {children}
    </a>
  )
}
