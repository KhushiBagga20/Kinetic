/**
 * The ensemble forecast, shown as four independent legs rather than one number.
 *
 * The point is legibility: which leg moved the score, how much of the data was
 * actually available, and how wide the honest range is. The headline signal is
 * deliberately not the biggest thing on screen — the range is.
 */

import { useState } from "react"
import { AnimatePresence, motion } from "motion/react"
import { Activity, ChevronDown, Loader2, Play } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Rise } from "@/components/ui/motion-primitives"
import { useForecast } from "@/hooks/use-kinetic"
import { money } from "@/lib/format"
import { cn } from "@/lib/utils"

const HORIZONS = [5, 10, 20] as const

function tone(signal: string) {
  if (signal.includes("BULL")) return "text-lime"
  if (signal.includes("BEAR")) return "text-ember"
  return "text-ink-muted"
}

export function ForecastPanel({ symbol }: { symbol: string }) {
  const [horizon, setHorizon] = useState<number>(10)
  const [enabled, setEnabled] = useState(false)
  const [open, setOpen] = useState<string | null>(null)
  const { data: forecast, isFetching } = useForecast(symbol, horizon, enabled)

  return (
    <Rise delay={0.12} className="glass p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity className="size-4 text-lime" strokeWidth={1.8} />
          <h2 className="text-[0.95rem] font-semibold text-ink">Ensemble forecast</h2>
          <span className="label hidden sm:inline">
            technical · sentiment · fundamentals · your documents
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-border/60 p-0.5">
            {HORIZONS.map((value) => (
              <button
                key={value}
                onClick={() => setHorizon(value)}
                className={cn(
                  "rounded-md px-2.5 py-1 font-mono text-[0.7rem] transition-colors",
                  horizon === value ? "bg-lime/15 text-lime" : "text-ink-dim hover:text-ink",
                )}
              >
                {value}d
              </button>
            ))}
          </div>
          <Button size="sm" onClick={() => setEnabled(true)} disabled={isFetching}>
            {isFetching ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" />}
            {forecast ? "Re-run" : "Run"}
          </Button>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {!enabled && (
          <motion.p
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-4 text-[0.8rem] leading-relaxed text-ink-muted"
          >
            Four independent signals are scored on the same −1 to +1 scale and weighted by how much
            data each returned. The projection is the 1σ band implied by realised volatility — read
            the range, not the number.
          </motion.p>
        )}

        {forecast && (
          <motion.div
            key={`${forecast.symbol}-${forecast.horizon_days}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="mt-5 grid gap-5 lg:grid-cols-[1fr_1.1fr]"
          >
            {/* -- headline ------------------------------------------------ */}
            <div>
              <div className="flex items-baseline gap-3">
                <span className={cn("text-[1.5rem] font-semibold tracking-[-0.03em]", tone(forecast.signal))}>
                  {forecast.signal}
                </span>
                <span className="numeric text-[0.8rem] text-ink-dim">
                  {forecast.direction >= 0 ? "+" : ""}
                  {forecast.direction.toFixed(2)}
                </span>
              </div>

              <div className="mt-4 space-y-3">
                {[
                  { label: "Confidence", value: forecast.confidence, suffix: "%", tone: "lime" },
                  { label: "Risk", value: forecast.risk_score * 10, suffix: `/10 · ${forecast.risk_label}`, tone: "ember", display: forecast.risk_score },
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
                  <div className="label">{forecast.horizon_days}-session 1σ range</div>
                  <div className="numeric mt-1 text-[1.05rem] text-ink">
                    {money(forecast.expected_low)} – {money(forecast.expected_high)}{" "}
                    <span className="text-ink-dim">{forecast.currency}</span>
                  </div>
                  <p className="mt-1 text-[0.7rem] leading-relaxed text-ink-dim">
                    About two thirds of historical moves of this size land inside this band.
                  </p>
                </div>
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
                          className={cn(
                            "size-3.5 text-ink-dim transition-transform",
                            open === leg.key && "rotate-180",
                          )}
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
          </motion.div>
        )}
      </AnimatePresence>
    </Rise>
  )
}
