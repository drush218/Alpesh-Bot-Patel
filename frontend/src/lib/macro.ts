// Labels for macro links scored server-side (analysis_view.score_links): effect = sensitivity × the
// factor's 1-month move, -2..+2 per link.

export function weightLabel(w: number): string {
  if (w === 0) return 'neutral'
  return `${Math.abs(w) >= 2 ? 'strong' : 'mild'} ${w > 0 ? 'tailwind' : 'headwind'}`
}

export function sensitivityText(s: number, move: string | null | undefined): string {
  const helps = s === 0 ? 'little sensitivity' : `${s > 0 ? 'helped' : 'hurt'} when it rises`
  return `${helps} · ${move ? `${move} over the month` : 'no move data'}`
}

export const verdictTone = (v: string): 'up' | 'down' | 'neutral' =>
  v.includes('tailwind') ? 'up' : v.includes('headwind') ? 'down' : 'neutral'

export const signedInt = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${Math.abs(n)}` : '0')
