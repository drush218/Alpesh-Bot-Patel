import type { ModelInputs } from '../../types/analysis'
import { deltaRows, fmt, stepDp } from '../../lib/modelRows'
import { sourceTag } from './Drivers'

export type OnEdit = (path: string, value: number, base: number | null) => void

/** One editable driver value; amber with "was" when it differs from base. */
export function Cell({ path, base, step, source, note, edits, onChange }: {
  path: string
  base: number | null
  step: number
  source?: string
  note?: string
  edits: Record<string, number>
  onChange: OnEdit
}) {
  const edited = path in edits
  const title = [`base ${base ?? 'not set'}${source && source !== 'none' ? ` · ${source}` : ''}`, note, path].filter(Boolean).join('\n')
  return (
    <span className={`an-cell${edited ? ' edited' : ''}`} title={title}>
      <input
        type="number"
        step={step}
        id={`in-${path}`}
        aria-label={path}
        defaultValue={edited ? edits[path] : base ?? ''}
        onChange={(e) => {
          const v = parseFloat(e.target.value)
          if (!Number.isNaN(v)) onChange(path, v, base)
        }}
      />
      <span className={`src src-${sourceTag(source, note)?.tag ?? ''}`}>{sourceTag(source, note)?.tag ?? ''}</span>
      {edited && <span className="was">was {fmt(base, stepDp(step))}</span>}
    </span>
  )
}

/** LOW/HIGH scenario deltas, shown under the income statement while editing. */
export function DeltaInputs({ inputs, edits, onChange }: { inputs: ModelInputs; edits: Record<string, number>; onChange: OnEdit }) {
  return (
    <>
      <table className="an-table" aria-label="Scenario deltas" style={{ width: 'auto' }}>
        <thead>
          <tr><th>Scenario deltas vs BAU · all years</th><th>growth pp</th><th>margin pp</th></tr>
        </thead>
        <tbody>
          {deltaRows(inputs).map((d) => (
            <tr key={d.label}>
              <td className="lbl">{d.label}</td>
              <td><Cell {...d.growth} step={0.5} note={d.ref} edits={edits} onChange={onChange} /></td>
              <td><Cell {...d.margin} step={0.5} note={d.ref} edits={edits} onChange={onChange} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="an-legend">
        <span>amber = edited · was = base value</span>
        <span>G guidance · F filing / reported · A assumption · E edited by you (hover a cell for the source)</span>
      </div>
    </>
  )
}
