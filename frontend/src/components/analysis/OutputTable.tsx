import { Fragment, useState } from 'react'
import type { WorkspaceResult } from '../../types/analysis'
import { actualYear, currencySymbol, fmt, inputRows, metrics, outYears, signed, stepDp, type InputCell, type InputRow, type Metric, type MetricKey, type OutYear } from '../../lib/modelRows'
import { Cell, type OnEdit } from './InputsTable'
import { SourceNote, sourceTag } from './Drivers'

interface Props {
  result: WorkspaceResult
  compare: boolean
  scenarioLabel: string
  edits: Record<string, number>
  onEdit?: OnEdit // set while editing: driver values become inputs
  editActuals?: boolean // Edit base: the base-year column is editable too
}

type DriverRow = Exclude<InputRow, { group: string }>

/** A driver under its income line: value + source tag (click for the note), or an input while editing. */
function DriverValue({ r, c, edits, onEdit, picked, onPick }: {
  r: DriverRow
  c: InputCell | undefined
  edits: Record<string, number>
  onEdit?: OnEdit // set when this cell is editable
  picked: string | null
  onPick: (path: string) => void
}) {
  if (!c) return null
  if (onEdit) return <Cell path={c.path} base={c.base} step={r.step} source={c.source} note={c.ref} edits={edits} onChange={onEdit} />
  const v = edits[c.path] ?? c.base
  if (v == null) return <span className="dv">—</span>
  const t = sourceTag(c.source, c.ref)
  return (
    <button className={`dr-cell dv${c.path in edits ? ' edited' : ''}${picked === c.path ? ' on' : ''}`} onClick={() => onPick(c.path)}
      title={[t?.name, c.ref].filter(Boolean).join(' · ')}>
      {fmt(v, stepDp(r.step))}{r.unit.startsWith('%') ? '%' : ''}
      <span className={`src-tag src-${t?.tag ?? 'none'}`}>{t?.tag ?? ' '}</span>
    </button>
  )
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

export function OutputTable({ result, compare, scenarioLabel, edits, onEdit, editActuals }: Props) {
  const { price, actual, base_inputs } = result
  const sym = currencySymbol(base_inputs.meta.reporting_currency)
  const priceLabel = price ? `${currencySymbol(price.currency)}${price.close.toFixed(2)}` : 'current price'
  const rows = metrics(sym, priceLabel)
  const years = base_inputs.meta.forecast_years
  const base = outYears(result.base_outputs, actual, price)
  const cur = result.outputs ? outYears(result.outputs, actual, price) : base
  const act = actualYear(actual, price)
  const actLabel = `${actual.year}A`
  const drivers = inputRows(base_inputs).filter((r): r is DriverRow => !('group' in r))
  const [picked, setPicked] = useState<string | null>(null)
  const pick = (path: string) => setPicked((p) => (p === path ? null : path))
  const pickable = drivers.flatMap((r) => [
    ...(r.actual ? [{ cell: r.actual, label: r.label, year: actLabel, step: r.step, unit: r.unit }] : []),
    ...r.cells.map((cell, i) => ({ cell, label: r.label, year: years[i], step: r.step, unit: r.unit })),
  ])
  const [open, setOpen] = useState<Set<MetricKey>>(new Set()) // drivers hidden until a line is clicked; all shown while editing
  const toggle = (k: MetricKey) => setOpen((o) => {
    const next = new Set(o)
    if (next.has(k)) next.delete(k)
    else next.add(k)
    return next
  })
  const dv = (r: DriverRow, i: number) => <DriverValue r={r} c={r.cells[i]} edits={edits} onEdit={onEdit} picked={picked} onPick={pick} />
  const check = actual.eps_check_pct

  return (
    <>
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
          {rows.map((m) => {
            const own = drivers.filter((r) => r.under === m.key)
            const expandable = own.length > 0 && !onEdit
            const shown = !!onEdit || open.has(m.key)
            return (
            <Fragment key={m.label}>
            <tr className={[m.pe ? 'pe' : '', expandable ? 'exp' : ''].join(' ').trim() || undefined} onClick={expandable ? () => toggle(m.key) : undefined}>
              <td className="lbl">
                {expandable ? (
                  <button className="exp-btn" aria-expanded={shown}><span className="caret">{shown ? '▾' : '▸'}</span>{m.label}</button>
                ) : m.label}
              </td>
              <td className="act">
                <Value m={m} r={act} />
                {m.key === 'eps' && check != null && Math.abs(check) > 2 && (
                  <span className="s down" title={`Calculated EPS is ${signed(check)}% vs the reported ${fmt(actual.reported_eps, 2)}`}>
                    {signed(check)}% vs rep.
                  </span>
                )}
              </td>
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
            {shown && own.map((r) => (
              <tr key={r.label} className="drv">
                <td className="lbl">{r.label}{!r.unit.startsWith('%') && <span className="u">{r.unit}</span>}</td>
                <td className="act">
                  <DriverValue r={r} c={r.actual} edits={edits} onEdit={editActuals ? onEdit : undefined} picked={picked} onPick={pick} />
                </td>
                {years.map((y, i) =>
                  compare
                    ? [
                        <td key={`${y}b`} className="base" />,
                        <td key={`${y}s`}>{dv(r, i)}</td>,
                        <td key={`${y}d`} />,
                      ]
                    : <td key={y}>{dv(r, i)}</td>,
                )}
              </tr>
            ))}
            </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
    {!onEdit && (
      <SourceNote
        picked={pickable.find((p) => p.cell.path === picked) ?? null}
      />
    )}
    </>
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
