export default function Logo({ className = 'h-8 w-8' }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#131c31" stroke="#202c47" />
      <path d="M8 11h7l3 3h6M8 21h5l3-3h8" fill="none" stroke="#4fd6e6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="8" cy="11" r="2" fill="#4fd6e6" />
      <circle cx="24" cy="14" r="2" fill="#4fd6e6" />
      <circle cx="8" cy="21" r="2" fill="#4fd6e6" />
      <circle cx="24" cy="18" r="2" fill="#4fd6e6" />
    </svg>
  )
}
