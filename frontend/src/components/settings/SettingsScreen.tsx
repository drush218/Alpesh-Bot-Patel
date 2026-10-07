import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { decideProposal, fetchSettingsStatus, previewAnalysis, saveCredentials, storeAnalysis } from '../../lib/apiClient'
import type { IngestPreview, SettingsStatus } from '../../types/settings'

const fmtDate = (iso: string | null) =>
  iso ? new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'
const fmtDateTime = (iso: string | null) =>
  iso ? `${fmtDate(iso)}, ${new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}` : '—'

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '200px minmax(0,1fr)', gap: 14, padding: '9px 0', borderTop: '1px solid var(--line)', fontSize: 12 }}>
      <span style={{ color: 'var(--ink3)' }}>{label}</span>
      <span style={{ minWidth: 0 }}>{children}</span>
    </div>
  )
}

function Section({ title, note, children }: { title: string; note?: ReactNode; children: ReactNode }) {
  return (
    <section className="an-card" style={{ marginBottom: 14 }}>
      <div className="an-head" style={{ marginBottom: 8 }}>
        <h2>{title}</h2>
        {note && <span className="an-sub">{note}</span>}
      </div>
      {children}
    </section>
  )
}

export function SettingsScreen({ onOpenAnalysis }: { onOpenAnalysis: (ticker: string) => void }) {
  const [status, setStatus] = useState<SettingsStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(() => {
    fetchSettingsStatus().then(setStatus).catch((e) => setError(e.message))
  }, [])
  useEffect(reload, [reload])

  return (
    <main style={{ maxWidth: 760, margin: '0 auto', padding: '24px 20px 80px' }}>
      <h1 style={{ margin: '0 0 16px', fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 22, fontWeight: 600, letterSpacing: '-.01em' }}>
        Settings
      </h1>
      {error && <p style={{ color: 'var(--down)' }}>{error}</p>}
      {!status && !error && <p className="an-sub">Loading…</p>}
      {status && (
        <>
          {status.warnings.map((w) => (
            <p key={w} style={{ color: 'var(--down)', fontSize: 11.5 }}>{w}</p>
          ))}
          <UploadSection onStored={reload} />
          <AnalysesSection status={status} onOpenAnalysis={onOpenAnalysis} />
          <ProposalsSection status={status} onDecided={reload} />
          <CredentialsSection status={status} onSaved={reload} />
          <PipelineSection status={status} />
        </>
      )}
    </main>
  )
}

/* ---------------- upload ---------------- */

interface Pending {
  file: string
  markdown: string
  preview: IngestPreview
  result?: string
  failed?: string
}

