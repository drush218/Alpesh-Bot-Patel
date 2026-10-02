import type { ReactNode } from 'react'

type Tone = 'up' | 'down' | 'neutral'
type Strength = 'full' | 'half' | 'neutral'

const TONE_VAR: Record<Tone, string> = {
  up: 'var(--up)',
  down: 'var(--down)',
  neutral: 'var(--ink3)',
}

const STRENGTH_PCT: Record<Strength, [number, number]> = {
  full: [20, 50],
  half: [12, 34],
  neutral: [7, 22],
}

interface ChipProps {
  tone: Tone
  strength?: Strength
  children: ReactNode
}

export function Chip({ tone, strength = 'full', children }: ChipProps) {
  const c = TONE_VAR[tone]
  const [bgPct, borderPct] = STRENGTH_PCT[strength]

  return (
    <span
      style={{
        display: 'inline-block',
        padding: '3px 9px',
        borderRadius: 2,
        fontSize: 10.5,
        letterSpacing: '.04em',
        whiteSpace: 'nowrap',
        color: c,
        background: `color-mix(in srgb, ${c} ${bgPct}%, transparent)`,
        border: `1px solid color-mix(in srgb, ${c} ${borderPct}%, transparent)`,
      }}
    >
      {children}
    </span>
  )
}
