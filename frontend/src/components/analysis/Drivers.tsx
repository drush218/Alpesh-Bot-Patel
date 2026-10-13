import { fmt, stepDp, type InputCell } from '../../lib/modelRows'

/** One tag per input cell: G guidance, F filing / reported share change, A assumption, E edited by you. */
export function sourceTag(source?: string, ref?: string): { tag: string; name: string } | null {
  if (ref?.startsWith('Edited in Portfolio Terminal')) return { tag: 'E', name: 'edited by you' }
  if (source === 'guidance') return { tag: 'G', name: 'guidance' }
  if (source === 'filing' || source === 'buyback_executed' || source === 'issuance_declared' || source === 'issuance_and_buyback')
    return { tag: 'F', name: source === 'filing' ? 'filing' : source.replace(/_/g, ' ') }
  if (source === 'assumption') return { tag: 'A', name: 'assumption' }
  return null
}

export interface PickedDriver {
  cell: InputCell
  label: string
  year: string
  step: number
  unit: string
}

/** Under the income statement: the picked driver's source note, else the tag legend. */
export function SourceNote({ picked }: { picked: PickedDriver | null }) {
  if (!picked) {
    return (
      <p className="an-legend dr-legend">
        <span><span className="src-tag src-G">G</span>guidance</span>
        <span><span className="src-tag src-F">F</span>filing / reported</span>
        <span><span className="src-tag src-A">A</span>assumption</span>
        <span><span className="src-tag src-E">E</span>edited by you</span>
        <span>click a driver for its source</span>
      </p>
    )
  }
  const { cell, label, year, step, unit } = picked
  const t = sourceTag(cell.source, cell.ref)
  return (
    <p className="dr-detail">
      <b>{label} {year}: {fmt(cell.base, stepDp(step))}{unit.startsWith('%') ? '%' : ''}</b>
      {t && <span className={`src-tag src-${t.tag}`}>{t.tag}</span>}
      {t?.name}{cell.ref ? ` — ${cell.ref}` : ''}
    </p>
  )
}
