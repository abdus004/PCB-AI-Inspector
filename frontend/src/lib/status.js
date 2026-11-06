import { CircleCheck, CircleHelp, TriangleAlert } from 'lucide-react'

export const STATUS_STYLES = {
  defects_detected: { icon: TriangleAlert, text: 'text-amber', bg: 'bg-amber/10', border: 'border-amber/30' },
  no_visible_defects_detected: { icon: CircleCheck, text: 'text-cyan', bg: 'bg-cyan/10', border: 'border-cyan/30' },
  inconclusive: { icon: CircleHelp, text: 'text-slate-soft', bg: 'bg-slate-soft/10', border: 'border-slate-soft/30' },
}
