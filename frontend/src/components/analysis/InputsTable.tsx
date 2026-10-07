import type { ModelInputs } from '../../types/analysis'
import { deltaRows, fmt, inputRows } from '../../lib/modelRows'

interface Props {
  inputs: ModelInputs
  edits: Record<string, number>
  onChange: (path: string, value: number, base: number) => void
}

const SRC_TAG: Record<string, string> = { guidance: 'G', filing: 'F', assumption: 'A' }

function Cell({ path, base, step, source, note, edits, onChange }: {
  path: string
  base: number
  step: number
  source?: string
  note?: string
  edits: Record<string, number>
  onChange: Props['onChange']
}) {
  const edited = path in edits
  const title = [`base ${base}${source && source !== 'none' ? ` · ${source}` : ''}`, note, path].filter(Boolean).join('\n')
  return (
    <span className={`an-cell${edited ? ' edited' : ''}`} title={title}>
      <input
        type="number"
        step={step}
        id={`in-${path}`}
        aria-label={path}
        defaultValue={edited ? edits[path] : base}
        onChange={(e) => {
          const v = parseFloat(e.target.value)
          if (!Number.isNaN(v)) onChange(path, v, base)
        }}
      />
      <span className="src">{source ? SRC_TAG[source] ?? '' : ''}</span>
      {edited && <span className="was">was {fmt(base, step >= 1 ? 0 : 1)}</span>}
    </span>
  )
}

export function InputsTable({ inputs, edits, onChange }: Props) {
  const years = inputs.meta.forecast_years
  return (
    <>
      <div className="an-scroll">
        <table className="an-table" aria-label="Model inputs">
          <thead>
            <tr>
              <th>Input</th>
              {years.map((y) => <th key={y}>{y}</th>)}
            </tr>
          </thead>
          <tbody>
            {inputRows(inputs).map((r) =>
              'group' in r ? (
                <tr key={r.group} className="group"><td colSpan={years.length + 1}>{r.group}</td></tr>
              ) : (
                <tr key={r.label}>
                  <td className="lbl">{r.label}<span className="u">{r.unit}</span></td>
                  {r.cells.map((c) => (
                    <td key={c.path}><Cell path={c.path} base={c.base} source={c.source} note={c.ref} step={r.step} edits={edits} onChange={onChange} /></td>
                  ))}
                </tr>
              ),
            )}
            <tr className="group"><td colSpan={years.length + 1}>Scenario deltas vs BAU · all years</td></tr>
            <tr>
              <td />
              <th>growth pp</th>
              <th>margin pp</th>
              {years.slice(2).map((y) => <th key={y} />)}
            </tr>
            {deltaRows(inputs).map((d) => (
              <tr key={d.label}>
                <td className="lbl">{d.label}</td>
                <td><Cell {...d.growth} step={0.5} note={d.ref} edits={edits} onChange={onChange} /></td>
                <td><Cell {...d.margin} step={0.5} note={d.ref} edits={edits} onChange={onChange} /></td>
                {years.slice(2).map((y) => <td key={y} />)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="an-legend">
        <span>amber = edited · was = base value</span>
        <span>G guidance · F filing · A assumption (hover a cell for the source)</span>
      </div>
    </>
  )
}
