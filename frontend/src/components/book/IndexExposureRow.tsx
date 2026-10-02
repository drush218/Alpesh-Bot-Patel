import type { IndexExposureRow as IndexExposureRowType } from '../../types/book'
import { formatPct } from '../../lib/format'
import { Chip } from '../common/Chip'

const RAMP = [100, 66, 46, 32, 22]

interface Props {
  row: IndexExposureRowType
  rank: number
}

export function IndexExposureRow({ row, rank }: Props) {
  const rampPct = RAMP[rank] ?? RAMP[RAMP.length - 1]
  const barWidth = Math.min(100, row.share_of_invested_pct)

  return (
    <div className="index-row">
      <span
        style={{
          width: 10,
          height: 10,
          borderRadius: 2,
          background: `color-mix(in srgb, var(--accent) ${rampPct}%, var(--panel2))`,
        }}
      />
      <span style={{ fontSize: 12, color: 'var(--ink)' }}>{row.name}</span>
      <span className="tabular-nums" style={{ fontSize: 13, fontWeight: 600, textAlign: 'right' }}>
        {formatPct(row.weight_of_book_pct)}
      </span>
      <div style={{ position: 'relative', height: 9, background: 'var(--panel2)', borderRadius: 1 }}>
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: `${barWidth}%`,
            background: `color-mix(in srgb, var(--accent) ${rampPct}%, var(--panel2))`,
            borderRadius: 1,
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: '40%',
            top: -3,
            bottom: -3,
            width: 1,
            background: 'var(--line2)',
          }}
        />
      </div>
      <span className="tabular-nums" style={{ fontSize: 11, color: 'var(--ink3)' }}>
        {formatPct(row.share_of_invested_pct)} of invested
      </span>
      <span style={{ visibility: row.over_limit ? 'visible' : 'hidden' }}>
        <Chip tone="down" strength="half">
          over 40%
        </Chip>
      </span>
      <span style={{ fontSize: 10.5, color: 'var(--ink2)', letterSpacing: '.05em', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {row.member_tickers.join(' · ')}
      </span>
    </div>
  )
}
