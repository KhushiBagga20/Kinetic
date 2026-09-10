/**
 * The only place that talks to the backend.
 *
 * Requests go to /api and Vite proxies them to the Python process in
 * development, so the browser is always same-origin.
 */

import type {
  Article,
  Candle,
  Exposure,
  Forecast,
  Indicator,
  IndexStats,
  Mover,
  Passage,
  Position,
  PortfolioSummary,
  Preferences,
  Quote,
  SourceRow,
  SystemStatus,
} from "./types"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
    ...init,
  })
  if (!response.ok) {
    const detail = await response.text().catch(() => "")
    throw new Error(detail ? `${response.status}: ${detail.slice(0, 200)}` : `${response.status}`)
  }
  return (await response.json()) as T
}

const post = <T,>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined })

export const api = {
  // -- system ---------------------------------------------------------------
  status: () => request<SystemStatus>("/system/status"),
  loadModel: () => post<SystemStatus["model"]>("/system/model/load"),
  unloadModel: () => post<SystemStatus["model"]>("/system/model/unload"),
  preferences: () => request<Preferences>("/system/preferences"),
  savePreferences: (changes: Partial<Preferences>) =>
    request<Preferences>("/system/preferences", {
      method: "PUT",
      body: JSON.stringify(changes),
    }),

  // -- market ---------------------------------------------------------------
  indices: () => request<Quote[]>("/market/indices"),
  quote: (symbol: string) => request<Quote>(`/market/quote/${encodeURIComponent(symbol)}`),
  history: (symbol: string, period: string) =>
    request<{ symbol: string; period: string; candles: Candle[] }>(
      `/market/history/${encodeURIComponent(symbol)}?period=${period}`,
    ),
  news: (symbol: string, limit?: number) =>
    request<Article[]>(`/market/news/${encodeURIComponent(symbol)}${limit ? `?limit=${limit}` : ""}`),
  movers: (kind: string, limit = 8) => request<Mover[]>(`/market/movers?kind=${kind}&limit=${limit}`),
  indicators: (symbol: string) =>
    request<{ score: number; indicators: Indicator[] }>(
      `/market/indicators/${encodeURIComponent(symbol)}`,
    ),
  fundamentals: (symbol: string) =>
    request<Record<string, string | number>>(`/market/fundamentals/${encodeURIComponent(symbol)}`),
  session: (symbol: string) =>
    request<{ symbol: string; exchange: string; timezone: string; state: string; label: string }>(
      `/market/session/${encodeURIComponent(symbol)}`,
    ),
  search: (query: string) =>
    request<{ symbol: string; name: string; type: string; exchange: string }[]>(
      `/market/search?q=${encodeURIComponent(query)}`,
    ),
  resolve: (query: string) =>
    request<{ symbol: string }>(`/market/resolve?q=${encodeURIComponent(query)}`),
  forecast: (symbol: string, horizon?: number) =>
    request<Forecast>(
      `/market/forecast/${encodeURIComponent(symbol)}${horizon ? `?horizon=${horizon}` : ""}`,
    ),

  // -- portfolio ------------------------------------------------------------
  portfolio: () =>
    request<{ positions: Position[]; summary: PortfolioSummary; file: string }>("/portfolio"),
  addHolding: (holding: { symbol: string; quantity: number; average_cost: number }) =>
    post<{ positions: Position[]; summary: PortfolioSummary }>("/portfolio/holdings", holding),
  removeHolding: (symbol: string) =>
    request<{ positions: Position[]; summary: PortfolioSummary }>(
      `/portfolio/holdings/${encodeURIComponent(symbol)}`,
      { method: "DELETE" },
    ),
  exposure: (topic: string) =>
    post<{ topic: string; matches: Exposure[] }>("/portfolio/exposure", { topic }),

  // -- knowledge ------------------------------------------------------------
  indexStats: () => request<IndexStats>("/knowledge/stats"),
  sources: () => request<SourceRow[]>("/knowledge/sources"),
  upload: async (files: File[]) => {
    const form = new FormData()
    files.forEach((file) => form.append("files", file))
    const response = await fetch("/api/knowledge/upload", { method: "POST", body: form })
    if (!response.ok) throw new Error(await response.text())
    return (await response.json()) as {
      results: { file: string; chunks?: number; error?: string }[]
    }
  },
  ingestDirectory: () => post<{ results: Record<string, number> }>("/knowledge/ingest-directory"),
  capture: (symbol: string) => post<{ symbol: string; chunks: number }>("/knowledge/capture", { symbol }),
  searchIndex: (query: string, k?: number) =>
    post<{ query: string; ms: number; passages: Passage[] }>("/knowledge/search", { query, k }),
  deleteSource: (source: string) =>
    request<unknown>(`/knowledge/sources/${encodeURIComponent(source)}`, { method: "DELETE" }),
  resetIndex: () => post<unknown>("/knowledge/reset"),

  // -- chat -----------------------------------------------------------------
  resetChat: () => post<unknown>("/chat/reset"),
}
