/**
 * Home — the user's own book first, the market second.
 *
 * Nothing here is a generic dashboard tile: the numbers are their positions,
 * the alerts are about their money, and every row leads somewhere.
 */

import { useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { motion } from "motion/react"
import { ArrowRight, Flame, ShieldAlert, Sparkles, TrendingDown, TrendingUp } from "lucide-react"

import { Delta } from "@/components/market/Delta"
import { StatCard } from "@/components/market/StatCard"
import { NumberFlow } from "@/components/ui/number-flow"
import { Rise, Stagger, StaggerItem } from "@/components/ui/motion-primitives"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Onboarding } from "@/components/layout/Onboarding"
import { Briefing } from "@/components/home/Briefing"
import {
  useIndices,
  useMovers,
  usePortfolio,
  usePreferences,
  useSession,
  useStatus,
} from "@/hooks/use-kinetic"
import { compact, money, percent } from "@/lib/format"
import { cn } from "@/lib/utils"

function greeting() {
  const hour = new Date().getHours()
  if (hour < 12) return "Good morning"
  if (hour < 17) return "Good afternoon"
  return "Good evening"
}

/** Only surface a position when there is a reason to look at it. */
function useAttention() {
  const { data } = usePortfolio()
  return useMemo(() => {
    const rows = data?.positions ?? []
    const summary = data?.summary
    const flags: { symbol: string; reason: string; kind: "move" | "loss" | "risk" }[] = []

    for (const row of rows) {
      if (row.day_change_percent !== null && Math.abs(row.day_change_percent) >= 3) {
        flags.push({
          symbol: row.symbol,
          reason: `moved ${row.day_change_percent > 0 ? "up" : "down"} ${Math.abs(row.day_change_percent).toFixed(1)}% today`,
          kind: "move",
        })
      } else if (row.unrealised_percent !== null && row.unrealised_percent <= -20) {
        flags.push({
          symbol: row.symbol,
          reason: `down ${Math.abs(row.unrealised_percent).toFixed(0)}% against your cost`,
          kind: "loss",
        })
      }
    }
    if (summary?.largest_weight && summary.largest_weight >= 40) {
      flags.push({
        symbol: summary.largest_position ?? "",
        reason: `is ${summary.largest_weight.toFixed(0)}% of the whole book`,
        kind: "risk",
      })
    }
    return flags.slice(0, 4)
  }, [data])
}

