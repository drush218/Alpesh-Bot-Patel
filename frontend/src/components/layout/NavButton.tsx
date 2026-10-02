interface NavButtonProps {
  label: string
  active?: boolean
  disabled?: boolean
  onClick?: () => void
}

export function NavButton({ label, active, disabled, onClick }: NavButtonProps) {
  return (
    <button
      onClick={disabled ? undefined : onClick}
      title={disabled ? 'Coming soon' : undefined}
      style={{
        padding: '6px 12px',
        borderRadius: 3,
        fontSize: 12,
        letterSpacing: '.04em',
        border: 0,
        background: active ? 'var(--accentSoft)' : 'transparent',
        color: disabled ? 'var(--line2)' : active ? 'var(--accent)' : 'var(--ink2)',
        fontWeight: active ? 600 : 400,
        cursor: disabled ? 'default' : 'pointer',
      }}
    >
      {label}
    </button>
  )
}
