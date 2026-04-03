import { Bt2Svg } from './Bt2Icon'

const stroke = {
  stroke: 'currentColor',
  strokeWidth: 1.65,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

export function Bt2LockIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path
        d="M7 11V8.8C7 6.149 9.239 4 12 4C14.761 4 17 6.149 17 8.8V11"
        {...stroke}
      />
      <path
        d="M6.5 11H17.5C18.3284 11 19 11.6716 19 12.5V18.5C19 19.3284 18.3284 20 17.5 20H6.5C5.67157 20 5 19.3284 5 18.5V12.5C5 11.6716 5.67157 11 6.5 11Z"
        {...stroke}
      />
    </Bt2Svg>
  )
}

export function Bt2HelpIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path d="M12 17.5H12.01" stroke="currentColor" strokeWidth={2} strokeLinecap="round" />
      <path
        d="M9.5 9.5C9.8 8.3 10.9 7.5 12.2 7.5C13.7 7.5 14.7 8.4 14.7 9.7C14.7 10.6 14.2 11.2 13.5 11.7C12.8 12.2 12.4 12.6 12.4 13.5V14"
        {...stroke}
      />
      <path
        d="M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z"
        {...stroke}
      />
    </Bt2Svg>
  )
}

export function Bt2ShieldCheckIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path d="M12 3l7 4v6c0 5-3 8-7 8s-7-3-7-8V7l7-4z" {...stroke} />
      <path d="M9.3 12.2l1.8 1.8 3.7-4.2" {...stroke} />
    </Bt2Svg>
  )
}

export function Bt2VaultIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path
        d="M4.5 10.3L12 6l7.5 4.3V18c0 3.9-2.7 6-7.5 6s-7.5-2.1-7.5-6v-7.7z"
        {...stroke}
      />
      <path d="M9 13l3 2 3-2" {...stroke} />
    </Bt2Svg>
  )
}

export function Bt2HistoryIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path d="M12 7v5l3 2" {...stroke} />
      <path d="M4.8 8.2A8.5 8.5 0 1 0 20 12" {...stroke} />
      <path d="M4 4v4h4" {...stroke} />
    </Bt2Svg>
  )
}

export function Bt2ChartBarsIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path d="M4 19V5" {...stroke} />
      <path d="M9 19v-8" {...stroke} />
      <path d="M14 19v-11" {...stroke} />
      <path d="M19 19v-6" {...stroke} />
    </Bt2Svg>
  )
}

export function Bt2UserIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path d="M20 21a8 8 0 0 0-16 0" {...stroke} />
      <path d="M12 12a4.5 4.5 0 1 0-4.5-4.5A4.5 4.5 0 0 0 12 12z" {...stroke} />
    </Bt2Svg>
  )
}

export function Bt2PlusIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path d="M12 5v14" {...stroke} />
      <path d="M5 12h14" {...stroke} />
    </Bt2Svg>
  )
}

export function Bt2SettingsIcon({ className }: { className?: string }) {
  return (
    <Bt2Svg className={className} aria-hidden>
      <path
        d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
        {...stroke}
      />
      <path
        d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
        {...stroke}
      />
    </Bt2Svg>
  )
}