function UploadSection({ onStored }: { onStored: () => void }) {
  const [items, setItems] = useState<Pending[]>([])
  const [busy, setBusy] = useState(false)
  const [drag, setDrag] = useState(false)

  const addFiles = async (files: FileList | File[]) => {
    setBusy(true)
    const next: Pending[] = []
    for (const f of Array.from(files)) {
      const markdown = await f.text()
      try {
        next.push({ file: f.name, markdown, preview: await previewAnalysis(markdown, f.name) })
      } catch (e) {
        next.push({ file: f.name, markdown, preview: { ok: false, filename: f.name, errors: [e instanceof Error ? e.message : String(e)] } })
      }
    }
    setItems((prev) => [...prev.filter((p) => !next.some((n) => n.file === p.file)), ...next])
    setBusy(false)
  }

  const store = async (targets: Pending[]) => {
    setBusy(true)
    for (const t of targets) {
      try {
        const r = await storeAnalysis(t.markdown, t.file)
        t.result = r.already_existed ? 'Already on file, not duplicated' : `Stored as the current ${r.ticker} analysis`
      } catch (e) {
        t.failed = e instanceof Error ? e.message : String(e)
      }
    }
    setItems((prev) => [...prev])
    setBusy(false)
    onStored()
  }

  const storable = items.filter((i) => i.preview.ok && i.preview.status !== 'duplicate' && !i.result && !i.failed)

  return (
    <Section title="Add analyses" note="stock-analysis skill output (.md with a stock-model block)">
      <label
        htmlFor="analysis-files"
        onDragOver={(e) => {
          e.preventDefault()
          setDrag(true)
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDrag(false)
          addFiles(e.dataTransfer.files)
        }}
        style={{
          display: 'block',
          border: `1px dashed ${drag ? 'var(--accent)' : 'var(--line2)'}`,
          background: drag ? 'var(--accentSoft)' : 'var(--panel2)',
          borderRadius: 3,
          padding: '18px 14px',
          textAlign: 'center',
          fontSize: 12,
          color: 'var(--ink2)',
          cursor: 'pointer',
        }}
      >
        Drop analysis files here, or <span style={{ color: 'var(--accent)' }}>choose files</span>. Nothing is stored until you confirm.
        <input
          id="analysis-files"
          type="file"
          accept=".md,.markdown,.txt,text/markdown"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files?.length) addFiles(e.target.files)
            e.target.value = ''
          }}
        />
      </label>
      {busy && <p className="an-sub">Working…</p>}

      {items.length > 0 && (
        <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
          {items.map((i) => (
            <PreviewRow key={i.file} item={i} disabled={busy} onStore={() => store([i])} onRemove={() => setItems((p) => p.filter((x) => x !== i))} />
          ))}
          {storable.length > 1 && (
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="an-btn primary" disabled={busy} onClick={() => store(storable)}>
                Store all {storable.length}
              </button>
            </div>
          )}
        </div>
      )}
    </Section>
  )
}

function PreviewRow({ item, disabled, onStore, onRemove }: { item: Pending; disabled: boolean; onStore: () => void; onRemove: () => void }) {
  const p = item.preview
  const statusText =
    p.status === 'new' ? 'new ticker' : p.status === 'replaces' ? `replaces the ${fmtDate(p.replaces_as_of ?? null)} analysis` : 'already on file'
  const last = p.bau_eps?.[p.bau_eps.length - 1]
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 3, padding: '10px 12px', display: 'grid', gap: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', alignItems: 'baseline' }}>
        <span style={{ fontSize: 12.5 }}>
          {p.ok ? (
            <>
              <b>{p.ticker}</b>{' '}
              <span style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", color: 'var(--ink2)' }}>{p.company}</span>{' '}
              <span className="an-sub">· data as of {fmtDate(p.data_as_of ?? null)} · {statusText}</span>
            </>
          ) : (
            <b>{item.file}</b>
          )}
        </span>
        <span className="an-tools">
          {item.result ? (
            <span style={{ fontSize: 11.5, color: 'var(--up)' }}>{item.result}</span>
          ) : item.failed ? (
            <span style={{ fontSize: 11.5, color: 'var(--down)' }}>{item.failed}</span>
          ) : (
            p.ok && p.status !== 'duplicate' && (
              <button className="an-btn primary" disabled={disabled} onClick={onStore}>Store</button>
            )
          )}
          <button className="an-btn" onClick={onRemove}>{item.result ? 'Clear' : 'Remove'}</button>
        </span>
      </div>
      {p.ok ? (
        <span className="an-sub">
          {item.file}
          {last && ` · BAU ${last.year} EPS ${last.eps.toFixed(2)} ${p.currency ?? ''}`} · {p.macro_count} macro links · {p.lever_count} levers ·{' '}
          {p.event_count} calendar events
          {p.proposed_factors?.length ? ` · proposes ${p.proposed_factors.join(', ')}` : ''}
        </span>
      ) : (
        <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11.5, color: 'var(--down)' }}>
          {p.errors.map((e) => <li key={e}>{e}</li>)}
        </ul>
      )}
    </div>
  )
}

/* ---------------- analyses on file ---------------- */

