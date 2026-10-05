import type { WorkspaceResult } from '../../types/analysis'
import { actualYear, currencySymbol, fmt, metrics, outYears, signed, type Metric, type OutYear } from '../../lib/modelRows'

interface Props {
  result: WorkspaceResult
  compare: boolean
  scenarioLabel: string
}

// A change that rounds to zero at the shown precision is no change.
const isZero = (d: number | null, dp: number) => d == null || Math.abs(d) < 0.5 * 10 ** -dp

function tone(d: number | null, dp: number, good: 1 | -1 = 1) {
  if (isZero(d, dp)) return 'flat'
  return d! * good > 0 ? 'up' : 'down'
}

function Value({ m, r }: { m: Metric; r: OutYear }) {
  const v = m.main(r)
  const s = m.sub?.(r)
  return (
    <>
      <span className="v">{fmt(v, m.mainDp)}</span>
      {m.sub && <span className="s">{s == null ? ' ' : m.subSigned ? `${signed(s)}%` : `${fmt(s)}%`}</span>}
    </>
  )
}

function Delta({ m, base, cur }: { m: Metric; base: OutYear; cur: OutYear }) {
  const b = m.main(base), c = m.main(cur)
  const d = b == null || c == null ? null : c - b
  const sb = m.sub?.(base), sc = m.sub?.(cur)
  const sd = sb == null || sc == null ? null : sc - sb
  return (
    <>
      <span className={`v ${tone(d, m.mainDp, m.good)}`}>{isZero(d, m.mainDp) ? '·' : signed(d, m.mainDp)}</span>
      {m.sub && (
        <span className={`s ${tone(sd, 1, m.subGood)}`}>{isZero(sd, 1) ? '·' : `${signed(sd)}pp`}</span>
      )}
    </>
  )
}

export function OutputTable({ result, compare, scenarioLabel }: Props) {
  const { price, actual, base_inputs } = result
  const sym = currencySymbol(base_inputs.meta.reporting_currency)
  const priceLabel = price ? `${currencySymbol(price.currency)}${price.close.toFixed(2)}` : 'current price'
  const rows = metrics(sym, priceLabel)
  const years = base_inputs.meta.forecast_years
  const base = outYears(result.base_outputs, actual, price)
  const cur = result.outputs ? outYears(result.outputs, actual, price) : base
  const act = actualYear(actual)
  const actLabel = `${actual.year}A`

  return (
    <div className="an-scroll">
      <table className="an-table an-out" aria-label="Model outputs">
        <thead>
          {compare ? (
            <>
              <tr className="yrs">
                <th />
                <th className="act span">actual</th>
                {years.map((y) => (
                  <th key={y} colSpan={3} className="span">{y}</th>
                ))}
              </tr>
              <tr>
                <th />
                <th className="act">{actLabel}</th>
                {years.map((y) => [
                  <th key={`${y}b`}>base</th>,
                  <th key={`${y}s`}>{scenarioLabel}</th>,
                  <th key={`${y}d`}>Δ</th>,
                ])}
              </tr>
            </>
          ) : (
            <tr>
              <th />
              <th className="act">{actLabel}</th>
              {years.map((y) => (
                <th key={y}>{y}</th>
              ))}
            </tr>
          )}
        </thead>
        <tbody>
          {rows.map((m) => (
            <tr key={m.label} className={m.pe ? 'pe' : undefined}>
              <td className="lbl">{m.label}</td>
              <td className="act"><Value m={m} r={act} /></td>
              {years.map((y, i) =>
                compare
                  ? [
                      <td key={`${y}b`} className="base"><Value m={m} r={base[i]} /></td>,
                      <td key={`${y}s`}><Value m={m} r={cur[i]} /></td>,
                      <td key={`${y}d`}><Delta m={m} base={base[i]} cur={cur[i]} /></td>,
                    ]
                  : <td key={y}><Value m={m} r={cur[i]} /></td>,
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function EpsBand({ result }: { result: WorkspaceResult }) {
  const out = result.outputs ?? result.base_outputs
  const last = out.scenarios.bau.length - 1
  const sym = currencySymbol(result.base_inputs.meta.reporting_currency)
  const year = result.base_inputs.meta.forecast_years[last]
  return (
    <div className="an-band">
      <span>{year} EPS range</span>
      <span>low <b>{sym}{fmt(out.scenarios.low[last].eps, 2)}</b></span>
      <span>BAU <b>{sym}{fmt(out.scenarios.bau[last].eps, 2)}</b></span>
      <span>high <b>{sym}{fmt(out.scenarios.high[last].eps, 2)}</b></span>
    </div>
  )
}
