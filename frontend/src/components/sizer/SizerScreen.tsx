import { useEffect, useState, type ReactNode } from 'react'
import { fetchSizerContext, type SizerContext } from '../../lib/apiClient'
import { formatGbp } from '../../lib/format'
import { currencySymbol } from '../../lib/modelRows'
import { size, type Macd } from '../../lib/sizer'

const HISTORY_KEY = 'pt.sizerRuns'
const MACD_LABELS = ['weak', 'neutral', 'strong'] as const

interface Run {
  at: string
  ticker: string
  detail: string
  sized: number
}

function readRuns(): Run[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]')
  } catch {
    return []
  }
}

function readMultiple() {
  try {
    const v = Number(localStorage.getItem('pt.referenceMultiple'))
    return [25, 30, 35, 40].includes(v) ? v : 30
  } catch {
    return 30
  }
}

function Field({ id, label, hint, children }: { id: string; label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label htmlFor={id} style={{ display: 'block' }}>
      <span className="an-micro" style={{ display: 'block', marginBottom: 5 }}>{label}</span>
      {children}
      {hint && <span className="an-sub" style={{ display: 'block', marginTop: 4 }}>{hint}</span>}
    </label>
  )
}

const inputStyle = {
  width: '100%',
  font: 'inherit',
  fontSize: 15,
  padding: '8px 10px',
  background: 'var(--panel2)',
  border: '1px solid var(--line2)',
  color: 'var(--ink)',
  borderRadius: 3,
} as const

function MacdPicker({ label, value, onChange }: { label: string; value: Macd; onChange: (v: Macd) => void }) {
  return (
    <div>
      <span className="an-micro" style={{ display: 'block', marginBottom: 5 }}>{label}</span>
      <div role="radiogroup" aria-label={label} style={{ display: 'flex', border: '1px solid var(--line2)', borderRadius: 3, overflow: 'hidden' }}>
        {MACD_LABELS.map((l, v) => (
          <button
            key={l}
            role="radio"
            aria-checked={v === value}
            onClick={() => onChange(v as Macd)}
            style={{ flex: 1, border: 0, padding: '7px 0', fontSize: 11.5, cursor: 'pointer', background: v === value ? 'var(--accent)' : 'transparent', color: v === value ? 'var(--bg)' : 'var(--ink2)', fontWeight: v === value ? 600 : 400 }}
          >
            {l}
          </button>
        ))}
      </div>
    </div>
  )
}

