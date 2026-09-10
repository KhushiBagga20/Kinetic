/**
 * Research — one symbol, examined from every angle the backend can offer.
 *
 * The chart is the anchor; quote statistics sit above it, the technical read
 * and the ensemble forecast beside it, and the news underneath.
 */

import { useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { AnimatePresence, motion } from "motion/react"
import { BookmarkPlus, Database, ExternalLink, Loader2, Radio } from "lucide-react"
import { toast } from "sonner"

import { Delta } from "@/components/market/Delta"
import { ForecastPanel } from "@/components/market/ForecastPanel"
import { PriceChart } from "@/components/market/PriceChart"
import { StatCard } from "@/components/market/StatCard"
import { NumberFlow } from "@/components/ui/number-flow"
import { Rise, Stagger, StaggerItem } from "@/components/ui/motion-primitives"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  useHistory,
  useIndicators,
  useKnowledgeMutations,
  useNews,
  useQuote,
  useSession,
  useStatus,
  useWatchlist,
} from "@/hooks/use-kinetic"
import { api } from "@/lib/api"
import { compact, money } from "@/lib/format"
import { cn } from "@/lib/utils"

const PERIODS = ["1mo", "3mo", "6mo", "1y", "5y"] as const
const PERIOD_LABELS: Record<string, string> = {
  "1mo": "1M",
  "3mo": "3M",
  "6mo": "6M",
  "1y": "1Y",
  "5y": "5Y",
}

