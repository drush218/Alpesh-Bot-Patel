import { supabase } from './supabaseClient'
import type { BookResponse } from '../types/book'
import type { AccountSummary, BenchmarksResponse } from '../types/account'
import type { IngestPreview, SettingsStatus } from '../types/settings'
import type { MacroView } from '../types/macro'
import type { DashboardData } from '../types/dashboard'
import type { AnalysisView, Override, ScenarioSummary, ScorecardIn, ScorecardResponse, WorkspaceResult } from '../types/analysis'

const BASE_URL = import.meta.env.VITE_API_BASE_URL

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    throw new ApiError(401, 'Not signed in')
  }

  const send = (token: string) =>
    fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), Authorization: `Bearer ${token}` },
    })

  let res = await send(session.access_token)

  // A stored token can expire just before supabase-js refreshes it; refresh once and retry.
  if (res.status === 401) {
    const { data } = await supabase.auth.refreshSession()
    if (data.session) res = await send(data.session.access_token)
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body.detail || `Request failed (${res.status})`)
  }

  return res
}

export async function fetchBook(): Promise<BookResponse> {
  const res = await authedFetch('/api/book')
  return res.json()
}

export async function fetchAccount(): Promise<AccountSummary> {
  const res = await authedFetch('/api/account')
  return res.json()
}

export async function fetchBenchmarks(): Promise<BenchmarksResponse> {
  const res = await authedFetch('/api/account/benchmarks')
  return res.json()
}

const post = (path: string, body: unknown) => authedFetch(path, { method: 'POST', body: JSON.stringify(body) })
const enc = encodeURIComponent

export async function listAnalysed(): Promise<string[]> {
  return (await authedFetch('/api/analysis')).json()
}

export async function fetchAnalysis(ticker: string): Promise<AnalysisView> {
  return (await authedFetch(`/api/analysis/${enc(ticker)}`)).json()
}

/** Current analysis with unsaved edits applied; outputs rerun server-side by the same engine as the skill. */
export async function previewWorkspace(ticker: string, overrides: Override[]): Promise<WorkspaceResult> {
  return (await post(`/api/analysis/${enc(ticker)}/workspace`, { overrides })).json()
}

export async function listScenarios(ticker: string): Promise<ScenarioSummary[]> {
  return (await authedFetch(`/api/analysis/${enc(ticker)}/scenarios`)).json()
}

export async function loadScenario(ticker: string, id: number): Promise<WorkspaceResult> {
  return (await authedFetch(`/api/analysis/${enc(ticker)}/scenarios/${id}`)).json()
}

export async function saveScenario(
  ticker: string,
  body: { name: string; note: string | null; overrides: Override[] },
): Promise<{ id: number; name: string; override_count: number }> {
  return (await post(`/api/analysis/${enc(ticker)}/scenarios`, body)).json()
}

export async function deleteScenario(ticker: string, id: number): Promise<void> {
  await authedFetch(`/api/analysis/${enc(ticker)}/scenarios/${id}`, { method: 'DELETE' })
}

export async function fetchScorecard(ticker: string): Promise<ScorecardResponse> {
  return (await authedFetch(`/api/analysis/${enc(ticker)}/scorecard`)).json()
}

export async function saveScorecard(ticker: string, card: ScorecardIn): Promise<ScorecardResponse> {
  return (await post(`/api/analysis/${enc(ticker)}/scorecard`, card)).json()
}

export async function fetchSettingsStatus(): Promise<SettingsStatus> {
  return (await authedFetch('/api/settings/status')).json()
}

export async function saveCredentials(api_key: string, api_secret: string): Promise<void> {
  await post('/api/settings/t212', { api_key, api_secret })
}

export async function previewAnalysis(markdown: string, filename: string | null): Promise<IngestPreview> {
  return (await post('/api/analyses/preview', { markdown, filename })).json()
}

export async function storeAnalysis(
  markdown: string,
  filename: string | null,
): Promise<{ analysis_id: number; already_existed: boolean; ticker: string }> {
  return (await post('/api/analyses', { markdown, filename })).json()
}

export async function decideProposal(code: string, decision: 'approve' | 'reject'): Promise<void> {
  await authedFetch(`/api/factors/proposals/${enc(code)}/${decision}`, { method: 'POST' })
}

export interface MarketRefreshSummary {
  prices_updated: number
  prices_fresh: number
  fx_updated: number
  fx_fresh: number
  failed: string[]
  unmapped: string[]
  warnings: string[]
}

/** Pull latest prices/FX into Supabase; anything under 15 min old is skipped server-side. */
export async function refreshMarket(): Promise<MarketRefreshSummary> {
  const res = await authedFetch('/api/market/refresh', { method: 'POST' })
  return res.json()
}

export { ApiError }

export async function fetchMacro(): Promise<MacroView> {
  return (await authedFetch('/api/macro')).json()
}

/** Pull factor series from FRED; the server skips factors already fetched today. */
export async function refreshMacro(): Promise<unknown> {
  return (await authedFetch('/api/macro/refresh', { method: 'POST' })).json()
}

export async function fetchDashboard(): Promise<DashboardData> {
  return (await authedFetch('/api/dashboard')).json()
}
