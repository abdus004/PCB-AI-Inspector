// Decorative PCB illustration with example detection boxes.
// It is an illustration only, not a real inspection result.
const TRACES = [
  'M40 60H150L180 90H300', 'M40 110H110L140 140H210L240 170H360', 'M60 220H200L230 190H330',
  'M300 60H420', 'M360 110V190H420', 'M90 270H260L290 240H420', 'M150 60V30', 'M110 140V250',
]
const PADS = [
  [40, 60], [300, 60], [420, 60], [40, 110], [360, 170], [60, 220], [330, 190],
  [90, 270], [420, 240], [420, 190], [150, 30], [110, 250],
]
const BOXES = [
  { x: 170, y: 72, w: 62, h: 36, label: 'open_circuit' },
  { x: 322, y: 176, w: 52, h: 30, label: 'short' },
  { x: 86, y: 232, w: 46, h: 38, label: 'missing_hole' },
]

export default function PcbHero() {
  return (
    <figure className="m-0">
      <div className="rounded-2xl border border-line bg-ink-850 p-3 sm:p-4">
        <svg viewBox="0 0 460 310" className="block h-auto w-full" role="img" aria-label="Illustration of a printed circuit board with three highlighted example defect regions">
          <rect x="6" y="6" width="448" height="298" rx="14" fill="#0e2a2f" stroke="#1d4a52" />
          {TRACES.map((d) => (
            <path key={d} d={d} fill="none" stroke="#2f7d86" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
          ))}
          {PADS.map(([cx, cy]) => (
            <g key={`${cx}-${cy}`}>
              <circle cx={cx} cy={cy} r="9" fill="#3a9aa5" />
              <circle cx={cx} cy={cy} r="3.5" fill="#0e2a2f" />
            </g>
          ))}
          <rect x="230" y="200" width="60" height="44" rx="4" fill="#0a1d21" stroke="#2f7d86" />
          {[0, 1, 2, 3].map((i) => (
            <g key={i}>
              <rect x={236 + i * 13} y="194" width="5" height="8" fill="#3a9aa5" />
              <rect x={236 + i * 13} y="242" width="5" height="8" fill="#3a9aa5" />
            </g>
          ))}
          {BOXES.map((b) => (
            <g key={b.label}>
              <rect x={b.x} y={b.y} width={b.w} height={b.h} fill="rgb(79 214 230 / 0.08)" stroke="#4fd6e6" strokeWidth="1.6" rx="2" />
              <rect x={b.x} y={b.y - 15} width={b.label.length * 5.4 + 10} height="15" fill="#4fd6e6" rx="2" />
              <text x={b.x + 5} y={b.y - 4.5} fontSize="9.5" fontWeight="600" fill="#070c18" fontFamily="Schibsted Grotesk, sans-serif">{b.label}</text>
            </g>
          ))}
        </svg>
      </div>
      <figcaption className="mt-2.5 px-1 text-xs text-dim">Illustration only. Not a real inspection result.</figcaption>
    </figure>
  )
}
