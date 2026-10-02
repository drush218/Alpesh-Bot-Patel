import { supabase } from './supabaseClient'
import type { BookResponse } from '../types/book'

const BASE_URL = import.meta.env.VITE_API_BASE_URL

class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function authedFetch(path: string): Promise<Response> {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    throw new ApiError(401, 'Not signed in')
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
  })

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

export { ApiError }
