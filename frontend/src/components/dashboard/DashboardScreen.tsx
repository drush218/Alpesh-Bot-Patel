import { useEffect, useState } from 'react'
import { fetchAccount } from '../../lib/apiClient'
import type { AccountSummary } from '../../types/account'
import { AccountStrip } from './AccountStrip'

export function DashboardScreen() {
  const [account, setAccount] = useState<AccountSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAccount()
      .then(setAccount)
      .catch((e) => setError(e.message || 'Failed to load account'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <main style={mainStyle}>
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 14,
          flexWrap: 'wrap',
          marginBottom: 16,
        }}
      >
        <h1
          style={{
            margin: 0,
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: '-.012em',
          }}
        >
          Dashboard
        </h1>
        <span style={{ color: 'var(--ink3)', fontSize: 11 }}>Trading212 live, GBP</span>
      </div>

      {loading && <p style={{ color: 'var(--ink3)' }}>Loading… (first load scans your deposit history and can take a minute)</p>}
      {error && <p style={{ color: 'var(--down)' }}>{error}</p>}
      {account && (
        <>
          {account.warnings.map((w) => (
            <p key={w} style={{ color: 'var(--down)', fontSize: 11 }}>{w}</p>
          ))}
          <AccountStrip account={account} />
        </>
      )}
    </main>
  )
}

const mainStyle = {
  maxWidth: 1240,
  margin: '0 auto',
  padding: '26px 20px 80px',
} as const
