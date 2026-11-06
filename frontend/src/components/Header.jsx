import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import Link from './Link.jsx'
import Logo from './Logo.jsx'

const NAV = [
  { label: 'Home', to: '/' },
  { label: 'About', to: '/#about' },
  { label: 'Model Performance', to: '/#performance' },
  { label: 'How It Works', to: '/#how-it-works' },
]

export function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2.5 rounded-md" aria-label="PCB-AI-Inspector home">
      <Logo />
      <span className="text-[17px] font-semibold tracking-tight">PCB-AI-Inspector</span>
    </Link>
  )
}

/** Landing page header with the four navigation links. */
export function LandingHeader() {
  const [open, setOpen] = useState(false)
  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-ink-950/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Brand />
        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV.map((item) => (
            <Link key={item.label} to={item.to} className="rounded-md px-3 py-2 text-sm text-mute transition-colors hover:text-fg">
              {item.label}
            </Link>
          ))}
          <Link to="/inspect" className="ml-3 rounded-lg bg-cyan px-4 py-2 text-sm font-semibold text-ink-950 transition-colors hover:bg-cyan-deep">
            Get Started
          </Link>
        </nav>
        <button
          className="rounded-md p-2 text-mute hover:text-fg md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {open && (
        <nav className="border-t border-line/70 px-5 py-3 md:hidden" aria-label="Mobile">
          {NAV.map((item) => (
            <Link key={item.label} to={item.to} onClick={() => setOpen(false)} className="block rounded-md px-2 py-3 text-sm text-mute hover:text-fg">
              {item.label}
            </Link>
          ))}
          <Link to="/inspect" onClick={() => setOpen(false)} className="mt-2 block rounded-lg bg-cyan px-4 py-3 text-center text-sm font-semibold text-ink-950">
            Get Started
          </Link>
        </nav>
      )}
    </header>
  )
}

/** Simple header used on the inspection and results pages. */
export function AppHeader() {
  return (
    <header className="border-b border-line/70 bg-ink-950/85">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Brand />
        <Link to="/" className="rounded-md px-3 py-2 text-sm text-mute transition-colors hover:text-fg">
          Home
        </Link>
      </div>
    </header>
  )
}
