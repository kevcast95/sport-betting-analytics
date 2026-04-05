/** Iconos locales equivalentes a Material del ref Stitch (sin CDN). */

const s = {
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  fill: 'none',
}

export function IconTrendingUp({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M4 16l6-6 4 4 6-8" {...s} />
      <path d="M14 8h6v6" {...s} />
    </svg>
  )
}

export function IconTrendingDown({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M4 8l6 6 4-4 6 8" {...s} />
      <path d="M14 16h6v-6" {...s} />
    </svg>
  )
}

export function IconRestart({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M4 12a8 8 0 1 1 3.2 6.4" {...s} />
      <path d="M4 16v-4h4" {...s} />
    </svg>
  )
}

export function IconPsychology({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M12 5a3 3 0 1 0-3 3M9 12h.01M15 12h.01" {...s} />
      <path d="M8 20h8M9.5 16c.8 2.3 4.2 2.3 5 0" {...s} />
      <path d="M6 8.5C4.5 9.7 4 11.2 4 13c0 2.8 2.2 5 5 5h2" {...s} />
      <path d="M18 8.5c1.5 1.2 2 2.7 2 4.5 0 2.8-2.2 5-5 5h-2" {...s} />
    </svg>
  )
}

export function IconSearch({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={16} height={16} aria-hidden>
      <circle cx="11" cy="11" r="6" {...s} />
      <path d="M20 20l-4-4" {...s} />
    </svg>
  )
}

export function IconChevronLeft({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={18} height={18} aria-hidden>
      <path d="M14 6l-6 6 6 6" {...s} />
    </svg>
  )
}

export function IconChevronRight({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={18} height={18} aria-hidden>
      <path d="M10 6l6 6-6 6" {...s} />
    </svg>
  )
}

export function IconExpandMore({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={18} height={18} aria-hidden>
      <path d="M6 9l6 6 6-6" {...s} />
    </svg>
  )
}

export function IconWallet({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M4 7a2 2 0 0 1 2-2h12v16H6a2 2 0 0 1-2-2V7z" {...s} />
      <path d="M16 11h2" {...s} />
    </svg>
  )
}

export function IconAnalytics({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M4 19V5M8 19v-6M12 19V9M16 19v-3M20 19v-8" {...s} />
    </svg>
  )
}

export function IconArrowForward({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M5 12h14M13 6l6 6-6 6" {...s} />
    </svg>
  )
}

export function IconCheckCircle({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={18} height={18} aria-hidden>
      <circle cx="12" cy="12" r="9" {...s} />
      <path d="M8 12l2.5 2.5L16 9" {...s} />
    </svg>
  )
}

export function IconFactCheck({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M9 11l2 2 4-4" {...s} />
      <path d="M5 4h11l3 3v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" {...s} />
    </svg>
  )
}

export function IconWarning({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={18} height={18} aria-hidden>
      <path d="M12 5l8 14H4l8-14z" {...s} />
      <path d="M12 10v3M12 17h.01" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
    </svg>
  )
}

export function IconVerified({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={18} height={18} aria-hidden>
      <path d="M12 3l7 4v6c0 5-3 8-7 8s-7-3-7-8V7l7-4z" {...s} />
      <path d="M9 12l2 2 4-3" {...s} />
    </svg>
  )
}

export function IconSmallCheck({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={16} height={16} aria-hidden>
      <path d="M6 12l3 3 6-6" stroke="currentColor" strokeWidth={2} fill="none" strokeLinecap="round" />
    </svg>
  )
}

export function IconLock({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={24} height={24} aria-hidden>
      <rect x="5" y="11" width="14" height="10" rx="2" {...s} />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" {...s} />
    </svg>
  )
}

export function IconBolt({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={24} height={24} aria-hidden>
      <path d="M13 2L4 14h7l-1 8 10-12h-7l0-8z" {...s} />
    </svg>
  )
}

export function IconToken({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={24} height={24} aria-hidden>
      <circle cx="12" cy="12" r="9" {...s} />
      <circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" />
    </svg>
  )
}

export function IconMenuBook({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={24} height={24} aria-hidden>
      <path d="M6 4h5a4 4 0 0 1 4 4v14a2 2 0 0 0-2-2H6V4z" {...s} />
      <path d="M18 4h-5a4 4 0 0 0-4 4v14a2 2 0 0 1 2-2h7V4z" {...s} />
    </svg>
  )
}

export function IconDiamond({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={24} height={24} aria-hidden>
      <path d="M12 3l8 8-8 10-8-10 8-8z" {...s} />
    </svg>
  )
}

export function IconCalendar({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <rect x="4" y="5" width="16" height="15" rx="2" {...s} />
      <path d="M8 3v4M16 3v4M4 11h16" {...s} />
    </svg>
  )
}

export function IconShowChart({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={22} height={22} aria-hidden>
      <path d="M4 19V5M8 19v-4M12 19V9M16 19v-6M20 19v-9" {...s} />
    </svg>
  )
}

export function IconShieldHeart({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={24} height={24} aria-hidden>
      <path
        d="M12 21s-8-4.5-8-11V5l8-3 8 3v5c0 6.5-8 11-8 11z"
        {...s}
      />
      <path
        d="M12 16c-2-2.2-4-4.1-4-6a2.5 2.5 0 0 1 4-1.7 2.5 2.5 0 0 1 4 1.7c0 1.9-2 3.8-4 6z"
        {...s}
      />
    </svg>
  )
}

export function IconWaterDrop({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={24} height={24} aria-hidden>
      <path d="M12 3s6 7 6 11a6 6 0 1 1-12 0c0-4 6-11 6-11z" {...s} />
    </svg>
  )
}

export function IconSecurity({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" width={24} height={24} aria-hidden>
      <path d="M12 3l8 4v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V7l8-4z" {...s} />
      <path d="M9 12l2 2 4-4" {...s} />
    </svg>
  )
}
