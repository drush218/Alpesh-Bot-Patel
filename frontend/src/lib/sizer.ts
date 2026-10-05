/** Position sizing, same arithmetic as pages/2_Position_Calculator.py (and the prototype's Sizer). */

export type Macd = 0 | 1 | 2 // weak / neutral / strong

export interface SizerInput {
  price: number // native currency
  target: number
  stop: number
  fxToGbp: number // native -> GBP
  bookGbp: number
  maxLossPct: number
  macdMonthly: Macd
  macdWeekly: Macd
}

export interface SizerResult {
  errors: string[]
  up: number
  down: number
  rr: number
  maxLoss: number
  score: number
  downsideRisk: number
  upsideReward: number
  adj: number
  base: number
  sized: number
  shares: number
  lossIfStopped: number
  bookRisk: number
}

// MACD score (monthly + weekly, 0-4) -> downside risk factor. The Streamlit page only mapped
// 0-2 and failed on 3-4; the prototype treats any score of 2+ as strong confirmation.
const DOWNSIDE_RISK: Record<number, number> = { 0: 2.0, 1: 1.5, 2: 1.0, 3: 1.0, 4: 1.0 }

export function size(i: SizerInput): SizerResult {
  const errors: string[] = []
  if (!(i.price > 0)) errors.push('Enter the current price.')
  if (i.stop >= i.price) errors.push('Stop loss must be below the current price.')
  if (i.target <= i.price) errors.push('Price target must be above the current price.')
  if (!(i.fxToGbp > 0)) errors.push('No GBP rate for this currency.')
  if (!(i.bookGbp > 0)) errors.push('Enter the book value.')

  const up = i.price ? (i.target - i.price) / i.price : 0
  const down = i.price ? Math.abs((i.stop - i.price) / i.price) : 0
  const rr = down > 0 ? up / down : 0
  const maxLoss = (i.maxLossPct / 100) * i.bookGbp
  const score = i.macdMonthly + i.macdWeekly
  const downsideRisk = DOWNSIDE_RISK[score]
  const upsideReward = downsideRisk === 1.0 ? rr / 2 : 1.0
  const adj = upsideReward / downsideRisk
  const base = down > 0 ? maxLoss / down : 0
  const sized = base * adj
  const priceGbp = i.price * i.fxToGbp
  const shares = priceGbp > 0 ? sized / priceGbp : 0
  const lossIfStopped = shares * (i.price - i.stop) * i.fxToGbp
  return { errors, up, down, rr, maxLoss, score, downsideRisk, upsideReward, adj, base, sized, shares, lossIfStopped, bookRisk: i.bookGbp ? (lossIfStopped / i.bookGbp) * 100 : 0 }
}
