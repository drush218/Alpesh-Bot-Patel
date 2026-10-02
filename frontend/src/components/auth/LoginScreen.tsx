import { useState, type FormEvent, type CSSProperties } from 'react'
import { useAuth } from '../../contexts/AuthContext'

export function LoginScreen() {
  const { signIn } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    const { error } = await signIn(email, password)
    setSubmitting(false)
    if (error) setError(error)
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          width: 320,
          border: '1px solid var(--line)',
          background: 'var(--panel)',
          borderRadius: 4,
          padding: '24px 22px',
          boxShadow: 'var(--shadow)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 9, marginBottom: 22 }}>
          <span style={{ fontWeight: 600, letterSpacing: '.14em', fontSize: 11, color: 'var(--accent)' }}>
            PORTFOLIO
          </span>
          <span style={{ fontWeight: 400, letterSpacing: '.14em', fontSize: 11, color: 'var(--ink3)' }}>
            TERMINAL
          </span>
        </div>

        <label style={{ display: 'block', fontSize: 10, letterSpacing: '.08em', color: 'var(--ink3)', textTransform: 'uppercase', marginBottom: 6 }}>
          Email
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={inputStyle}
        />

        <label style={{ display: 'block', fontSize: 10, letterSpacing: '.08em', color: 'var(--ink3)', textTransform: 'uppercase', margin: '14px 0 6px' }}>
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={inputStyle}
        />

        {error && (
          <p style={{ color: 'var(--down)', fontSize: 11.5, marginTop: 12, marginBottom: 0 }}>{error}</p>
        )}

        <button
          type="submit"
          disabled={submitting}
          style={{
            marginTop: 20,
            width: '100%',
            fontFamily: 'inherit',
            fontSize: 12,
            padding: '9px',
            border: '1px solid var(--accent)',
            background: 'var(--accentSoft)',
            color: 'var(--accent)',
            borderRadius: 3,
            cursor: submitting ? 'default' : 'pointer',
            opacity: submitting ? 0.6 : 1,
          }}
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}

const inputStyle: CSSProperties = {
  width: '100%',
  fontFamily: 'inherit',
  fontSize: 13,
  padding: '8px 10px',
  border: '1px solid var(--line2)',
  background: 'var(--bg)',
  color: 'var(--ink)',
  borderRadius: 3,
}
