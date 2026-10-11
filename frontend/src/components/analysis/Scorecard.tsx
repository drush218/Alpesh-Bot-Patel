import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchScorecard, saveScorecard } from '../../lib/apiClient'
import { signedInt } from '../../lib/macro'
import type { Catalyst, CatalystStatus, Dimension, MacroSummary, ScorecardIn, ScorecardResponse } from '../../types/analysis'

const DIMS: [Dimension, string][] = [['growth', 'Growth'], ['value', 'Value'], ['income', 'Income'], ['macro', 'Macro']]
const NEXT_STATUS: Record<CatalystStatus, CatalystStatus> = { open: 'hit', hit: 'missed', missed: 'open' }
type Side = 'bull_catalysts' | 'bear_catalysts'

// The user's card is never prefilled; scores are null (unset) until clicked. 0 is a real score.
const SCORES = [0, 1, 2, 3]
const blank = (): ScorecardIn => ({ growth: null, value: null, income: null, macro: null, bull_catalysts: [], bear_catalysts: [], note: null, target_pe: null, target_pe_note: null })

const today = () => new Date().toISOString().slice(0, 10)
const fmtDate = (d: string) =>
  new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })

export function Scorecard({ ticker, onTargetPe, macroSummary }: { ticker: string; onTargetPe?: (pe: number | null) => void; macroSummary?: MacroSummary }) {
  const [data, setData] = useState<ScorecardResponse | null>(null)
  const [card, setCard] = useState<ScorecardIn>(blank)
  const [dirty, setDirty] = useState(false)
  const [claudeOpen, setClaudeOpen] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [peText, setPeText] = useState('')

  const onTargetPeRef = useRef(onTargetPe)
  useEffect(() => {
    onTargetPeRef.current = onTargetPe
  }, [onTargetPe])

  const adopt = useCallback((res: ScorecardResponse) => {
    setData(res)
    const c = res.current
    setCard(c ? {
      growth: c.growth, value: c.value, income: c.income, macro: c.macro, bull_catalysts: c.bull_catalysts, bear_catalysts: c.bear_catalysts,
      note: c.note, target_pe: c.target_pe, target_pe_note: c.target_pe_note,
    } : blank())
    setPeText(c?.target_pe != null ? String(c.target_pe) : '')
    setDirty(false)
    onTargetPeRef.current?.(c?.target_pe ?? null) // saved target only, so the chart doesn't move while typing
  }, [])

  useEffect(() => {
    fetchScorecard(ticker).then(adopt).catch((e) => setError(e.message))
  }, [ticker, adopt])

  const change = (next: ScorecardIn) => {
    setCard(next)
    setDirty(true)
    setMsg(null)
  }
  const setCat = (side: Side, i: number, patch: Partial<Catalyst>) =>
    change({ ...card, [side]: card[side].map((c, j) => (j === i ? { ...c, ...patch } : c)) })

  const save = async () => {
    setSaving(true)
    try {
      const res = await saveScorecard(ticker, card)
      adopt(res)
      setMsg(`Saved as version ${res.versions}. Earlier versions are kept.`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  if (!data) {
    return (
      <section className="an-card">
        <h2>Scorecard</h2>
        <p className="an-sub">{error ?? 'Loading…'}</p>
      </section>
    )
  }

  const sug = data.suggested
  const complete = card.growth != null && card.value != null && card.income != null && card.macro != null
  const status =
    msg ??
    (dirty ? 'Unsaved changes' : data.versions ? `${data.versions} saved version${data.versions === 1 ? '' : 's'} · dated catalysts show in upcoming events` : 'Not scored yet. Click a box to score 0–3.')

  return (
    <section className="an-card">
      <div className="an-head" style={{ marginBottom: 10 }}>
        <h2>Scorecard</h2>
      </div>
      {error && <p className="an-sub" style={{ color: 'var(--down)' }}>{error}</p>}

      <div className="sc-dims">
        {DIMS.map(([k, label]) => {
          const mine = card[k]
          const theirs = k === 'macro' ? null : sug?.[k]?.score
          const diff = mine != null && theirs != null ? Math.abs(mine - theirs) : 0
          return (
            <div key={k} className={`sc-dim${diff >= 2 ? ' flag' : ''}`}>
              <span className="name">{label}</span>
              <div className="sc-pips" role="radiogroup" aria-label={label}>
                {SCORES.map((n) => (
                  <button
                    key={n}
                    className={`sc-pip${mine != null && n <= mine ? ' on' : ''}`}
                    role="radio"
                    aria-checked={n === mine}
                    aria-label={`${label} ${n} of 3`}
                    onClick={() => change({ ...card, [k]: n })}
                  >
                    {n}
                  </button>
                ))}
              </div>
              <span className="diff" style={k === 'macro' ? { color: 'var(--ink3)' } : undefined}>
                {k === 'macro'
                  ? macroSummary ? `net ${signedInt(macroSummary.net)}` : ''
                  : diff >= 2 ? `Claude ${theirs}` : ''}
              </span>
            </div>
          )
        })}
      </div>

      <div className="sc-cats">
        {(['bull_catalysts', 'bear_catalysts'] as Side[]).map((side) => (
          <CatalystList
            key={side}
            title={side === 'bull_catalysts' ? 'Bull catalysts' : 'Bear catalysts'}
            items={card[side]}
            onStatus={(i, s) => setCat(side, i, { status: s })}
            onRemove={(i) => change({ ...card, [side]: card[side].filter((_, j) => j !== i) })}
            onAdd={(c) => change({ ...card, [side]: [...card[side], c] })}
            placeholder={`Add a ${side === 'bull_catalysts' ? 'bull' : 'bear'} catalyst`}
          />
        ))}
      </div>

      <div className="sc-target">
        <div className="an-micro">Target PE</div>
        <div className="sc-add">
          <input
            type="number"
            min={0}
            step={0.5}
            value={peText}
            placeholder="e.g. 22"
            aria-label="Target PE"
            onWheel={(e) => e.currentTarget.blur()}
            onChange={(e) => {
              setPeText(e.target.value)
              const v = Number(e.target.value)
              change({ ...card, target_pe: e.target.value === '' || !(v > 0) ? null : v })
            }}
            style={{ flex: '0 1 90px' }}
          />
          <span className="an-sub" style={{ alignSelf: 'center' }}>× EPS</span>
        </div>
        <textarea
          className="sc-just"
          rows={3}
          value={card.target_pe_note ?? ''}
          placeholder="Why this multiple? (peers, history, growth)"
          aria-label="Target PE justification"
          onChange={(e) => change({ ...card, target_pe_note: e.target.value || null })}
        />
      </div>

      {sug && (
        <div className="sc-disc">
          <button onClick={() => setClaudeOpen((o) => !o)} aria-expanded={claudeOpen}>
            <span>{claudeOpen ? '▾' : '▸'}</span>Claude's view
            {sug.as_of && <i style={{ color: 'var(--ink3)', fontStyle: 'normal' }}>({fmtDate(sug.as_of)})</i>}
          </button>
          {claudeOpen && (
            <div className="sc-claude">
              {DIMS.filter(([k]) => k !== 'macro').map(([k, label]) => (
                <div key={k} className="row">
                  <span>{label}</span>
                  <b title={sug[k as 'growth']?.score_1_5 != null ? `${sug[k as 'growth']?.score_1_5}/5 in the analysis` : undefined}>{sug[k as 'growth']?.score ?? '—'}</b>
                  <span>{sug[k as 'growth']?.ref}</span>
                </div>
              ))}
              {[...sug.bull_catalysts.map((c) => ['bull', c] as const), ...sug.bear_catalysts.map((c) => ['bear', c] as const)].map(
                ([side, c]) => (
                  <div key={side + c.text} className="row">
                    <span>{side}</span>
                    <span />
                    <span>{c.text}{c.date ? ` · ${fmtDate(c.date)}` : ''}</span>
                  </div>
                ),
              )}
            </div>
          )}
        </div>
      )}

      <div className="sc-foot">
        <span className="an-sub">{status}</span>
        <button className="an-btn primary" disabled={!complete || !dirty || saving} onClick={save}>
          Save scorecard
        </button>
      </div>
    </section>
  )
}

function CatalystList({ title, items, onStatus, onRemove, onAdd, placeholder }: {
  title: string
  items: Catalyst[]
  onStatus: (i: number, s: CatalystStatus) => void
  onRemove: (i: number) => void
  onAdd: (c: Catalyst) => void
  placeholder: string
}) {
  const [text, setText] = useState('')
  const [date, setDate] = useState('')
  const now = today()

  return (
    <div>
      <div className="an-micro">{title}</div>
      <ul className="sc-list">
        {items.length === 0 && <li className="an-sub">None yet</li>}
        {items.map((c, i) => (
          <li key={i} className="sc-cat">
            <span className="txt">
              {c.text}
              {c.date && <div className="dt">{fmtDate(c.date)}</div>}
            </span>
            <button className={`sc-status ${c.status}`} title="Change status" onClick={() => onStatus(i, NEXT_STATUS[c.status])}>
              {c.status}
            </button>
            <button className="sc-remove" aria-label={`Remove ${c.text}`} title="Remove" onClick={() => onRemove(i)}>×</button>
            {c.date && c.date < now && c.status === 'open' && (
              <span className="ask">
                Date passed. How did it go?
                <button className="sc-status hit" onClick={() => onStatus(i, 'hit')}>hit</button>
                <button className="sc-status missed" onClick={() => onStatus(i, 'missed')}>missed</button>
              </span>
            )}
          </li>
        ))}
      </ul>
      <form
        className="sc-add"
        onSubmit={(e) => {
          e.preventDefault()
          if (!text.trim()) return
          onAdd({ text: text.trim(), date: date || null, status: 'open' })
          setText('')
          setDate('')
        }}
      >
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder={placeholder} aria-label={placeholder} />
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} aria-label="Date (optional)" />
        <button className="an-btn" type="submit">Add</button>
      </form>
    </div>
  )
}
