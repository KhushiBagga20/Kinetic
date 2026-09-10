/** Shapes returned by the Kinetic backend. One place, so views stay honest. */

export interface Quote {
  symbol: string
  name: string
  price: number | null
  previous_close: number | null
  change: number | null
  change_percent: number | null
  currency: string
  exchange: string
  quote_type: string
  volume: number | null
  market_cap: number | null
  day_low: number | null
  day_high: number | null
  year_low: number | null
  year_high: number | null
  market_state: string
  as_of: string
  source: string
}

export interface Candle {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  sma20: number | null
  sma50: number | null
}

export interface Article {
  title: string
  publisher: string
  published: string
  url: string
  summary: string
  provider: string
  symbol: string
}

export interface Mover {
  symbol: string
  name: string
  price: number | null
  change_percent: number | null
  volume: number | null
  currency: string
}

export interface Indicator {
  key: string
  value: number | null
  signal: number
  note: string
}

export interface Position {
  symbol: string
  name: string
  quantity: number
  average_cost: number
  currency: string
  price: number | null
  market_value: number | null
  cost_basis: number
  unrealised: number | null
  unrealised_percent: number | null
  day_change_percent: number | null
  day_change_value: number | null
  value_in_base: number | null
  weight: number
  sector: string
  market_session: string
  as_of: string
}

export interface PortfolioSummary {
  holdings: number
  base_currency: string
  market_value?: number
  cost_basis?: number
  unrealised?: number
  unrealised_percent?: number
  day_change?: number
  day_change_percent?: number
  largest_position?: string
  largest_weight?: number
  sectors?: Record<string, number>
  as_of: string
}

export interface Exposure {
  symbol: string
  name: string
  relevance: number
  weight: number
  value_in_base: number | null
  sector: string
  day_change_percent: number | null
}

export interface ForecastLeg {
  key: string
  name: string
  score: number
  weight: number
  available: boolean
  notes: string[]
}

export interface Forecast {
  symbol: string
  name: string
  price: number | null
  currency: string
  signal: string
  direction: number
  confidence: number
  risk_score: number
  risk_label: string
  horizon_days: number
  expected_low: number | null
  expected_high: number | null
  legs: ForecastLeg[]
  drivers: string[]
  data_quality: string
  as_of: string
}

export interface Passage {
  text: string
  label: string
  source: string
  score: number
  collection: string
  kind: "live" | "document"
  metadata: Record<string, unknown>
}

export interface IndexStats {
  documents: number
  market_feed: number
  path: string
  embedding_model: string
  chunk_size: number
  chunk_overlap: number
  retrieval_k: number
  documents_dir: string
}

export interface SourceRow {
  source: string
  chunks: number
  kind: string
  ingested: string
}

export interface SystemStatus {
  model: {
    model: string
    loaded: boolean
    load_seconds: number
    error: string
    backend: string
  }
  index: { documents: number; market_feed: number; path: string; embedding_model: string }
  providers: { market: string; news: string }
  settings: {
    base_currency: string
    default_symbol: string
    index_symbols: string[]
    retrieval_k: number
    weights: Record<string, number>
  }
  disclaimer: string
}

export interface Preferences {
  name: string
  base_currency: string
  horizon: string
  risk_appetite: string
  watchlist: string[]
  text_size: string
  high_contrast: boolean
  reduce_motion: boolean
  options: { horizons: string[]; risk_appetites: string[]; text_sizes: string[] }
}

/** One update from the agent while it works. */
export interface AgentEvent {
  kind:
    | "status"
    | "sources"
    | "thought"
    | "token"
    | "step_reset"
    | "tool_call"
    | "tool_result"
    | "done"
    | "error"
  text: string
  data: {
    passages?: Passage[]
    ms?: number
    arguments?: Record<string, unknown>
    result?: string
    tools_used?: string[]
    seconds?: number
    tokens?: number
    tokens_per_sec?: number
  }
}
