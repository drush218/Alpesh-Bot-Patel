import { useCallback, useEffect, useRef, useState } from 'react'
import {
  deleteScenario,
  listScenarios,
  loadScenario,
  previewWorkspace,
  saveAsBase,
  saveScenario,
} from '../../lib/apiClient'
import { currencySymbol } from '../../lib/modelRows'
import type { Override, ScenarioSummary, WorkspaceResult } from '../../types/analysis'
import { Drivers } from './Drivers'
import { InputsTable } from './InputsTable'
import { PeChart } from './ValuationPanels'
import { EpsBand, OutputTable } from './OutputTable'

type Form = null | 'save' | 'saveas' | 'reset' | 'delete' | 'base' | { done: string }

const toList = (edits: Record<string, number>): Override[] => Object.entries(edits).map(([path, value]) => ({ path, value }))
const toMap = (list: Override[]) => Object.fromEntries(list.map((o) => [o.path, o.value]))
const sameEdits = (a: Record<string, number>, b: Record<string, number>) =>
  Object.keys(a).length === Object.keys(b).length && Object.entries(a).every(([k, v]) => b[k] === v)

function formatPriceTime(iso: string) {
  const d = new Date(iso)
  return `${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}, ${d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`
}

export function ScenarioWorkspace({ ticker, onBaseLoaded, onBaseSaved }: {
  ticker: string
  onBaseLoaded?: (r: WorkspaceResult) => void
  onBaseSaved?: () => void
}) {
  const [saved, setSaved] = useState<ScenarioSummary[]>([])
  const [selected, setSelected] = useState<number | null>(null)
  const [loaded, setLoaded] = useState<WorkspaceResult | null>(null) // result for the selected scenario / base, unedited
  const [result, setResult] = useState<WorkspaceResult | null>(null) // what's shown (includes unsaved edits)
  const [edits, setEdits] = useState<Record<string, number>>({})
  const [editing, setEditing] = useState(false)
  const [editingBase, setEditingBase] = useState(false) // correcting BAU itself, not a scenario
  const [compare, setCompare] = useState(false)
  const [form, setForm] = useState<Form>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [tableKey, setTableKey] = useState(0) // remounts the uncontrolled inputs when edits are replaced
  const previewTimer = useRef<number | undefined>(undefined)
  const onBaseLoadedRef = useRef(onBaseLoaded)
  useEffect(() => {
    onBaseLoadedRef.current = onBaseLoaded
  }, [onBaseLoaded])

  const loadedEdits = loaded?.scenario ? toMap(loaded.scenario.overrides) : {}
  const dirty = !sameEdits(edits, loadedEdits)
  const current = saved.find((s) => s.id === selected) ?? null
  const showingBase = Object.keys(edits).length === 0
  const comparing = compare && !showingBase // nothing to compare while showing the base

  const fail = (e: unknown) => setError(e instanceof Error ? e.message : String(e))

  const refreshList = useCallback(() => listScenarios(ticker).then(setSaved).catch(fail), [ticker])

  const show = useCallback((r: WorkspaceResult, nextEdits: Record<string, number>) => {
    setLoaded(r)
    setResult(r)
    setEdits(nextEdits)
    setTableKey((k) => k + 1)
  }, [])

  useEffect(() => {
    previewWorkspace(ticker, [])
      .then((r) => {
        show(r, {})
        onBaseLoadedRef.current?.(r)
      })
      .catch(fail)
    refreshList()
  }, [ticker, show, refreshList])


  const select = async (id: number | null) => {
    setForm(null)
    setError(null)
    setSelected(id)
    try {
      if (id == null) show(await previewWorkspace(ticker, []), {})
      else {
        const r = await loadScenario(ticker, id)
        show(r, toMap(r.scenario?.overrides ?? []))
      }
    } catch (e) {
      fail(e)
    }
  }

  const rerun = (next: Record<string, number>) => {
    window.clearTimeout(previewTimer.current)
    previewTimer.current = window.setTimeout(() => {
      previewWorkspace(ticker, toList(next))
        .then((r) => setResult((prev) => ({ ...r, scenario: prev?.scenario })))
        .catch(fail)
    }, 250)
  }

  const onEdit = (path: string, value: number, base: number) => {
    setEdits((prev) => {
      const next = { ...prev }
      if (Math.abs(value - base) < 1e-9) delete next[path]
      else next[path] = value
      rerun(next)
      return next
    })
  }

  const startEditing = () => {
    setEditing(true)
    setEditingBase(false)
    setForm(null)
    if (selected == null) setCompare(true)
  }

  const startEditingBase = () => {
    setEditing(true)
    setEditingBase(true)
    setForm(null)
    setCompare(true)
  }

  const submitBase = async () => {
    setBusy(true)
    try {
      await saveAsBase(ticker, toList(edits))
      setEditing(false)
      setEditingBase(false)
      onBaseSaved?.() // the whole screen reloads onto the new analysis
    } catch (e) {
      fail(e)
    } finally {
      setBusy(false)
    }
  }

  const discard = () => {
    if (loaded) show(loaded, loadedEdits)
    setEditing(false)
    setEditingBase(false)
    setForm(null)
  }

  const resetToBase = () => {
    setEdits({})
    setTableKey((k) => k + 1)
    rerun({})
    setForm(null)
  }

  const submitSave = async (name: string, note: string) => {
    setBusy(true)
    try {
      const res = await saveScenario(ticker, { name, note: note || null, overrides: toList(edits) })
      await refreshList()
      setEditing(false)
      await select(res.id)
      setForm({ done: `Saved “${res.name}”.` })
    } catch (e) {
      fail(e)
    } finally {
      setBusy(false)
    }
  }

  const confirmDelete = async () => {
    if (!current) return
    setBusy(true)
    try {
      await deleteScenario(ticker, current.id)
      await refreshList()
      await select(null)
      setForm({ done: `Deleted “${current.name}”.` })
    } catch (e) {
      fail(e)
    } finally {
      setBusy(false)
    }
  }

  if (!result) {
    return (
      <section className="an-card">
        <h2>Income statement (forecast)</h2>
        <p className="an-sub">{error ?? 'Loading the model…'}</p>
      </section>
    )
  }

  const n = Object.keys(edits).length
  const price = result.price
  const scen = loaded?.scenario

  return (
    <section className="an-card">
      <div className="an-head">
        <div style={{ minWidth: 0 }}>
          <h2>Income statement (forecast)</h2>
          <div className="an-sub">
            {editingBase ? (
              <>
                Editing the <b>base analysis</b> · {n} input{n === 1 ? '' : 's'} changed
                {n > 0 && <> · <span className="an-dirty">unsaved</span></>}
              </>
            ) : editing ? (
              <>
                Editing <b>{current ? current.name : 'new scenario'}</b> · {n} input{n === 1 ? '' : 's'} changed from base
                {dirty && <> · <span className="an-dirty">unsaved</span></>}
              </>
            ) : current ? (
              <>Showing <b>{current.name}</b>{current.note ? ` · ${current.note}` : ''}</>
            ) : (
              <>Showing the <b>base analysis</b>{result.data_as_of ? ` (${result.data_as_of})` : ''}</>
            )}
          </div>
        </div>
        <div className="an-tools">
          {editingBase ? (
            <>
              <button className="an-btn primary" disabled={n === 0 || busy} onClick={() => setForm('base')}>Save as base…</button>
              <button className="an-btn" onClick={discard}>{n ? 'Discard changes' : 'Done'}</button>
            </>
          ) : editing ? (
            <>
              <button className="an-btn primary" disabled={n === 0 || busy} onClick={() => setForm('save')}>
                {current ? 'Save' : 'Save as…'}
              </button>
              {current && (
                <button className="an-btn" disabled={n === 0 || busy} onClick={() => setForm('saveas')}>Save as new…</button>
              )}
              <button className="an-btn" disabled={n === 0} onClick={() => setForm('reset')}>Return to base</button>
              <button className="an-btn" onClick={discard}>{dirty ? 'Discard changes' : 'Done'}</button>
            </>
          ) : (
            <>
              <label className="an-sub" htmlFor="scenario-select" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                show
                <select
                  id="scenario-select"
                  className="an-select"
                  value={selected ?? ''}
                  onChange={(e) => select(e.target.value ? Number(e.target.value) : null)}
                >
                  <option value="">Base{result.data_as_of ? ` · analysis ${result.data_as_of}` : ''}</option>
                  {saved.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} · {s.override_count} edit{s.override_count === 1 ? '' : 's'}
                    </option>
                  ))}
                </select>
              </label>
              {current ? (
                <>
                  <button className="an-btn" onClick={startEditing}>Edit</button>
                  <button className="an-btn danger" onClick={() => setForm('delete')}>Delete</button>
                </>
              ) : (
                <>
                  <button className="an-btn" onClick={startEditingBase} title="Correct the analysis's own BAU inputs">Edit base</button>
                  <button className="an-btn primary" onClick={startEditing} title="A deviation from BAU, saved separately">New scenario</button>
                </>
              )}
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="an-callout error">
          <span className="k">ERROR</span>
          <span>{error}</span>
        </div>
      )}

      {scen?.rebased && loaded && (
        <div className="an-callout">
          <span className="k">REBASED</span>
          <span>Saved on an earlier analysis and applied to the current one. Save it again to move it onto this base.</span>
          {(loaded.base_moved.length > 0 || loaded.could_not_apply.length > 0) && (
            <ul>
              {loaded.base_moved.map((m) => (
                <li key={m.path}>{m.path}: {m.note}, your {edits[m.path] ?? '—'} still applied</li>
              ))}
              {loaded.could_not_apply.map((p) => (
                <li key={p}>Could not apply {p} (no longer in the analysis)</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {result.errors.length > 0 && (
        <div className="an-callout error">
          <span className="k">MODEL ERROR</span>
          <ul>{result.errors.map((e) => <li key={e}>{e}</li>)}</ul>
        </div>
      )}

      <FormRow
        form={form}
        currentName={current?.name}
        currentNote={current?.note}
        editCount={n}
        busy={busy}
        onCancel={() => setForm(null)}
        onSave={submitSave}
        onReset={resetToBase}
        onDelete={confirmDelete}
        onSaveBase={submitBase}
      />

      <div className="an-head" style={{ margin: '4px 0 6px' }}>
        <div className="an-price">
          current price{' '}
          {price ? (
            <>
              <b>{currencySymbol(price.currency)}{price.close.toFixed(2)}</b>
              <span>{price.source ?? 'stored'} · {formatPriceTime(price.fetched_at)} · PE uses this</span>
            </>
          ) : (
            <span>not loaded yet, so PE is blank</span>
          )}
        </div>
        <div style={{ display: 'flex', border: '1px solid var(--line2)', borderRadius: 3, overflow: 'hidden' }}>
          {[
            { on: !comparing, label: showingBase ? 'Base' : 'Scenario only', click: () => setCompare(false), disabled: false },
            { on: comparing, label: 'Compare to base', click: () => setCompare(true), disabled: showingBase },
          ].map((b) => (
            <button
              key={b.label}
              disabled={b.disabled}
              onClick={b.click}
              style={{
                border: 0,
                padding: '5px 11px',
                fontSize: 11.5,
                letterSpacing: '.05em',
                cursor: b.disabled ? 'default' : 'pointer',
                background: b.on ? 'var(--accent)' : 'transparent',
                color: b.on ? 'var(--bg)' : b.disabled ? 'var(--line2)' : 'var(--ink2)',
                fontWeight: b.on ? 600 : 400,
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>

      <OutputTable result={result} compare={comparing} scenarioLabel={editing && dirty ? 'now' : current ? 'scen.' : 'now'} />
      <EpsBand result={result} />

      <div className="an-micro" style={{ margin: '14px 0 2px' }}>PE at current price{comparing ? ' · edited' : ''}</div>
      <PeChart outputs={result.outputs ?? result.base_outputs} years={result.base_inputs.meta.forecast_years} price={price} />

      {!editing && <Drivers inputs={result.base_inputs} />}

      {editing && (
        <div className="an-edit">
          <div className="an-head" style={{ marginBottom: 8 }}>
            <h2 style={{ fontSize: 14 }}>{editingBase ? 'Base inputs' : 'Inputs'}</h2>
            <span className="an-sub">
              {editingBase ? 'Fixes to the analysis itself; saving stores a new version' : 'Edits update the table above as you type'}
            </span>
          </div>
          <InputsTable key={tableKey} inputs={result.base_inputs} edits={edits} onChange={onEdit} />
        </div>
      )}
    </section>
  )
}

function FormRow({ form, currentName, currentNote, editCount, busy, onCancel, onSave, onReset, onDelete, onSaveBase }: {
  form: Form
  currentName?: string
  currentNote?: string | null
  editCount: number
  busy: boolean
  onCancel: () => void
  onSave: (name: string, note: string) => void
  onReset: () => void
  onDelete: () => void
  onSaveBase: () => void
}) {
  if (!form) return null
  if (form === 'base') {
    return (
      <div className="an-form">
        <span className="msg">
          Store {editCount} edit{editCount === 1 ? '' : 's'} as the new base analysis? The current version is kept as history,
          edited values are tagged as yours, and saved scenarios rebase onto the new base.
        </span>
        <button className="an-btn primary" onClick={onSaveBase} disabled={busy}>Save as base</button>
        <button className="an-btn" onClick={onCancel}>Cancel</button>
      </div>
    )
  }
  if (typeof form === 'object') {
    return <div className="an-form done"><span className="msg">{form.done}</span></div>
  }
  if (form === 'save' || form === 'saveas') {
    const prefill = form === 'save'
    return (
      <form
        className="an-form"
        onSubmit={(e) => {
          e.preventDefault()
          const data = new FormData(e.currentTarget)
          const name = String(data.get('name') ?? '').trim()
          if (name) onSave(name, String(data.get('note') ?? '').trim())
        }}
      >
        <label htmlFor="scenario-name">
          Name
          <input id="scenario-name" name="name" required maxLength={80} autoFocus defaultValue={prefill ? currentName ?? '' : ''} placeholder="e.g. Faster openings" />
        </label>
        <label htmlFor="scenario-note">
          Note (optional)
          <input id="scenario-note" name="note" defaultValue={prefill ? currentNote ?? '' : ''} placeholder="What this scenario assumes" />
        </label>
        <button className="an-btn primary" type="submit" disabled={busy}>Save</button>
        <button className="an-btn" type="button" onClick={onCancel}>Cancel</button>
        <span className="msg">Saving under an existing name replaces that scenario.</span>
      </form>
    )
  }
  if (form === 'reset') {
    return (
      <div className="an-form">
        <span className="msg">Clear all {editCount} edits back to the base analysis? Nothing saved changes until you save.</span>
        <button className="an-btn primary" onClick={onReset}>Return to base</button>
        <button className="an-btn" onClick={onCancel}>Cancel</button>
      </div>
    )
  }
  return (
    <div className="an-form">
      <span className="msg">Delete “{currentName}”? This can't be undone.</span>
      <button className="an-btn danger-fill" onClick={onDelete} disabled={busy}>Delete scenario</button>
      <button className="an-btn" onClick={onCancel}>Cancel</button>
    </div>
  )
}
