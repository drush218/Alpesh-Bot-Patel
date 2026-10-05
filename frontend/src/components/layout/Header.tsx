import { useTheme } from '../../contexts/ThemeContext'
import { NavButton } from './NavButton'

const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'book', label: 'Book' },
  { key: 'analysis', label: 'Analysis' },
  { key: 'macro', label: 'Macro' },
  { key: 'sizer', label: 'Sizer' },
  { key: 'settings', label: 'Settings' },
] as const

export type Screen = 'dashboard' | 'book' | 'analysis' | 'settings'
const BUILT: readonly string[] = ['dashboard', 'book', 'analysis', 'settings']

function formatTimestamp(date: Date): string {
  const datePart = date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  const timePart = date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
  const tz = new Intl.DateTimeFormat('en-GB', { timeZoneName: 'short' })
    .formatToParts(date)
    .find((p) => p.type === 'timeZoneName')?.value
  return `${datePart} · ${timePart}${tz ? ' ' + tz : ''}`
}

export function Header({ screen, onNavigate, analysisTicker }: { screen: Screen; onNavigate: (s: Screen) => void; analysisTicker: string | null }) {
  const { theme, toggleTheme } = useTheme()

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 20,
        padding: '0 20px',
        height: 52,
        borderBottom: '1px solid var(--line)',
        background: 'var(--panel)',
        position: 'sticky',
        top: 0,
        zIndex: 20,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 9 }}>
        <span style={{ fontWeight: 600, letterSpacing: '.14em', fontSize: 11, color: 'var(--accent)' }}>
          PORTFOLIO
        </span>
        <span style={{ fontWeight: 400, letterSpacing: '.14em', fontSize: 11, color: 'var(--ink3)' }}>
          TERMINAL
        </span>
      </div>

      <nav style={{ display: 'flex', gap: 2, marginLeft: 8 }}>
        {NAV_ITEMS.map((item) => (
          <NavButton
            key={item.key}
            label={item.key === 'analysis' && analysisTicker ? analysisTicker : item.label}
            active={item.key === screen}
            disabled={!BUILT.includes(item.key) || (item.key === 'analysis' && !analysisTicker)}
            onClick={() => onNavigate(item.key as Screen)}
          />
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      <div style={{ display: 'flex', alignItems: 'center', gap: 14, color: 'var(--ink3)', fontSize: 11, letterSpacing: '.04em' }}>
        <span>{formatTimestamp(new Date())}</span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--ink2)' }}>
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'var(--up)',
              animation: 'pulseDot 2.4s ease-in-out infinite',
            }}
          />
          prices live
        </span>
        <button
          onClick={toggleTheme}
          style={{
            fontFamily: 'inherit',
            fontSize: 11,
            letterSpacing: '.08em',
            padding: '5px 10px',
            border: '1px solid var(--line2)',
            background: 'transparent',
            color: 'var(--ink2)',
            borderRadius: 3,
            cursor: 'pointer',
          }}
        >
          {theme === 'light' ? 'DARK' : 'LIGHT'}
        </button>
      </div>
    </header>
  )
}
