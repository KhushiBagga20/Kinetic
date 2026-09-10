/**
 * Data hooks.
 *
 * Everything the interface shows is server state, so it all goes through React
 * Query: one cache, one place to say how stale each kind of number is allowed
 * to be. Prices refresh on their own; the index and the model do not.
 */

import { useEffect } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type { Preferences } from "@/lib/types"

const LIVE = 20_000 // quotes: a page left open should not go stale
const SLOW = 5 * 60_000 // fundamentals, news

export const useStatus = () =>
  useQuery({ queryKey: ["status"], queryFn: api.status, refetchInterval: 30_000 })

export const useIndexStats = () => useQuery({ queryKey: ["index-stats"], queryFn: api.indexStats })

export const usePreferences = () => useQuery({ queryKey: ["preferences"], queryFn: api.preferences })

export const useIndices = () =>
  useQuery({ queryKey: ["indices"], queryFn: api.indices, refetchInterval: LIVE })

export const useQuote = (symbol: string | undefined) =>
  useQuery({
    queryKey: ["quote", symbol],
    queryFn: () => api.quote(symbol!),
    enabled: Boolean(symbol),
    refetchInterval: LIVE,
  })

export const useHistory = (symbol: string | undefined, period: string) =>
  useQuery({
    queryKey: ["history", symbol, period],
    queryFn: () => api.history(symbol!, period),
    enabled: Boolean(symbol),
    staleTime: SLOW,
  })

export const useNews = (symbol: string | undefined, limit?: number) =>
  useQuery({
    queryKey: ["news", symbol, limit],
    queryFn: () => api.news(symbol!, limit),
    enabled: Boolean(symbol),
    staleTime: SLOW,
  })

export const useIndicators = (symbol: string | undefined) =>
  useQuery({
    queryKey: ["indicators", symbol],
    queryFn: () => api.indicators(symbol!),
    enabled: Boolean(symbol),
    staleTime: SLOW,
  })

export const useFundamentals = (symbol: string | undefined) =>
  useQuery({
    queryKey: ["fundamentals", symbol],
    queryFn: () => api.fundamentals(symbol!),
    enabled: Boolean(symbol),
    staleTime: SLOW,
  })

export const useSession = (symbol: string | undefined) =>
  useQuery({
    queryKey: ["session", symbol],
    queryFn: () => api.session(symbol!),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  })

export const useMovers = (kind: string) =>
  useQuery({ queryKey: ["movers", kind], queryFn: () => api.movers(kind), refetchInterval: 60_000 })

export const useForecast = (symbol: string | undefined, horizon: number, enabled: boolean) =>
  useQuery({
    queryKey: ["forecast", symbol, horizon],
    queryFn: () => api.forecast(symbol!, horizon),
    enabled: Boolean(symbol) && enabled,
    staleTime: SLOW,
    refetchInterval: SLOW, // stays current on its own while the page is open
  })

export const usePortfolio = () =>
  useQuery({ queryKey: ["portfolio"], queryFn: api.portfolio, refetchInterval: 30_000 })

// -- automation ----------------------------------------------------------------
// The backend rebuilds these on its own timer; the page only has to look.
// While the first build is still running, poll quickly so it appears as soon
// as it is ready, then settle to a slow check.

const pollUntilReady = (data: { ready?: boolean } | undefined) => (data?.ready ? 60_000 : 4_000)

// Browsers pause timers in hidden tabs, so also check the moment the user
// comes back to the tab — they should see the newest results straight away.
export const useBriefing = () =>
  useQuery({
    queryKey: ["briefing"],
    queryFn: api.briefing,
    refetchInterval: (query) => pollUntilReady(query.state.data),
    refetchOnWindowFocus: true,
  })

export const useAutoExposure = () =>
  useQuery({
    queryKey: ["auto-exposure"],
    queryFn: api.autoExposure,
    refetchInterval: (query) => pollUntilReady(query.state.data),
    refetchOnWindowFocus: true,
  })

export function useRefreshAutomation() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.refreshAutomation,
    onSuccess: () => {
      // Check back shortly: the rebuild runs in the background.
      window.setTimeout(() => {
        client.invalidateQueries({ queryKey: ["briefing"] })
        client.invalidateQueries({ queryKey: ["auto-exposure"] })
      }, 1500)
    },
  })
}

export const useSources = () => useQuery({ queryKey: ["sources"], queryFn: api.sources })

/** Debounced live symbol search, used by ⌘K. */
export function useSymbolSearch(query: string) {
  const client = useQueryClient()
  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (query.trim().length > 1) client.invalidateQueries({ queryKey: ["symbol-search", query] })
    }, 250)
    return () => window.clearTimeout(timer)
  }, [query, client])

  return useQuery({
    queryKey: ["symbol-search", query],
    queryFn: () => api.search(query),
    enabled: query.trim().length > 1,
    staleTime: SLOW,
  })
}

export function useLoadModel() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (action: "load" | "unload") =>
      action === "load" ? api.loadModel() : api.unloadModel(),
    onSuccess: () => client.invalidateQueries({ queryKey: ["status"] }),
  })
}

export function useSavePreferences() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (changes: Partial<Preferences>) => api.savePreferences(changes),
    onSuccess: (data) => client.setQueryData(["preferences"], data),
  })
}

export function useWatchlist() {
  const { data: prefs } = usePreferences()
  const save = useSavePreferences()

  return {
    add: async (query: string) => {
      const { symbol } = await api.resolve(query)
      const next = Array.from(new Set([...(prefs?.watchlist ?? []), symbol]))
      save.mutate({ watchlist: next })
      return symbol
    },
    remove: (symbol: string) =>
      save.mutate({ watchlist: (prefs?.watchlist ?? []).filter((s) => s !== symbol) }),
  }
}

export function usePortfolioMutations() {
  const client = useQueryClient()
  const refresh = () => {
    client.invalidateQueries({ queryKey: ["portfolio"] })
    // The backend starts rebuilding exposure and the briefing for the new book.
    client.invalidateQueries({ queryKey: ["briefing"] })
    client.invalidateQueries({ queryKey: ["auto-exposure"] })
  }
  return {
    add: useMutation({ mutationFn: api.addHolding, onSuccess: refresh }),
    remove: useMutation({ mutationFn: api.removeHolding, onSuccess: refresh }),
    exposure: useMutation({ mutationFn: api.exposure }),
  }
}

export function useKnowledgeMutations() {
  const client = useQueryClient()
  const refresh = () => {
    client.invalidateQueries({ queryKey: ["index-stats"] })
    client.invalidateQueries({ queryKey: ["sources"] })
  }
  return {
    upload: useMutation({ mutationFn: api.upload, onSuccess: refresh }),
    ingestDirectory: useMutation({ mutationFn: api.ingestDirectory, onSuccess: refresh }),
    capture: useMutation({ mutationFn: api.capture, onSuccess: refresh }),
    remove: useMutation({ mutationFn: api.deleteSource, onSuccess: refresh }),
    reset: useMutation({ mutationFn: api.resetIndex, onSuccess: refresh }),
    search: useMutation({ mutationFn: ({ query, k }: { query: string; k?: number }) => api.searchIndex(query, k) }),
  }
}
