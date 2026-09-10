/**
 * Price prediction — the ensemble signal plus the Monte Carlo simulation.
 *
 * It runs on its own as soon as a symbol is opened; nobody has to press Run.
 * The headline is the odds and the range, not a single target price, and the
 * "no guarantee" notice is always on screen next to it.
 */

import { useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { ChevronDown, FlaskConical, Loader2, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Rise } from "@/components/ui/motion-primitives"
import { NoGuarantee, NoGuaranteePill, SimulationPanel } from "@/components/market/SimulationPanel"
import { useForecast } from "@/hooks/use-kinetic"
import { money, signalTone } from "@/lib/format"
import { cn } from "@/lib/utils"

const HORIZONS = [5, 10, 20] as const

export function ForecastPanel({ symbol }: { symbol: string }) {
  const [horizon, setHorizon] = useState<number>(10)
  const [open, setOpen] = useState<string | null>(null)
  const { data: forecast, isFetching, isError, refetch } = useForecast(symbol, horizon, true)

  return (
    <Rise delay={0.08} className="glass border-lime/25 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <FlaskConical className="size-4 text-lime" strokeWidth={1.8} />
          <h2 className="text-[1.05rem] font-semibold text-ink">Price prediction &amp; simulation</h2>
          <NoGuaranteePill />
          <span className="label hidden md:inline">
            5 signals · 2,000 simulated futures · backtested
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-border/60 p-0.5" role="group" aria-label="Horizon">
            {HORIZONS.map((value) => (
              <button
                key={value}
                onClick={() => setHorizon(value)}
                aria-pressed={horizon === value}
                className={cn(
                  "rounded-md px-2.5 py-1 font-mono text-[0.7rem] transition-colors",
                  horizon === value ? "bg-lime/15 text-lime" : "text-ink-dim hover:text-ink",
                )}
              >
                {value}d
              </button>
            ))}
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            aria-label="Refresh prediction"
          >
            {isFetching ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
            Refresh
          </Button>
        </div>
      </div>

      {!forecast && isFetching && (
        <div className="mt-5 space-y-3">
          <p className="flex items-center gap-2 text-[0.8rem] text-ink-muted">
            <Loader2 className="size-3.5 animate-spin text-lime" />
            Scoring five signals, simulating 2,000 futures and backtesting two years of history…
          </p>
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      )}

      {!forecast && isError && !isFetching && (
        <p className="mt-4 text-[0.8rem] text-ink-dim">
          Could not build a prediction for {symbol} — there is no live data for it right now.
        </p>
      )}

      <AnimatePresence mode="wait">
        {forecast && (
          <motion.div
            key={`${forecast.symbol}-${forecast.horizon_days}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="mt-5 space-y-5"
          >
            <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
              {/* -- headline ------------------------------------------------ */}
              <div>
                <div className="flex flex-wrap items-baseline gap-3">
                  <span className={cn("text-[1.6rem] font-semibold tracking-[-0.03em]", signalTone(forecast.signal))}>
                    {forecast.signal}
                  </span>
                  <span className="numeric text-[0.8rem] text-ink-dim">
                    {forecast.direction >= 0 ? "+" : ""}
                    {forecast.direction.toFixed(2)}
                  </span>
                </div>
                {forecast.probability_up !== null && (
                  <p className="mt-1 text-[0.82rem] text-ink-muted">
                    <span className="numeric text-ink">{Math.round(forecast.probability_up * 100)}%</span>{" "}
                    of simulated futures end higher in {forecast.horizon_days} sessions.
                  </p>
                )}

                <div className="mt-4 space-y-3">
                  {[
                    { label: "Confidence", value: forecast.confidence, suffix: "%", tone: "lime" },
                    {
                      label: "Risk",
                      value: forecast.risk_score * 10,
                      suffix: `/10 · ${forecast.risk_label}`,
                      tone: "ember",
                      display: forecast.risk_score,
                    },
                  ].map((row) => (
                    <div key={row.label}>
                      <div className="flex items-baseline justify-between text-[0.78rem]">
                        <span className="text-ink-muted">{row.label}</span>
                        <span className="numeric text-ink">
                          {row.display ?? row.value.toFixed(0)}
                          {row.suffix}
                        </span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${row.value}%` }}
                          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                          className={cn(
                            "h-full rounded-full",
                            row.tone === "lime"
                              ? "bg-gradient-to-r from-lime-deep to-lime"
                              : "bg-gradient-to-r from-ember/60 to-ember",
                          )}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {forecast.expected_low !== null && (
                  <div className="mt-5 rounded-lg border border-lime/20 bg-lime/[0.05] p-3.5">
                    <div className="label">{forecast.horizon_days}-session likely range · 68%</div>
                    <div className="numeric mt-1 text-[1.05rem] text-ink">
                      {money(forecast.expected_low)} – {money(forecast.expected_high)}{" "}
                      <span className="text-ink-dim">{forecast.currency}</span>
                    </div>
                    <p className="mt-1 text-[0.7rem] leading-relaxed text-ink-dim">
                      About two in three simulated futures land inside this band.
                    </p>
                  </div>
                )}

                {forecast.drivers.length > 0 && (
                  <ul className="mt-4 space-y-1.5">
                    {forecast.drivers.map((driver) => (
                      <li key={driver} className="border-l border-lime/25 pl-2.5 text-[0.74rem] leading-relaxed text-ink-muted">
                        {driver}
                      </li>
                    ))}
                  </ul>
                )}

                <p className="mt-3 text-[0.7rem] text-ink-dim">{forecast.data_quality}</p>
              </div>

              {/* -- legs ---------------------------------------------------- */}
              <div className="space-y-2">
                {forecast.legs.map((leg) => (
                  <div
                    key={leg.key}
                    className={cn(
                      "rounded-lg border border-border/50 px-3.5 py-3 transition-colors",
                      !leg.available && "opacity-50",
                    )}
                  >
                    <button
                      className="flex w-full items-center justify-between text-left"
                      onClick={() => setOpen(open === leg.key ? null : leg.key)}
                      disabled={!leg.notes.length}
                      aria-expanded={open === leg.key}
                    >
                      <span className="text-[0.83rem] text-ink">{leg.name}</span>
                      <span className="flex items-center gap-2">
                        <span
                          className={cn(
                            "numeric text-[0.78rem]",
                            leg.score > 0.05 ? "text-lime" : leg.score < -0.05 ? "text-ember" : "text-ink-dim",
                          )}
                        >
                          {leg.available ? `${leg.score >= 0 ? "+" : ""}${leg.score.toFixed(2)}` : "no data"}
                        </span>
                        <span className="numeric text-[0.7rem] text-ink-dim">
                          {leg.available ? `${(leg.weight * 100).toFixed(0)}%` : "excluded"}
                        </span>
                        {leg.notes.length > 0 && (
                          <ChevronDown
                            className={cn("size-3.5 text-ink-dim transition-transform", open === leg.key && "rotate-180")}
                          />
                        )}
                      </span>
                    </button>

                    <div className="mt-2 h-1 overflow-hidden rounded-full bg-surface">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.abs(leg.score) * 100}%` }}
                        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                        className={cn("h-full rounded-full", leg.score >= 0 ? "bg-lime/70" : "bg-ember/70")}
                      />
                    </div>

                    <AnimatePresence initial={false}>
                      {open === leg.key && (
                        <motion.ul
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                          className="overflow-hidden"
                        >
                          {leg.notes.map((note) => (
                            <li
                              key={note}
                              className="mt-2 border-l border-lime/25 pl-2.5 text-[0.74rem] leading-relaxed text-ink-muted"
                            >
                              {note}
                            </li>
                          ))}
                        </motion.ul>
                      )}
                    </AnimatePresence>
                  </div>
                ))}
              </div>
            </div>

            <div className="hairline" />

            <SimulationPanel forecast={forecast} />

            <NoGuarantee text={forecast.guarantee.replace(/^No guarantee\.\s*/, "")} />
          </motion.div>
        )}
      </AnimatePresence>
    </Rise>
  )
}
