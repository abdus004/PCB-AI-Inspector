import {
  ArrowRight, CircleDot, Eraser, FileText, ImagePlus, Info, ScanSearch, Scissors, Spline, Unplug, Zap,
} from 'lucide-react'
import PcbHero from '../components/PcbHero.jsx'
import { LandingHeader, Brand } from '../components/Header.jsx'
import Link from '../components/Link.jsx'
import { DEFECT_CLASSES, METRICS_DISCLOSURE, MODEL_METRICS, STEPS, TECH_STACK } from '../data/content.js'

const ICONS = { CircleDot, Eraser, FileText, ImagePlus, ScanSearch, Scissors, Spline, Unplug, Zap }

function GetStarted({ className = '' }) {
  return (
    <Link
      to="/inspect"
      className={`inline-flex items-center justify-center gap-2 rounded-lg bg-cyan px-6 py-3 text-[15px] font-semibold text-ink-950 transition-colors hover:bg-cyan-deep ${className}`}
    >
      Get Started
      <ArrowRight className="h-4 w-4" aria-hidden="true" />
    </Link>
  )
}

function SectionTitle({ title, children }) {
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h2>
      {children && <p className="mt-3 leading-relaxed text-mute">{children}</p>}
    </div>
  )
}

export default function LandingPage() {
  return (
    <div>
      <LandingHeader />
      <main>
        {/* Hero */}
        <section id="home" className="relative overflow-hidden">
          <div className="grid-texture pointer-events-none absolute inset-0" aria-hidden="true" />
          <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-5 py-16 sm:py-20 lg:grid-cols-[1.05fr_1fr] lg:py-24">
            <div>
              <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl lg:text-5xl">
                Smarter PCB Inspection. Powered by Artificial Intelligence.
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-mute">
                Upload or capture a photo of a printed circuit board and let a trained YOLO11n model
                flag possible manufacturing defects in seconds, with annotated images and a downloadable report.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-4">
                <GetStarted />
                <Link to="/#how-it-works" className="rounded-md px-2 py-2 text-sm font-medium text-mute transition-colors hover:text-fg">
                  See how it works
                </Link>
              </div>
            </div>
            <PcbHero />
          </div>
        </section>

        {/* Model performance */}
        <section id="performance" className="border-y border-line/70 bg-ink-900">
          <div className="mx-auto max-w-6xl px-5 py-16 sm:py-20">
            <SectionTitle title="Model performance">
              Fine-tuned YOLO11n results on a held-out test set.
            </SectionTitle>
            <dl className="mt-10 grid grid-cols-2 overflow-hidden rounded-xl border border-line bg-line lg:grid-cols-4" style={{ gap: 1 }}>
              {MODEL_METRICS.map((metric) => (
                <div key={metric.label} className="bg-ink-850 p-5 sm:p-6">
                  <dt className="text-sm text-mute">{metric.label}</dt>
                  <dd className="mt-2 text-3xl font-semibold tracking-tight text-fg sm:text-4xl">{metric.value}</dd>
                  <p className="mt-2 text-xs leading-relaxed text-dim">{metric.hint}</p>
                </div>
              ))}
            </dl>
            <div className="mt-5 flex items-start gap-3 rounded-lg border border-amber/25 bg-amber/5 p-4 text-sm leading-relaxed text-amber/90">
              <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p>{METRICS_DISCLOSURE}</p>
            </div>
          </div>
        </section>

        {/* Supported defects */}
        <section id="about" className="mx-auto max-w-6xl px-5 py-16 sm:py-20">
          <SectionTitle title="Six supported defect classes">
            PCB-AI-Inspector is trained to recognise six common bare-board manufacturing defects.
            Anything outside these classes is not covered.
          </SectionTitle>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {DEFECT_CLASSES.map((defect) => {
              const Icon = ICONS[defect.icon]
              return (
                <li key={defect.key} className="rounded-xl border border-line bg-ink-850 p-5">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-ink-700 text-cyan">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mt-4 font-semibold">{defect.name}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-mute">{defect.text}</p>
                </li>
              )
            })}
          </ul>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="border-y border-line/70 bg-ink-900">
          <div className="mx-auto max-w-6xl px-5 py-16 sm:py-20">
            <SectionTitle title="How it works">Three steps from photo to report.</SectionTitle>
            <ol className="mt-10 grid gap-4 md:grid-cols-3">
              {STEPS.map((step, index) => {
                const Icon = ICONS[step.icon]
                return (
                  <li key={step.title} className="rounded-xl border border-line bg-ink-850 p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-ink-700 text-cyan">
                        <Icon className="h-5 w-5" aria-hidden="true" />
                      </div>
                      <span className="text-sm font-medium text-dim">Step {index + 1}</span>
                    </div>
                    <h3 className="mt-5 font-semibold">{step.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-mute">{step.text}</p>
                  </li>
                )
              })}
            </ol>
          </div>
        </section>

        {/* Tech stack */}
        <section className="mx-auto max-w-6xl px-5 py-16 sm:py-20">
          <SectionTitle title="Built with">An open, student-friendly stack you can run entirely on your own machine.</SectionTitle>
          <ul className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {TECH_STACK.map((tech) => (
              <li key={tech.name} className="rounded-lg border border-line bg-ink-850 px-4 py-3">
                <p className="text-sm font-medium">{tech.name}</p>
                <p className="mt-0.5 text-xs text-dim">{tech.role}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Final CTA */}
        <section className="mx-auto max-w-6xl px-5 pb-20">
          <div className="rounded-2xl border border-line bg-ink-850 px-6 py-12 text-center sm:px-12">
            <h2 className="mx-auto max-w-xl text-2xl font-semibold tracking-tight sm:text-3xl">
              Ready to inspect your first board?
            </h2>
            <p className="mx-auto mt-3 max-w-lg text-mute">
              Upload a photo or use your camera. Your results are stored locally and can be reopened at any time.
            </p>
            <div className="mt-7">
              <GetStarted />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line/70">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 py-8 sm:flex-row sm:items-center sm:justify-between">
          <Brand />
          <p className="max-w-md text-xs leading-relaxed text-dim">
            An experimental decision-support tool. Always confirm findings by manual inspection.
          </p>
        </div>
      </footer>
    </div>
  )
}
