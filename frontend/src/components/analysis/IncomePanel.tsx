import { useEffect, useState } from 'react'
import { clearDividend, fetchDividend, saveDividend } from '../../lib/apiClient'
import { currencySymbol, fmt, signed } from '../../lib/modelRows'
import type { DividendInput, DividendMode, DividendResponse, ModelOutputs, Price } from '../../types/analysis'

const MODES: [DividendMode, string][] = [
  ['per_payment', 'Per payment'],
  ['half', 'Half-year'],
  ['annual', 'Annual total'],
  ['uneven', 'Uneven'],
]
const FREQS: [number, string][] = [[1, 'yearly'], [2, 'twice a year'], [4, 'quarterly'], [12, 'monthly']]

const blank = (): DividendInput => ({ mode: 'per_payment', amount: null, frequency: 4, payments: [] })

/** What the form adds up to, before it's saved. */
function annual(d: DividendInput): number | null {
  if (d.mode === 'uneven') return d.payments.length ? d.payments.reduce((a, b) => a + b, 0) : null
  if (d.amount == null) return null
  return d.mode === 'per_payment' ? d.amount * (d.frequency ?? 1) : d.mode === 'half' ? d.amount * 2 : d.amount
}

const num = (s: string) => (s.trim() === '' || !(Number(s) >= 0) ? null : Number(s))

interface Props {
  ticker: string
  outputs: ModelOutputs
  years: string[]
  baseShares: number
  price: Price | null
}

export function IncomePanel({ ticker, outputs, years, baseShares, price }: Props) {
  const [data, setData] = useState<DividendResponse | null>(null)
  const [form, setForm] = useState<DividendInput>(blank)
  const [amountText, setAmountText] = useState('')
  const [payText, setPayText] = useState<string[]>([])
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const adopt = (res: DividendResponse) => {
    setData(res)
    const inp = res.input ?? blank()
    setForm({ ...inp, frequency: inp.frequency ?? 4, payments: inp.payments ?? [] })
    setAmountText(inp.amount != null ? String(inp.amount) : '')
    setPayText((inp.payments ?? []).map(String))
    setDirty(false)
  }

  useEffect(() => {
    fetchDividend(ticker).then(adopt).catch((e) => setError(e.message))
  }, [ticker])

  const edit = (next: DividendInput) => {
    setForm(next)
    setDirty(true)
  }
  const setPayments = (texts: string[]) => {
    setPayText(texts)
    edit({ ...form, payments: texts.map(num).filter((v): v is number => v != null) })
  }

  const run = (p: Promise<DividendResponse>) => p.then(adopt).catch((e) => setError(e instanceof Error ? e.message : String(e)))

  const psym = currencySymbol(price?.currency)
  const dps = dirty ? annual(form) : data?.annual_dps ?? null
  const divYield = dps != null && price ? (dps / price.close) * 100 : null
  const bau = outputs.scenarios.bau
  const fx = price?.fx ?? null
  const rows = bau.map((r, i) => {
    const prevShares = i === 0 ? baseShares : bau[i - 1].shares_diluted
    const buyback = prevShares ? (1 - r.shares_diluted / prevShares) * 100 : null
    const payout = dps != null && fx != null && r.eps > 0 ? (dps / (r.eps * fx)) * 100 : null
    return { payout, buyback, total: buyback != null ? (divYield ?? 0) + buyback : null }
  })
  const canSave = dirty && annual(form) != null

  return (
    <div>
      <div className="inc-form">
        <select className="an-select" value={form.mode} aria-label="How the dividend is entered"
          onChange={(e) => edit({ ...form, mode: e.target.value as DividendMode })}>
          {MODES.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>

        {form.mode !== 'uneven' && (
          <label className="inc-amt">
            <span>{psym}</span>
            <input type="number" min={0} step="any" value={amountText} placeholder="0.00" aria-label="Dividend amount"
              onWheel={(e) => e.currentTarget.blur()}
              onChange={(e) => {
                setAmountText(e.target.value)
                edit({ ...form, amount: num(e.target.value) })
              }} />
          </label>
        )}
        {form.mode === 'per_payment' && (
          <select className="an-select" value={form.frequency ?? 4} aria-label="Payments per year"
            onChange={(e) => edit({ ...form, frequency: Number(e.target.value) as DividendInput['frequency'] })}>
            {FREQS.map(([n, l]) => <option key={n} value={n}>{l}</option>)}
          </select>
        )}
        {form.mode === 'uneven' && (
          <div className="inc-pays">
            {payText.map((t, i) => (
              <label key={i} className="inc-amt">
                <span>{psym}</span>
                <input type="number" min={0} step="any" value={t} aria-label={`Payment ${i + 1}`}
                  onWheel={(e) => e.currentTarget.blur()}
                  onChange={(e) => setPayments(payText.map((x, j) => (j === i ? e.target.value : x)))} />
                <button className="sc-remove" aria-label={`Remove payment ${i + 1}`} onClick={() => setPayments(payText.filter((_, j) => j !== i))}>×</button>
              </label>
            ))}
            <button className="an-btn" onClick={() => setPayments([...payText, ''])}>+ Payment</button>
          </div>
        )}

        <div className="an-tools" style={{ marginLeft: 'auto' }}>
          {data?.input && <button className="an-btn danger" onClick={() => run(clearDividend(ticker))}>Clear</button>}
          <button className="an-btn primary" disabled={!canSave} onClick={() => run(saveDividend(ticker, form))}>Save</button>
        </div>
      </div>
      {error && <p className="an-sub" style={{ color: 'var(--down)' }}>{error}</p>}

      <div className="inc-stats">
        <div>
          <div className="an-micro">Dividend / share</div>
          <div className="inc-big">{dps != null ? `${psym}${fmt(dps, 2)}` : '—'}</div>
          <div className="an-sub">
            {data?.yahoo_ttm != null ? `Yahoo trailing 12m ${psym}${fmt(data.yahoo_ttm, 2)}` : 'No Yahoo history'}
          </div>
        </div>
        <div>
          <div className="an-micro">Dividend yield</div>
          <div className="inc-big">{divYield != null ? `${fmt(divYield, 2)}%` : '—'}</div>
          <div className="an-sub">at {psym}{price ? price.close.toFixed(2) : '—'}{dirty && ' · unsaved'}</div>
        </div>
      </div>

      <div className="an-scroll">
        <table className="an-table an-out" aria-label="Income by forecast year">
          <thead>
            <tr><th />{years.map((y) => <th key={y}>{y}</th>)}</tr>
          </thead>
          <tbody>
            <tr>
              <td className="lbl">Payout ratio<span className="u">dividend ÷ BAU EPS</span></td>
              {rows.map((r, i) => <td key={years[i]}><span className="v">{r.payout != null ? `${fmt(r.payout, 0)}%` : '—'}</span></td>)}
            </tr>
            <tr>
              <td className="lbl">Buyback yield<span className="u">fall in share count</span></td>
              {rows.map((r, i) => <td key={years[i]}><span className="v">{r.buyback != null ? `${signed(r.buyback, 1)}%` : '—'}</span></td>)}
            </tr>
            <tr className="pe">
              <td className="lbl">Shareholder yield<span className="u">dividend + buyback</span></td>
              {rows.map((r, i) => <td key={years[i]}><span className="v">{r.total != null ? `${fmt(r.total, 1)}%` : '—'}</span></td>)}
            </tr>
          </tbody>
        </table>
      </div>
      <p className="an-sub" style={{ margin: '6px 0 0' }}>
        Dividend held flat at your figure across the forecast. A negative buyback yield means the share count is rising (dilution).
      </p>
    </div>
  )
}