export function ResearchPage() {
  const [params, setParams] = useSearchParams()
  const { data: status } = useStatus()
  const [draft, setDraft] = useState("")
  const [period, setPeriod] = useState<string>("6mo")
  const [resolving, setResolving] = useState(false)

  const symbol = params.get("symbol") ?? status?.settings.default_symbol ?? ""

  const { data: quote, isLoading: quoteLoading } = useQuote(symbol)
  const { data: history } = useHistory(symbol, period)
  const { data: technicals } = useIndicators(symbol)
  const { data: news = [] } = useNews(symbol, 6)
  const { data: session } = useSession(symbol)
  const watchlist = useWatchlist()
  const { capture } = useKnowledgeMutations()

  useEffect(() => setDraft(""), [symbol])

  const search = async (query: string) => {
    if (!query.trim()) return
    setResolving(true)
    try {
      const { symbol: resolved } = await api.resolve(query.trim())
      setParams({ symbol: resolved })
    } catch {
      toast.error(`No instrument found for “${query}”`)
    } finally {
      setResolving(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* -- symbol bar ----------------------------------------------------- */}
      <Rise className="flex flex-wrap items-center gap-3">
        <form
          className="flex flex-1 gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            search(draft)
          }}
        >
          <Input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={`${symbol} — type any company or ticker`}
            className="h-10 max-w-md"
          />
          <Button type="submit" variant="outline" className="h-10" disabled={resolving}>
            {resolving ? <Loader2 className="size-4 animate-spin" /> : "Go"}
          </Button>
        </form>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-9"
            onClick={() =>
              watchlist.add(symbol).then(() => toast.success(`${symbol} added to your watchlist`))
            }
          >
            <BookmarkPlus className="size-3.5" />
            Watch
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-9"
            disabled={capture.isPending}
            onClick={() =>
              capture.mutate(symbol, {
                onSuccess: (result) =>
                  toast.success(`Indexed ${result.chunks} live passages for ${result.symbol}`),
              })
            }
          >
            {capture.isPending ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Database className="size-3.5" />
            )}
            Capture to index
          </Button>
        </div>
      </Rise>

      {/* -- identity ------------------------------------------------------- */}
      <AnimatePresence mode="wait">
        <motion.div
          key={symbol}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-wrap items-end gap-x-4 gap-y-2"
        >
          <h1 className="font-mono text-[1.7rem] font-semibold tracking-[-0.03em] text-lime">
            {symbol}
          </h1>
          <span className="text-[0.95rem] text-ink">{quote?.name}</span>
          <span className="flex items-center gap-1.5 text-[0.72rem] text-ink-dim">
            <Radio className="size-3" />
            {session?.exchange} · {session?.label}
          </span>
          {quote && (
            <span className="ml-auto flex items-baseline gap-3">
              <NumberFlow
                value={quote.price}
                format={(v) => money(v, quote.currency)}
                className="text-[1.6rem] font-semibold tracking-[-0.03em]"
              />
              <Delta value={quote.change_percent} size="lg" />
            </span>
          )}
        </motion.div>
      </AnimatePresence>

      {/* -- session stats -------------------------------------------------- */}
      {quoteLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((index) => (
            <Skeleton key={index} className="h-[92px] rounded-xl" />
          ))}
        </div>
      ) : (
        quote && (
          <Stagger className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StaggerItem>
              <StatCard
                label="Day range"
                value={
                  <span className="numeric text-[1.15rem]">
                    {money(quote.day_low)} – {money(quote.day_high)}
                  </span>
                }
                detail={quote.currency}
              />
            </StaggerItem>
            <StaggerItem>
              <StatCard
                label="52-week range"
                value={
                  <span className="numeric text-[1.15rem]">
                    {money(quote.year_low)} – {money(quote.year_high)}
                  </span>
                }
                detail={quote.currency}
              />
            </StaggerItem>
            <StaggerItem>
              <StatCard label="Volume" value={compact(quote.volume)} detail="shares traded" />
            </StaggerItem>
            <StaggerItem>
              <StatCard
                label="Market cap"
                value={compact(quote.market_cap)}
                detail={quote.currency}
              />
            </StaggerItem>
          </Stagger>
        )
      )}

      <div className="grid items-start gap-5 lg:grid-cols-[1.55fr_1fr]">
        {/* -- chart -------------------------------------------------------- */}
        <Rise delay={0.05} className="glass p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="section-title">Price</h2>
            <Tabs value={period} onValueChange={setPeriod}>
              <TabsList className="h-8">
                {PERIODS.map((value) => (
                  <TabsTrigger key={value} value={value} className="h-6 px-2.5 font-mono text-[0.7rem]">
                    {PERIOD_LABELS[value]}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
          </div>

          {history?.candles.length ? (
            <PriceChart
              candles={history.candles}
              currency={quote?.currency ?? ""}
              height={390}
            />
          ) : (
            <Skeleton className="h-[390px] rounded-lg" />
          )}
        </Rise>

        {/* -- technical read ---------------------------------------------- */}
        <Rise delay={0.1} className="glass p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="section-title">Technical read</h2>
            {technicals && (
              <span
                className={cn(
                  "numeric text-[0.76rem]",
                  technicals.score > 0.05 ? "text-lime" : technicals.score < -0.05 ? "text-ember" : "text-ink-dim",
                )}
              >
                score {technicals.score >= 0 ? "+" : ""}
                {technicals.score.toFixed(2)}
              </span>
            )}
          </div>

          <Stagger className="space-y-2.5">
            {(technicals?.indicators ?? []).map((indicator) => (
              <StaggerItem key={indicator.key}>
                <div className="flex items-baseline justify-between text-[0.8rem]">
                  <span className="capitalize text-ink">{indicator.key.replace(/_/g, " ")}</span>
                  <span className="numeric text-ink-muted">{indicator.value}</span>
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-surface">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, Math.abs(indicator.signal) * 100)}%` }}
                    transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                    className={cn(
                      "h-full rounded-full",
                      indicator.signal >= 0 ? "bg-lime/70" : "bg-ember/70",
                    )}
                  />
                </div>
                <p className="mt-1 text-[0.7rem] leading-relaxed text-ink-dim">{indicator.note}</p>
              </StaggerItem>
            ))}
          </Stagger>
        </Rise>
      </div>

      <ForecastPanel symbol={symbol} />

      {/* -- news ----------------------------------------------------------- */}
      <Rise delay={0.15} className="glass p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="section-title">Live headlines</h2>
          <span className="label">Yahoo Finance</span>
        </div>
        <Stagger className="grid gap-2 md:grid-cols-2">
          {news.map((article) => (
            <StaggerItem key={article.url || article.title}>
              <a
                href={article.url}
                target="_blank"
                rel="noreferrer"
                className="group block h-full rounded-lg border border-border/50 p-3.5 transition-colors hover:border-lime/25 hover:bg-lime/[0.04]"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-[0.83rem] font-medium leading-snug text-ink">
                    {article.title}
                  </h3>
                  <ExternalLink className="mt-0.5 size-3 shrink-0 text-ink-dim opacity-0 transition-opacity group-hover:opacity-100" />
                </div>
                {article.summary && (
                  <p className="mt-1.5 line-clamp-2 text-[0.74rem] leading-relaxed text-ink-dim">
                    {article.summary}
                  </p>
                )}
                <div className="mt-2 font-mono text-[0.66rem] text-ink-dim">
                  {article.publisher} · {article.published}
                </div>
              </a>
            </StaggerItem>
          ))}
        </Stagger>
      </Rise>
    </div>
  )
}