export function SizerScreen({ initialTicker }: { initialTicker: string | null }) {
  const [tickerInput, setTickerInput] = useState(initialTicker ?? '')
  const [ctx, setCtx] = useState<SizerContext | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [price, setPrice] = useState(0)
  const [target, setTarget] = useState(0)
  const [stop, setStop] = useState(0)
  const [book, setBook] = useState(0)
  const [maxLossPct, setMaxLossPct] = useState(1)
  const [macdM, setMacdM] = useState<Macd>(0)
  const [macdW, setMacdW] = useState<Macd>(0)
  const [stepsOpen, setStepsOpen] = useState(false)
  const [runs, setRuns] = useState<Run[]>(readRuns)
  const [year, setYear] = useState<number>(-1)
  const mult = readMultiple()

  const load = async (t: string) => {
    if (!t.trim()) return
    setLoading(true)
    setError(null)
    try {
      const c = await fetchSizerContext(t.trim())
      setCtx(c)
      if (c.price != null) {
        setPrice(+c.price.toFixed(2))
        setTarget(+(c.price * 1.25).toFixed(2))
        setStop(+(c.price * 0.9).toFixed(2))
      }
      if (c.book) setBook(+c.book.conservative_gbp.toFixed(2))
      setYear(c.analysis ? c.analysis.years.length - 1 : -1)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (initialTicker) load(initialTicker)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialTicker])

  const fx = ctx?.fx_to_gbp ?? 0
  const r = size({ price, target, stop, fxToGbp: fx, bookGbp: book, maxLossPct, macdMonthly: macdM, macdWeekly: macdW })
  const pence = ctx?.currency === 'GBp' || ctx?.currency === 'GBX'
  const sym = currencySymbol(ctx?.currency ?? undefined)
  const money = (v: number | null | undefined) => (v == null ? '—' : pence ? `${v.toFixed(2)}p` : `${sym}${v.toFixed(2)}`)
  const unit = pence ? 'pence' : ctx?.currency ?? '—'
  const an = ctx?.analysis
  const bandAt = (k: 'low' | 'high') => (an && year >= 0 ? an.eps[k][year] * mult * an.fx : null)
  const low = bandAt('low'), high = bandAt('high')
  const held = ctx?.held?.value_gbp ?? 0

  const saveRun = () => {
    const run: Run = {
      at: new Date().toISOString(),
      ticker: ctx?.ticker ?? tickerInput.toUpperCase(),
      detail: `${money(price)} → ${money(target)} / stop ${money(stop)} · ${maxLossPct.toFixed(1)}% · MACD ${macdM}+${macdW}`,
      sized: r.sized,
    }
    const next = [run, ...runs].slice(0, 12)
    setRuns(next)
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
    } catch {
      /* per-browser history only */
    }
  }

  const steps: [string, string, string][] = [
    ['Implied upside', `(${money(target)} − ${money(price)}) ÷ ${money(price)}`, `${(r.up * 100).toFixed(2)}%`],
    ['Implied downside', `(${money(stop)} − ${money(price)}) ÷ ${money(price)}`, `${(r.down * 100).toFixed(2)}%`],
    ['Risk / reward', 'upside ÷ downside', `${r.rr.toFixed(2)} : 1`],
    ['Max acceptable loss', `${maxLossPct.toFixed(1)}% × ${formatGbp(book)}`, formatGbp(r.maxLoss)],
    ['MACD score → downside risk factor', `monthly ${macdM} + weekly ${macdW} = ${r.score}`, `${r.downsideRisk.toFixed(1)}×`],
    ['Adjustment factor', `upside reward ${r.upsideReward.toFixed(3)} ÷ downside risk ${r.downsideRisk.toFixed(1)}`, r.adj.toFixed(3)],
    ['Base → adjusted investment', `${formatGbp(r.base)} × ${r.adj.toFixed(3)}`, formatGbp(r.sized)],
  ]

  return (
    <main style={{ maxWidth: 1240, margin: '0 auto', padding: '24px 20px 80px' }}>
      <h1 style={{ margin: '0 0 14px', fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 22, fontWeight: 600, letterSpacing: '-.01em' }}>
        Position sizer {ctx && <span style={{ color: 'var(--ink3)', fontWeight: 400, fontSize: 15 }}>· {ctx.ticker}</span>}
      </h1>

      <form
        className="an-form"
        style={{ maxWidth: 520, background: 'transparent', border: 0, padding: 0 }}
        onSubmit={(e) => {
          e.preventDefault()
          load(tickerInput)
        }}
      >
        <label htmlFor="sizer-ticker">
          Ticker
          <input id="sizer-ticker" value={tickerInput} onChange={(e) => setTickerInput(e.target.value.toUpperCase())} placeholder="e.g. BROS, MSFT, GRG.L" />
        </label>
        <button className="an-btn primary" type="submit" disabled={loading || !tickerInput.trim()}>{loading ? 'Loading…' : 'Load'}</button>
      </form>
      {error && <p style={{ color: 'var(--down)' }}>{error}</p>}
      {ctx?.warnings.map((w) => <p key={w} style={{ color: 'var(--down)', fontSize: 11.5 }}>{w}</p>)}

      {ctx && (
        <>
          <section className="an-card" style={{ borderTop: '2px solid var(--accent)', margin: '14px 0' }}>
            <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
              <div>
                <div className="an-micro">price now</div>
                <div style={{ fontSize: 17, fontWeight: 600 }}>{ctx.price != null ? `${money(ctx.price)}` : '—'}</div>
                <div className="an-sub">{fx ? `${formatGbp(price * fx)} · ${ctx.currency}→GBP ${fx.toFixed(4)}` : 'no GBP rate'}</div>
              </div>
              {an ? (
                <div>
                  <div className="an-micro">band {an.years[year]} at {mult}×</div>
                  <div style={{ fontSize: 17, fontWeight: 600, color: 'var(--accent)' }}>
                    {low != null && high != null ? (price > high ? 'above HIGH' : price < low ? 'below LOW' : 'inside band') : '—'}
                  </div>
                  <div className="an-sub">LOW {money(low)} · HIGH {money(high)} · analysis {an.data_as_of}</div>
                </div>
              ) : (
                <div>
                  <div className="an-micro">analysis</div>
                  <div style={{ fontSize: 13, color: 'var(--ink3)' }}>none on file, so no band to seed from</div>
                </div>
              )}
              <div>
                <div className="an-micro">held now</div>
                <div style={{ fontSize: 17, fontWeight: 600 }}>{held ? formatGbp(held) : '—'}</div>
                <div className="an-sub">{held && book ? `${((held / book) * 100).toFixed(1)}% of book` : 'not held'}</div>
              </div>
            </div>
            {an && low != null && high != null && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14, paddingTop: 13, borderTop: '1px solid var(--line)', alignItems: 'center' }}>
                <button className="an-btn" onClick={() => setTarget(+high.toFixed(2))}>use HIGH {money(high)} as target</button>
                <button className="an-btn" onClick={() => setStop(+low.toFixed(2))}>use LOW {money(low)} as stop</button>
                <select className="an-select" aria-label="Band year" value={year} onChange={(e) => setYear(Number(e.target.value))}>
                  {an.years.map((y, i) => <option key={y} value={i}>{y}</option>)}
                </select>
                <span className="an-sub">at {mult}×, change the reference multiple on the analysis screen</span>
              </div>
            )}
          </section>

          <div className="an-grid">
            <div style={{ minWidth: 0, display: 'grid', gap: 14 }}>
              <section className="an-card">
                <h2 style={{ marginBottom: 12 }}>Trade inputs</h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
                  <Field id="sz-price" label={`current price (${unit})`} hint="from Yahoo, editable">
                    <input id="sz-price" type="number" step={0.01} value={price} onChange={(e) => setPrice(+e.target.value || 0)} style={inputStyle} />
                  </Field>
                  <Field id="sz-target" label={`price target (${unit})`} hint={`implied upside ${(r.up * 100).toFixed(1)}%`}>
                    <input id="sz-target" type="number" step={0.01} value={target} onChange={(e) => setTarget(+e.target.value || 0)} style={inputStyle} />
                  </Field>
                  <Field id="sz-stop" label={`stop loss (${unit})`} hint={`implied downside ${(r.down * 100).toFixed(1)}%`}>
                    <input id="sz-stop" type="number" step={0.01} value={stop} onChange={(e) => setStop(+e.target.value || 0)} style={inputStyle} />
                  </Field>
                  <Field id="sz-book" label="book value (GBP)" hint="lower of cost and market value, plus cash">
                    <input id="sz-book" type="number" step={100} value={book} onChange={(e) => setBook(+e.target.value || 0)} style={inputStyle} />
                  </Field>
                </div>
                <div style={{ marginTop: 14 }}>
                  <Field id="sz-maxloss" label={`max acceptable loss · ${maxLossPct.toFixed(1)}% of book = ${formatGbp(r.maxLoss)}`}>
                    <input id="sz-maxloss" type="range" min={0.1} max={5} step={0.1} value={maxLossPct} onChange={(e) => setMaxLossPct(+e.target.value)} style={{ width: '100%', accentColor: 'var(--accent)' }} />
                  </Field>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, marginTop: 14 }}>
                  <MacdPicker label="MACD monthly" value={macdM} onChange={setMacdM} />
                  <MacdPicker label="MACD weekly" value={macdW} onChange={setMacdW} />
                </div>
              </section>

              <section className="an-card">
                <button onClick={() => setStepsOpen((o) => !o)} aria-expanded={stepsOpen} style={{ background: 'transparent', border: 0, padding: 0, cursor: 'pointer', display: 'flex', gap: 8, alignItems: 'baseline', color: 'var(--ink)' }}>
                  <span style={{ color: 'var(--accent)' }}>{stepsOpen ? '▾' : '▸'}</span>
                  <h2>Step-by-step breakdown</h2>
                  <span className="an-sub">7 steps, same arithmetic as the calculator</span>
                </button>
                {stepsOpen && (
                  <div style={{ marginTop: 12, display: 'grid', gap: 0 }}>
                    {steps.map(([label, work, out], i) => (
                      <div key={label} style={{ display: 'grid', gridTemplateColumns: '22px minmax(0,1fr) auto', gap: 10, padding: '8px 0', borderTop: '1px solid var(--line)', fontSize: 12 }}>
                        <span style={{ color: 'var(--ink3)' }}>{i + 1}</span>
                        <span>
                          {label}
                          <span className="an-sub" style={{ display: 'block' }}>{work}</span>
                        </span>
                        <b style={{ fontWeight: 600 }}>{out}</b>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>

            <aside>
              <section style={{ border: '1px solid var(--accent)', background: 'var(--accentSoft)', borderRadius: 4, padding: '16px 17px' }}>
                {r.errors.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: 16, color: 'var(--down)', fontSize: 12 }}>{r.errors.map((e) => <li key={e}>{e}</li>)}</ul>
                ) : (
                  <>
                    <div className="an-micro">suggested position</div>
                    <div style={{ fontSize: 23, fontWeight: 600, letterSpacing: '-.015em' }}>{formatGbp(r.sized)}</div>
                    <div className="an-sub">{r.shares.toFixed(1)} shares · {((r.sized / book) * 100).toFixed(1)}% of book{held ? ` · ${(((held + r.sized) / book) * 100).toFixed(1)}% with what you hold` : ''}</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 14px', marginTop: 14 }}>
                      <div><div className="an-micro">loss if stopped</div><div style={{ fontSize: 15 }}>{formatGbp(r.lossIfStopped)}</div></div>
                      <div><div className="an-micro">book risk</div><div style={{ fontSize: 15 }}>{r.bookRisk.toFixed(2)}%</div></div>
                      <div><div className="an-micro">R:R</div><div style={{ fontSize: 15, color: r.rr < 2 ? 'var(--down)' : 'var(--up)' }}>{r.rr.toFixed(2)} : 1</div></div>
                      <div><div className="an-micro">adj. factor</div><div style={{ fontSize: 15 }}>{r.adj.toFixed(3)}</div></div>
                    </div>
                    {r.rr < 2 && <p style={{ margin: '12px 0 0', fontSize: 11.5, color: 'var(--down)' }}>Weak risk/reward ({r.rr.toFixed(2)} : 1). At least 2 : 1 is the usual bar.</p>}
                    <button className="an-btn" style={{ marginTop: 12, width: '100%', borderColor: 'var(--accent)', color: 'var(--accent)' }} onClick={saveRun}>Save sizer run</button>
                  </>
                )}
              </section>
              <section className="an-card">
                <div className="an-micro" style={{ marginBottom: 6 }}>sizer history · this browser</div>
                {runs.length === 0 && <span className="an-sub">No saved runs yet.</span>}
                {runs.map((run) => (
                  <div key={run.at} style={{ display: 'grid', gridTemplateColumns: '64px 1fr auto', gap: 8, padding: '6px 0', borderBottom: '1px solid var(--line)', fontSize: 11.5, color: 'var(--ink2)' }}>
                    <span style={{ color: 'var(--ink3)' }}>{new Date(run.at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}</span>
                    <span><b style={{ color: 'var(--ink)', fontWeight: 600 }}>{run.ticker}</b> {run.detail}</span>
                    <span style={{ color: 'var(--ink)' }}>{formatGbp(run.sized)}</span>
                  </div>
                ))}
              </section>
            </aside>
          </div>
        </>
      )}
    </main>
  )
}
