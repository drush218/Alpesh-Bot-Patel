import type { ModelInputs, ModelOutputs, Price, WorkspaceResult } from '../types/analysis'

/* ---------- inputs: every editable cell, addressed the way the API stores overrides ---------- */

export interface InputCell {
  path: string
  base: number
  source?: string
  ref?: string
}

export type InputRow =
  | { group: string }
  | { label: string; unit: string; step: number; cells: InputCell[] }

export function inputRows(inputs: ModelInputs): InputRow[] {
  const years = inputs.meta.forecast_years
  const sourced = (list: { pct?: number; value?: number; source?: string; ref?: string }[], path: (y: string) => string, key: 'pct' | 'value' = 'pct') =>
    years.map((y, i) => ({ path: path(y), base: Number(list[i]?.[key] ?? 0), source: list[i]?.source, ref: list[i]?.ref }))

  const rows: InputRow[] = [{ group: 'Revenue growth' }]
  for (const s of inputs.revenue.segments) {
    rows.push({ label: s.name, unit: '%', step: 0.1, cells: sourced(s.growth, (y) => `revenue.segments[${s.name}].growth[${y}].pct`) })
  }
  rows.push({ group: 'Profit' })
  rows.push({ label: 'Operating margin', unit: '%', step: 0.1, cells: sourced(inputs.operating_margin, (y) => `operating_margin[${y}].pct`) })
  rows.push({ label: 'Net interest', unit: inputs.meta.units === 'm' ? 'm' : '', step: 1, cells: sourced(inputs.net_interest, (y) => `net_interest[${y}].value`, 'value') })
  rows.push({ label: 'Tax rate', unit: '%', step: 0.5, cells: sourced(inputs.tax_rate, (y) => `tax_rate[${y}].pct`) })
  if (inputs.nci_pct) {
    rows.push({ label: 'Minority interest', unit: '%', step: 0.5, cells: sourced(inputs.nci_pct, (y) => `nci_pct[${y}].pct`) })
  }
  rows.push({ group: 'Shares' })
  rows.push({ label: 'Share change', unit: '%/yr', step: 0.1, cells: sourced(inputs.shares.annual_change, (y) => `shares.annual_change[${y}].pct`) })
  return rows
}

export function deltaRows(inputs: ModelInputs) {
  return (['low', 'high'] as const).map((k) => ({
    label: k.toUpperCase(),
    ref: inputs.scenarios[k].ref,
    growth: { path: `scenarios.${k}.growth_pp`, base: inputs.scenarios[k].growth_pp },
    margin: { path: `scenarios.${k}.margin_pp`, base: inputs.scenarios[k].margin_pp },
  }))
}

/* ---------- outputs: the BAU table rows ---------- */

export interface OutYear {
  revenue: number | null
  growth: number | null
  costs: number | null
  margin: number | null
  ni: number | null
  niChg: number | null
  shares: number | null
  shareChg: number | null
  eps: number | null
  epsChg: number | null
  pe: number | null
}

const pctChange = (a: number, b: number | null) => (b ? (a / b - 1) * 100 : null)

export function peAt(eps: number, price: Price | null): number | null {
  if (!price || price.fx == null || eps <= 0) return null
  return price.close / (eps * price.fx)
}

export function outYears(outputs: ModelOutputs, actual: WorkspaceResult['actual'], price: Price | null): OutYear[] {
  let prevNi: number | null = null // base-year net income / EPS aren't in the analysis yet
  let prevEps: number | null = null
  let prevShares = actual.shares
  return outputs.scenarios.bau.map((y) => {
    const row: OutYear = {
      revenue: y.revenue,
      growth: y.revenue_growth_pct,
      costs: y.revenue - y.operating_income,
      margin: y.operating_margin_pct,
      ni: y.net_income,
      niChg: pctChange(y.net_income, prevNi),
      shares: y.shares_diluted,
      shareChg: pctChange(y.shares_diluted, prevShares),
      eps: y.eps,
      epsChg: pctChange(y.eps, prevEps),
      pe: peAt(y.eps, price),
    }
    prevNi = y.net_income
    prevEps = y.eps
    prevShares = y.shares_diluted
    return row
  })
}

export function actualYear(actual: WorkspaceResult['actual']): OutYear {
  return {
    revenue: actual.revenue, growth: null, costs: null, margin: null, ni: null, niChg: null,
    shares: actual.shares, shareChg: null, eps: null, epsChg: null, pe: null,
  }
}

const fmtNum = (x: number, d: number) => x.toLocaleString('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d })
export const fmt = (x: number | null, d = 1) => (x == null ? '—' : fmtNum(x, d))
export const signed = (x: number | null, d = 1) =>
  x == null ? '—' : `${x > 0 ? '+' : x < 0 ? '−' : '±'}${fmtNum(Math.abs(x), d)}`

export interface Metric {
  label: string
  main: (r: OutYear) => number | null
  mainDp: number
  sub?: (r: OutYear) => number | null
  subSigned?: boolean
  good: 1 | -1    // direction that's good for the main delta
  subGood?: 1 | -1
  pe?: boolean
}

export function metrics(ccySymbol: string, priceLabel: string): Metric[] {
  return [
    { label: `Revenue ${ccySymbol}m`, main: (r) => r.revenue, mainDp: 0, sub: (r) => r.growth, subSigned: true, good: 1, subGood: 1 },
    { label: `Costs ${ccySymbol}m`, main: (r) => r.costs, mainDp: 0, sub: (r) => r.margin, good: -1, subGood: 1 },
    { label: `Net income ${ccySymbol}m`, main: (r) => r.ni, mainDp: 0, sub: (r) => r.niChg, subSigned: true, good: 1, subGood: 1 },
    { label: 'Shares out. m', main: (r) => r.shares, mainDp: 1, sub: (r) => r.shareChg, subSigned: true, good: -1, subGood: -1 },
    { label: `EPS ${ccySymbol}`, main: (r) => r.eps, mainDp: 2, sub: (r) => r.epsChg, subSigned: true, good: 1, subGood: 1 },
    { label: `PE × at ${priceLabel}`, main: (r) => r.pe, mainDp: 1, good: -1, pe: true },
  ]
}

export function currencySymbol(ccy: string | undefined): string {
  return ({ USD: '$', GBP: '£', EUR: '€', GBp: 'p', GBX: 'p' } as Record<string, string>)[ccy ?? ''] ?? (ccy ? `${ccy} ` : '')
}