export function HomePage() {
  const navigate = useNavigate()
  const { data: prefs, isLoading: prefsLoading } = usePreferences()
  const { data: status } = useStatus()
  const { data: portfolio, isLoading: portfolioLoading } = usePortfolio()
  const { data: indices = [] } = useIndices()
  const { data: movers = [] } = useMovers("day_gainers")
  const { data: session } = useSession(status?.settings.default_symbol)
  const attention = useAttention()

  const positions = portfolio?.positions ?? []
  const summary = portfolio?.summary
  const base = summary?.base_currency ?? "INR"
  const setUp = Boolean(prefs?.name) || positions.length > 0

  const best = positions.reduce<(typeof positions)[number] | null>(
    (top, row) =>
      row.day_change_percent !== null && (!top || row.day_change_percent > (top.day_change_percent ?? -Infinity))
        ? row
        : top,
    null,
  )
  const worst = positions.reduce<(typeof positions)[number] | null>(
    (low, row) =>
      row.day_change_percent !== null && (!low || row.day_change_percent < (low.day_change_percent ?? Infinity))
        ? row
        : low,
    null,
  )

  const ask = (question: string) =>
    navigate(`/assistant?q=${encodeURIComponent(question)}`)

  // Wait until we actually know — otherwise onboarding flashes on every reload.
  if (prefsLoading || portfolioLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-72 rounded-lg" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((index) => (
            <Skeleton key={index} className="h-[92px] rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-56 rounded-xl" />
      </div>
    )
  }
  if (!setUp) return <Onboarding />

  return (
    <div className="space-y-6">
      {/* -- greeting ------------------------------------------------------- */}
      <Rise className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[2rem] font-semibold leading-none tracking-[-0.035em] text-ink">
            {greeting()}
            {prefs?.name ? `, ${prefs.name.split(" ")[0]}` : ""}
          </h1>
          <p className="mt-2 flex items-center gap-2 text-[0.8rem] text-ink-muted">
            <span className="live-dot" />
            {session?.exchange || "Market"} is{" "}
            <span className="text-lime">{session?.label ?? "…"}</span>
            <span className="text-ink-dim">·</span>
            <span className="numeric text-ink-dim">
              {indices[0]?.name} {percent(indices[0]?.change_percent)}
            </span>
          </p>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => navigate("/portfolio")}>
            Open portfolio
            <ArrowRight className="size-3.5" />
          </Button>
          <Button
            size="sm"
            onClick={() => ask("How is my portfolio doing today, and what drove the move?")}
          >
            <Sparkles className="size-3.5" />
            Ask about my book
          </Button>
        </div>
      </Rise>

      {/* -- the book ------------------------------------------------------- */}
      {positions.length > 0 && summary && (
        <Stagger className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StaggerItem>
            <StatCard
              label="Your book"
              accent
              value={<NumberFlow value={summary.market_value} format={(v) => compact(v)} />}
              detail={`${summary.holdings} holdings · ${base}`}
            />
          </StaggerItem>
          <StaggerItem>
            <StatCard
              label="Today"
              value={
                <NumberFlow
                  value={summary.day_change}
                  format={(v) => `${v >= 0 ? "+" : ""}${money(v, "", 0)}`}
                />
              }
              detail={<Delta value={summary.day_change_percent} />}
            />
          </StaggerItem>
          <StaggerItem>
            <StatCard
              label="Unrealised"
              value={
                <NumberFlow
                  value={summary.unrealised}
                  format={(v) => `${v >= 0 ? "+" : ""}${money(v, "", 0)}`}
                />
              }
              detail={<Delta value={summary.unrealised_percent} />}
            />
          </StaggerItem>
          <StaggerItem>
            <StatCard
              label="Concentration"
              value={`${summary.largest_weight?.toFixed(0) ?? 0}%`}
              detail={`in ${summary.largest_position}`}
            />
          </StaggerItem>
        </Stagger>
      )}

      {/* -- automatic briefing: already written when the page opens -------- */}
      <Briefing />

      <div className="grid items-start gap-5 lg:grid-cols-[1.4fr_1fr]">
        {/* -- attention --------------------------------------------------- */}
        <Rise delay={0.05} className="glass p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="section-title">Worth a look</h2>
            <span className="label">your positions only</span>
          </div>

          {attention.length === 0 ? (
            <p className="py-6 text-center text-[0.82rem] text-ink-dim">
              Nothing in your book moved sharply today.
            </p>
          ) : (
            <Stagger className="space-y-2">
              {attention.map((flag) => {
                const Icon =
                  flag.kind === "risk" ? ShieldAlert : flag.kind === "loss" ? TrendingDown : Flame
                return (
                  <StaggerItem key={`${flag.symbol}-${flag.reason}`}>
                    <button
                      onClick={() => navigate(`/research?symbol=${encodeURIComponent(flag.symbol)}`)}
                      className="group flex w-full items-center gap-3 rounded-lg border border-border/60 bg-white/[0.015] px-3.5 py-3 text-left transition-colors hover:border-lime/30 hover:bg-lime/[0.05]"
                    >
                      <Icon
                        className={cn(
                          "size-4 shrink-0",
                          flag.kind === "risk" ? "text-ember" : "text-lime",
                        )}
                        strokeWidth={1.8}
                      />
                      <span className="font-mono text-[0.82rem] text-ink">{flag.symbol}</span>
                      <span className="flex-1 text-[0.8rem] text-ink-muted">{flag.reason}</span>
                      <ArrowRight className="size-3.5 -translate-x-1 text-ink-dim opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
                    </button>
                  </StaggerItem>
                )
              })}
            </Stagger>
          )}

          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {[
              ["Where am I over-exposed?", "What is my biggest concentration risk right now?"],
              ["News on what I own", "Summarise today's headlines for my holdings and flag what matters."],
              ["What's moving?", "What are the biggest moves in the market right now, and do any of them touch my holdings?"],
              ["Is my book at risk?", "Given my holdings and their sectors, what is the main risk in my portfolio today?"],
            ].map(([label, question]) => (
              <button
                key={label}
                onClick={() => ask(question)}
                className="group flex items-center justify-between rounded-lg border border-border/50 px-3 py-2.5 text-left text-[0.78rem] text-ink-muted transition-colors hover:border-lime/30 hover:text-ink"
              >
                {label}
                <Sparkles className="size-3 text-ink-dim transition-colors group-hover:text-lime" />
              </button>
            ))}
          </div>
        </Rise>

        {/* -- movers ------------------------------------------------------ */}
        <Rise delay={0.1} className="glass p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="section-title">Today&rsquo;s gainers</h2>
            <span className="label">live screener</span>
          </div>
          <Stagger className="space-y-1">
            {movers.slice(0, 7).map((mover) => (
              <StaggerItem key={mover.symbol}>
                <button
                  onClick={() => navigate(`/research?symbol=${encodeURIComponent(mover.symbol)}`)}
                  className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors hover:bg-lime/[0.06]"
                >
                  <span className="w-16 shrink-0 font-mono text-[0.78rem] text-ink">
                    {mover.symbol}
                  </span>
                  <span className="flex-1 truncate text-[0.76rem] text-ink-dim">{mover.name}</span>
                  <Delta value={mover.change_percent} />
                </button>
              </StaggerItem>
            ))}
          </Stagger>
        </Rise>
      </div>

      {/* -- best / worst -------------------------------------------------- */}
      {best && worst && (
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            { row: best, label: "Best today", Icon: TrendingUp },
            { row: worst, label: "Weakest today", Icon: TrendingDown },
          ].map(({ row, label, Icon }) => (
            <motion.button
              key={label}
              whileHover={{ y: -2 }}
              onClick={() => navigate(`/research?symbol=${encodeURIComponent(row.symbol)}`)}
              className="glass flex items-center gap-4 px-4 py-3.5 text-left"
            >
              <Icon className="size-5 text-ink-dim" strokeWidth={1.6} />
              <div className="flex-1">
                <div className="label">{label}</div>
                <div className="mt-0.5 font-mono text-[0.9rem] text-ink">{row.symbol}</div>
              </div>
              <Delta value={row.day_change_percent} size="lg" />
            </motion.button>
          ))}
        </div>
      )}
    </div>
  )
}
