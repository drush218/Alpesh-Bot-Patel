import { useState } from 'react'
import { fmt, inputRows } from '../../lib/modelRows'
import type { ModelInputs } from '../../types/analysis'

const OPEN_KEY = 'pt.driversOpen'

/** One tag per input cell: G guidance, F filing / reported share change, A assumption, E edited by you. */
export function sourceTag(source?: string, ref?: string): { tag: string; name: string } | null {
  if (ref?.startsWith('Edited in Portfolio Terminal')) return { tag: 'E', name: 'edited by you' }
  if (source === 'guidance') return { tag: 'G', name: 'guidance' }
  if (source === 'filing' || source === 'buyback_executed' || source === 'issuance_declared' || source === 'issuance_and_buyback')
    return { tag: 'F', name: source === 'filing' ? 'filing' : source.replace(/_/g, ' ') }
  if (source === 'assumption') return { tag: 'A', name: 'assumption' }
  return null
}

function loadOpen() {
  try {
    return localStorage.getItem(OPEN_KEY) !== '0'
  } catch {
    return true
  }
}

/** Read-only drivers under the income statement: every input with its source tag; click a value for the note. */
export function Drivers({ inputs }: { inputs: ModelInputs }) {
  const [open, setOpenState] = useState(loadOpen)
  const [picked, setPicked] = useState<string | null>(null)
  const years = inputs.meta.forecast_years
  const rows = inputRows(inputs)

  const cells = rows.flatMap((r) =>
    'group' in r ? [] : r.cells.map((c, i) => ({ ...c, label: r.label, year: years[i], step: r.step, unit: r.unit, tag: sourceTag(c.source, c.ref) })),
  )
  const counts: Record<string, number> = {}
  for (const c of cells) {
    if (!c.tag) continue
    const k = c.tag.tag === 'F' ? 'reported' : c.tag.name
    counts[k] = (counts[k] ?? 0) + 1
  }
  const mix = (['guidance', 'reported', 'assumption', 'edited by you'] as const)
    .filter((k) => counts[k])
    .map((k) => `${counts[k]} ${k === 'assumption' && counts[k] > 1 ? 'assumptions' : k}`)
    .join(' · ')

  const setOpen = (v: boolean) => {
    setOpenState(v)
    try {
      localStorage.setItem(OPEN_KEY, v ? '1' : '0')
    } catch {
      /* per-browser convenience only */
    }
  }

  const d = cells.find((c) => c.path === picked)

  return (
    <div className="dr">
      <button className="dr-toggle" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span>{open ? '▾' : '▸'}</span> Drivers <span className="an-sub">{mix}</span>
      </button>
      {open && (
        <>
          <div className="an-scroll">
            <table className="an-table dr-table" aria-label="Forecast drivers and their sources">
              <thead>
                <tr><th />{years.map((y) => <th key={y}>{y}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((r) =>
                  'group' in r ? (
                    <tr key={r.group} className="group"><td colSpan={years.length + 1}>{r.group}</td></tr>
                  ) : (
                    <tr key={r.label}>
                      <td className="lbl">{r.label}<span className="u">{r.unit}</span></td>
                      {r.cells.map((c) => {
                        const t = sourceTag(c.source, c.ref)
                        return (
                          <td key={c.path}>
                            <button className={`dr-cell${picked === c.path ? ' on' : ''}`} onClick={() => setPicked(picked === c.path ? null : c.path)}
                              title={[t?.name, c.ref].filter(Boolean).join(' · ')}>
                              {fmt(c.base, r.step >= 1 ? 0 : 1)}
                              {t && <span className={`src-tag src-${t.tag}`}>{t.tag}</span>}
                            </button>
                          </td>
                        )
                      })}
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
          {d ? (
            <p className="dr-detail">
              <b>{d.label} {d.year}: {fmt(d.base, d.step >= 1 ? 0 : 1)}{d.unit.startsWith('%') ? '%' : ''}</b>
              {d.tag && <span className={`src-tag src-${d.tag.tag}`}>{d.tag.tag}</span>}
              {d.tag?.name}{d.ref ? ` — ${d.ref}` : ''}
            </p>
          ) : (
            <p className="an-legend dr-legend">
              <span><span className="src-tag src-G">G</span>guidance</span>
              <span><span className="src-tag src-F">F</span>filing / reported</span>
              <span><span className="src-tag src-A">A</span>assumption</span>
              <span><span className="src-tag src-E">E</span>edited by you</span>
              <span>click a value for its source</span>
            </p>
          )}
        </>
      )}
    </div>
  )
}
