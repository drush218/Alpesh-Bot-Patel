interface Option<T extends string> {
  value: T
  label: string
}

interface SegmentedControlProps<T extends string> {
  options: Option<T>[]
  value: T
  onChange: (value: T) => void
}

export function SegmentedControl<T extends string>({ options, value, onChange }: SegmentedControlProps<T>) {
  return (
    <div
      style={{
        display: 'flex',
        border: '1px solid var(--line2)',
        borderRadius: 3,
        overflow: 'hidden',
      }}
    >
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            style={{
              padding: '6px 13px',
              fontSize: 11.5,
              letterSpacing: '.05em',
              border: 0,
              cursor: 'pointer',
              background: active ? 'var(--accent)' : 'transparent',
              color: active ? 'var(--bg)' : 'var(--ink2)',
              fontWeight: active ? 600 : 400,
            }}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}