function AnalysesSection({ status, onOpenAnalysis }: { status: SettingsStatus; onOpenAnalysis: (t: string) => void }) {
  const h = status.holdings
  return (
    <Section
      title="Analyses on file"
      note={h.count ? `${h.modelled} of ${h.count} holdings modelled` : `${status.analyses.length} on file`}
    >
      {status.analyses.length === 0 ? (
        <p className="an-sub">None yet. Add one above.</p>
      ) : (
        <div className="an-scroll">
          <table className="an-table" style={{ fontSize: 12 }}>
            <thead>
              <tr>
                <th>Ticker</th>
                <th style={{ textAlign: 'left' }}>Company</th>
                <th>Data as of</th>
                <th>Added</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {status.analyses.map((a) => (
                <tr key={a.ticker}>
                  <td style={{ fontWeight: 600 }}>{a.ticker}</td>
                  <td style={{ textAlign: 'left', fontFamily: "'IBM Plex Sans', system-ui, sans-serif", color: 'var(--ink2)' }}>{a.company ?? '—'}</td>
                  <td>{fmtDate(a.data_as_of)}</td>
                  <td style={{ color: 'var(--ink3)' }}>{fmtDate(a.ingested_at)}</td>
                  <td>
                    {a.is_stale ? (
                      <span title={`Earnings on ${fmtDate(a.last_earnings)} since this was added`} style={{ color: 'var(--accent)' }}>stale</span>
                    ) : (
                      <span style={{ color: 'var(--ink3)' }}>current</span>
                    )}
                  </td>
                  <td>
                    <button className="an-btn" onClick={() => onOpenAnalysis(a.ticker)}>Open ▸</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {h.without_analysis.length > 0 && (
        <p className="an-sub" style={{ marginTop: 10 }}>
          Held without an analysis: {h.without_analysis.join(' · ')}
        </p>
      )}
    </Section>
  )
}

/* ---------------- factor proposals ---------------- */

function ProposalsSection({ status, onDecided }: { status: SettingsStatus; onDecided: () => void }) {
  const [busy, setBusy] = useState<string | null>(null)
  if (status.proposals.length === 0) return null
  const decide = async (code: string, d: 'approve' | 'reject') => {
    setBusy(code)
    try {
      await decideProposal(code, d)
      onDecided()
    } finally {
      setBusy(null)
    }
  }
  return (
    <Section title="Proposed macro factors" note="analyses suggested these; macro links using them stay out of Macro until approved">
      <div style={{ display: 'grid', gap: 8 }}>
        {status.proposals.map((p) => (
          <div key={p.code} style={{ border: '1px solid var(--line)', borderRadius: 3, padding: '10px 12px', display: 'grid', gap: 4 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', alignItems: 'baseline' }}>
              <span style={{ fontSize: 12.5 }}>
                <b>{p.name ?? p.code}</b> <span className="an-sub">{p.code} · {p.scope ?? '—'} · from {p.proposed_by_tickers.join(', ')}</span>
              </span>
              <span className="an-tools">
                <button className="an-btn primary" disabled={busy === p.code} onClick={() => decide(p.code, 'approve')}>Approve</button>
                <button className="an-btn" disabled={busy === p.code} onClick={() => decide(p.code, 'reject')}>Reject</button>
              </span>
            </div>
            {p.rationale && <span style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 12, color: 'var(--ink2)' }}>{p.rationale}</span>}
            {(p.series || p.provider) && <span className="an-sub">series {p.series ?? '—'} · {p.provider ?? '—'}</span>}
          </div>
        ))}
      </div>
    </Section>
  )
}

/* ---------------- credentials ---------------- */

function CredentialsSection({ status, onSaved }: { status: SettingsStatus; onSaved: () => void }) {
  const [open, setOpen] = useState(!status.credentials.saved)
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  return (
    <Section title="Trading212" note="encrypted before storing; never shown again">
      <Row label="API credentials">
        {status.credentials.saved ? <>saved <span className="an-sub">key {status.credentials.key_hint}</span></> : <span style={{ color: 'var(--accent)' }}>not set</span>}
        {status.credentials.saved && !open && (
          <button className="an-btn" style={{ marginLeft: 10 }} onClick={() => setOpen(true)}>Replace</button>
        )}
      </Row>
      {open && (
        <form
          className="an-form"
          style={{ marginTop: 8, marginBottom: 0 }}
          onSubmit={async (e) => {
            e.preventDefault()
            const data = new FormData(e.currentTarget)
            setBusy(true)
            try {
              await saveCredentials(String(data.get('key') ?? ''), String(data.get('secret') ?? ''))
              setMsg('Saved.')
              setOpen(false)
              onSaved()
            } catch (err) {
              setMsg(err instanceof Error ? err.message : String(err))
            } finally {
              setBusy(false)
            }
          }}
        >
          <label htmlFor="t212-key">API key<input id="t212-key" name="key" type="password" autoComplete="off" required /></label>
          <label htmlFor="t212-secret">API secret<input id="t212-secret" name="secret" type="password" autoComplete="off" /></label>
          <button className="an-btn primary" type="submit" disabled={busy}>Save</button>
          {status.credentials.saved && <button className="an-btn" type="button" onClick={() => setOpen(false)}>Cancel</button>}
        </form>
      )}
      {msg && <p className="an-sub" style={{ marginTop: 8 }}>{msg}</p>}
    </Section>
  )
}

/* ---------------- pipeline ---------------- */

function PipelineSection({ status }: { status: SettingsStatus }) {
  return (
    <Section title="Data & pipeline">
      <Row label="Write path">Supabase · analyses, prices, FX, scenarios, scorecards</Row>
      <Row label="Parsed analyses">
        {status.holdings.count ? `${status.holdings.modelled} of ${status.holdings.count} holdings` : status.analyses.length}
      </Row>
      <Row label="Oldest strike date">
        <span style={{ color: status.oldest_strike ? 'var(--accent)' : undefined }}>{fmtDate(status.oldest_strike)}</span>
      </Row>
      <Row label="Prices last fetched">{fmtDateTime(status.prices.last_fetched)} · Yahoo, refreshed on sign-in if over 15 min old</Row>
      {status.prices.unmapped.length > 0 && (
        <Row label="No price symbol">
          <span style={{ color: 'var(--accent)' }}>{status.prices.unmapped.join(' · ')}</span>
          <span className="an-sub"> · needs a Yahoo symbol set by hand</span>
        </Row>
      )}
      <Row label="Deposit history cached">{fmtDateTime(status.deposits_cached_at)} · refreshed after 24h</Row>
      <Row label="Expected-move check">
        index only · 250-day fit (60 minimum) · flag at |z| ≥ 2.5 · results days labelled earnings, not unexplained
      </Row>
      {status.model.length > 0 && (
        <div className="an-scroll" style={{ marginTop: 8 }}>
          <table className="an-table" style={{ fontSize: 11.5 }}>
            <thead>
              <tr><th>Ticker</th><th>Index</th><th>β</th><th>R²</th><th>Daily σ</th><th>Fit window</th></tr>
            </thead>
            <tbody>
              {status.model.map((m) => (
                <tr key={m.ticker}>
                  <td style={{ fontWeight: 600 }}>{m.ticker}</td>
                  <td>{m.index ?? '—'}</td>
                  <td>{m.beta != null ? m.beta.toFixed(2) : '—'}</td>
                  <td style={{ color: m.r2 != null && m.r2 < 0.1 ? 'var(--accent)' : undefined }}>{m.r2 != null ? m.r2.toFixed(2) : '—'}</td>
                  <td>{m.sigma_pct != null ? `${m.sigma_pct.toFixed(1)}%` : '—'}</td>
                  <td style={{ color: 'var(--ink3)' }}>{m.fit_from ? `${fmtDate(m.fit_from)} – ${fmtDate(m.fit_to)} · ${m.n}d` : 'under 60 days of history'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="an-sub" style={{ margin: '6px 0 0' }}>Low R² (amber, under 0.10) means the index explains little of that name's daily moves, so its flags are mostly about company news.</p>
        </div>
      )}
    </Section>
  )
}
