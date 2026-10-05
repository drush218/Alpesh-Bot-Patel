import { supabase } from './supabaseClient'
import type { BookResponse } from '../types/book'
import type { AccountSummary, BenchmarksResponse } from '../types/account'

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
    fetch(`${BASE_URL}${path}`, { ...init, headers: { Authorization: `Bearer ${token}` } })

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
